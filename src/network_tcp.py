"""
network_tcp.py - Hạt nhân kết nối, chat & truyền file (TCP)

Giao thức (mỗi gói bắt đầu bằng 1 từ khóa, các trường ngăn cách bởi '|'):
    HI|<tên>|<cổng_tcp>|
    MSG|<độ_dài_byte>|<nội_dung>
    FILE|<tên_file>|<kích_thước_byte>|<luồng byte nhị phân>
    BYE|
"""
import os
import socket
import threading

try:
    from .protocol import CHUNK_SIZE, MAX_FIELD_LEN, recv_exact, recv_field
except ImportError:
    from protocol import CHUNK_SIZE, MAX_FIELD_LEN, recv_exact, recv_field

DOWNLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads"
)
HANDSHAKE_TIMEOUT = 5.0
FILE_RECV_TIMEOUT = 10.0


# ---------------------------------------------------------------- Framing helper
def _safe_name(name):
    """Chống path traversal và ký tự không hợp lệ trên Windows."""
    cleaned = os.path.basename(name.replace("\\", "/"))
    for ch in '<>:"/\\|?*':
        cleaned = cleaned.replace(ch, "_")
    cleaned = cleaned.strip()
    return "unnamed" if cleaned in ("", ".", "..") else cleaned


# ---------------------------------------------------------------- Kết nối
class PeerConnection:
    """Một kết nối chat TCP tới 1 peer (hai chiều)."""

    def __init__(self, sock, my_name, my_port, callbacks):
        self.sock = sock
        self.my_name = my_name
        self.my_port = my_port
        self.cb = callbacks
        self.peer_name = None
        self.peer_port = None
        self.peer_ip = sock.getpeername()[0]
        self._send_lock = threading.Lock()
        self._local_closed = False

    # --- gửi
    def _send(self, data):
        with self._send_lock:
            self.sock.sendall(data)

    def send_hello(self):
        self._send(f"HI|{self.my_name}|{self.my_port}|".encode("utf-8"))

    def send_message(self, text):
        body = text.encode("utf-8")
        self._send(f"MSG|{len(body)}|".encode("utf-8") + body)

    def send_bye(self):
        try:
            self._send(b"BYE|")
        except OSError:
            pass

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass

    # --- nhận (chạy trong luồng riêng)
    def receive_loop(self):
        is_file_conn = False
        graceful_bye = False
        try:
            self.sock.settimeout(HANDSHAKE_TIMEOUT)
            while True:
                kind = recv_field(self.sock)
                if kind is None:
                    break
                if self.peer_name is None and kind != "HI":
                    raise ValueError("Thiếu gói chào HI|")
                if kind == "HI":
                    self.peer_name = recv_field(self.sock)
                    self.peer_port = int(recv_field(self.sock))
                    self.sock.settimeout(None)
                    self.cb.get("on_peer_connected", lambda *a: None)(
                        self.peer_name, self.peer_ip, self.peer_port)
                elif kind == "MSG":
                    self.cb.get("_on_chat_active", lambda *a: None)(self)
                    length = int(recv_field(self.sock))
                    data = recv_exact(self.sock, length)
                    if data is None:
                        break
                    self.cb.get("on_message", lambda *a: None)(
                        self.peer_name, data.decode("utf-8", errors="replace"))
                elif kind == "FILE":
                    is_file_conn = True
                    if not self._receive_file():
                        break
                elif kind == "BYE":
                    graceful_bye = True
                    break
                else:
                    break  # gói lạ -> ngắt kết nối
        except (OSError, ValueError):
            pass
        finally:
            self.close()
            self.cb.get("_on_conn_closed", lambda *a: None)(self)
            if not is_file_conn and not self._local_closed and self.peer_name:
                self.cb.get("on_peer_disconnected", lambda *a: None)(
                    self.peer_name, graceful_bye)

    def _receive_file(self):
        on_progress = self.cb.get("on_file_progress", lambda *a: None)
        filename = "unknown"
        part_path = None
        received = 0
        try:
            self.sock.settimeout(FILE_RECV_TIMEOUT)
            raw_name = recv_field(self.sock)
            raw_size = recv_field(self.sock)
            if raw_name is None or raw_size is None:
                raise ConnectionError("Thiếu header kích thước file")
            filename = _safe_name(raw_name)
            size = int(raw_size)
            peer_dir = os.path.join(DOWNLOAD_DIR, _safe_name(self.peer_name or "unknown"))
            os.makedirs(peer_dir, exist_ok=True)
            final_path = os.path.join(peer_dir, filename)
            part_path = final_path + ".part"

            with open(part_path, "wb") as f:
                while received < size:
                    data = recv_exact(self.sock, min(CHUNK_SIZE, size - received))
                    if data is None:
                        raise ConnectionError("Sender closed before file completed")
                    f.write(data)
                    received += len(data)
                    on_progress(self.peer_name, filename,
                                100 if size == 0 else received * 100 // size)

            os.replace(part_path, final_path)  # đủ 100% mới đổi tên
        except (OSError, ValueError):
            if part_path and os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except OSError:
                    pass
            on_progress(self.peer_name, filename, -1)  # lỗi/đứt
            return False

        self.cb.get("on_file_done", lambda *a: None)(
            self.peer_name, final_path)
        return True


# ---------------------------------------------------------------- Server
class TCPServer:
    """Acceptor: lắng nghe cổng, mỗi peer kết đến -> 1 luồng receiver."""

    def __init__(self, my_name, port=0, callbacks=None):
        self.my_name = my_name
        self.cb = callbacks or {}
        self.peers = {}          # (ip, port_peer) -> PeerConnection
        self._lock = threading.Lock()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("0.0.0.0", port))
        self.port = self.server.getsockname()[1]   # port=0 -> hệ thống tự chọn
        self.server.listen(10)
        self._running = False

    def start(self):
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self):
        self._running = False
        try:
            self.server.close()
        except OSError:
            pass
        with self._lock:
            conns = list(self.peers.values())
            self.peers.clear()
        for p in conns:
            p._local_closed = True
            p.send_bye()
            p.close()

    def _accept_loop(self):
        while self._running:
            try:
                conn, _ = self.server.accept()
            except OSError:
                break
            peer = PeerConnection(conn, self.my_name, self.port, self._wrap_cb())
            try:
                peer.send_hello()
            except OSError:
                peer.close()
                continue
            threading.Thread(target=peer.receive_loop, daemon=True).start()

    def _wrap_cb(self):
        """Bọc callback để lưu peer khi nhận chat và dọn khi đóng kết nối."""
        cb = dict(self.cb)

        def on_chat_active(conn):
            if conn.peer_port is None:
                return
            with self._lock:
                self.peers.setdefault((conn.peer_ip, conn.peer_port), conn)

        def on_conn_closed(conn):
            with self._lock:
                for k in [k for k, v in self.peers.items() if v is conn]:
                    self.peers.pop(k, None)

        cb["_on_chat_active"] = on_chat_active
        cb["_on_conn_closed"] = on_conn_closed
        return cb

    # --- phía chủ động kết nối
    def connect_to_peer(self, ip, port):
        """Mở kết nối chat tới peer, trả về PeerConnection."""
        key = (ip, port)
        with self._lock:
            if key in self.peers:
                return self.peers[key]
        sock = socket.create_connection((ip, port), timeout=3)
        sock.settimeout(None)
        peer = PeerConnection(sock, self.my_name, self.port, self._wrap_cb())
        peer.send_hello()
        with self._lock:
            self.peers[key] = peer
        threading.Thread(target=peer.receive_loop, daemon=True).start()
        return peer

    def send_message(self, ip, port, text):
        conn = self.connect_to_peer(ip, port)
        try:
            conn.send_message(text)
        except OSError:
            conn._local_closed = True
            with self._lock:
                for k in [k for k, v in self.peers.items() if v is conn]:
                    self.peers.pop(k, None)
            conn.close()
            raise

    def leave_peer(self, ip, port, peer_name=None):
        """Gửi BYE| và đóng kết nối chat tới peer."""
        conns = []
        key = (ip, int(port))
        with self._lock:
            conn = self.peers.pop(key, None)
            if conn:
                conns.append(conn)
            if peer_name:
                for k in [k for k, v in self.peers.items()
                          if v.peer_name == peer_name]:
                    c = self.peers.pop(k, None)
                    if c:
                        conns.append(c)
        for conn in conns:
            conn._local_closed = True
            conn.send_bye()
            conn.close()

    # --- gửi file: kết nối TCP độc lập, luồng riêng
    def send_file(self, ip, port, filepath, on_progress=None):
        threading.Thread(
            target=self._send_file_worker,
            args=(ip, port, filepath, on_progress),
            daemon=True).start()

    def _send_file_worker(self, ip, port, filepath, on_progress):
        filename = _safe_name(os.path.basename(filepath))
        try:
            size = os.path.getsize(filepath)
            with socket.create_connection((ip, port), timeout=5) as s:
                s.settimeout(FILE_RECV_TIMEOUT)
                s.sendall(f"HI|{self.my_name}|{self.port}|".encode("utf-8"))
                s.sendall(f"FILE|{filename}|{size}|".encode("utf-8"))
                sent = 0
                with open(filepath, "rb") as f:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        s.sendall(chunk)
                        sent += len(chunk)
                        if on_progress:
                            on_progress(filename,
                                        100 if size == 0 else sent * 100 // size)
                if on_progress and size == 0:
                    on_progress(filename, 100)
                # Half-close write side and drain peer's HI greeting until FIN so
                # Winsock does not emit a TCP RST that truncates large transfers.
                s.shutdown(socket.SHUT_WR)
                s.settimeout(5.0)
                try:
                    while s.recv(1024):
                        pass
                except OSError:
                    pass
        except OSError:
            if on_progress:
                on_progress(filename, -1)   # -1 = lỗi


# ---------------------------------------------------------------- Demo
if __name__ == "__main__":
    # Chạy thử 2 peer trên cùng máy: python src/network_tcp.py
    import time

    def make(name):
        return TCPServer(name, callbacks={
            "on_peer_connected": lambda n, ip, p: print(f"[{name}] peer vào: {n} {ip}:{p}"),
            "on_message": lambda n, t: print(f"[{name}] {n}: {t}"),
            "on_file_progress": lambda n, f, pct: print(f"[{name}] {f}: {pct}%"),
            "on_file_done": lambda n, p: print(f"[{name}] nhận xong: {p}"),
        })

    a, b = make("Alice"), make("Bob")
    a.start(); b.start()
    a.send_message("127.0.0.1", b.port, "Xin chào Bob!")
    time.sleep(0.5)
    a.send_file("127.0.0.1", b.port, __file__)
    time.sleep(1)
