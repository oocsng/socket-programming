"""
network_tcp.py - Hạt nhân kết nối, chat & truyền file (TCP)

Giao thức (mỗi gói bắt đầu bằng 1 từ khóa, các trường ngăn cách bởi '|'):
    HI|<tên>|<cổng_tcp>|
    MSG|<độ_dài_byte>|<nội_dung>
    FILE|<tên_file>|<kích_thước_byte>|<luồng byte nhị phân>
"""
import os
import socket
import threading

CHUNK_SIZE = 32 * 1024          # 32 KB mỗi khối
DOWNLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads"
)
MAX_FIELD_LEN = 1024            # chặn header dài bất thường


# ---------------------------------------------------------------- Framing
def recv_exact(sock, n):
    """Đọc ĐÚNG n byte (xử lý bài toán rách/dính gói của TCP).
    Trả về None nếu đối phương đóng kết nối giữa chừng."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def recv_field(sock):
    """Đọc từng byte cho tới khi gặp '|', trả về chuỗi (không gồm '|')."""
    buf = bytearray()
    while True:
        b = recv_exact(sock, 1)
        if b is None:
            return None
        if b == b"|":
            return buf.decode("utf-8", errors="replace")
        buf.extend(b)
        if len(buf) > MAX_FIELD_LEN:
            raise ValueError("Header quá dài")


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

    # --- gửi
    def _send(self, data):
        with self._send_lock:
            self.sock.sendall(data)

    def send_hello(self):
        self._send(f"HI|{self.my_name}|{self.my_port}|".encode("utf-8"))

    def send_message(self, text):
        body = text.encode("utf-8")
        self._send(f"MSG|{len(body)}|".encode("utf-8") + body)

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass

    # --- nhận (chạy trong luồng riêng)
    def receive_loop(self):
        try:
            while True:
                kind = recv_field(self.sock)
                if kind is None:
                    break
                if kind == "HI":
                    self.peer_name = recv_field(self.sock)
                    self.peer_port = int(recv_field(self.sock))
                    self.cb.get("on_peer_connected", lambda *a: None)(
                        self.peer_name, self.peer_ip, self.peer_port)
                elif kind == "MSG":
                    length = int(recv_field(self.sock))
                    data = recv_exact(self.sock, length)
                    if data is None:
                        break
                    self.cb.get("on_message", lambda *a: None)(
                        self.peer_name, data.decode("utf-8", errors="replace"))
                elif kind == "FILE":
                    if not self._receive_file():
                        break
                else:
                    break  # gói lạ -> ngắt kết nối
        except (OSError, ValueError):
            pass
        finally:
            self.close()
            self.cb.get("on_peer_disconnected", lambda *a: None)(self.peer_name)

    def _receive_file(self):
        filename = _safe_name(recv_field(self.sock) or "")
        size = int(recv_field(self.sock))
        peer_dir = os.path.join(DOWNLOAD_DIR, _safe_name(self.peer_name or "unknown"))
        os.makedirs(peer_dir, exist_ok=True)
        final_path = os.path.join(peer_dir, filename)
        part_path = final_path + ".part"
        on_progress = self.cb.get("on_file_progress", lambda *a: None)

        received = 0
        try:
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
            if os.path.exists(part_path):
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
            for p in self.peers.values():
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
                continue
            threading.Thread(target=peer.receive_loop, daemon=True).start()

    def _wrap_cb(self):
        """Bọc callback để lưu peer vào danh sách khi bắt tay xong."""
        cb = dict(self.cb)
        orig_connected = self.cb.get("on_peer_connected", lambda *a: None)
        orig_disc = self.cb.get("on_peer_disconnected", lambda *a: None)

        def on_connected(name, ip, port):
            orig_connected(name, ip, port)

        def on_disconnected(name):
            with self._lock:
                for k in [k for k, v in self.peers.items()
                          if v.peer_name == name]:
                    self.peers.pop(k, None)
            orig_disc(name)

        cb["on_peer_connected"] = on_connected
        cb["on_peer_disconnected"] = on_disconnected
        return cb

    # --- phía chủ động kết nối
    def connect_to_peer(self, ip, port):
        """Mở kết nối chat tới peer, trả về PeerConnection."""
        key = (ip, port)
        with self._lock:
            if key in self.peers:
                return self.peers[key]
        sock = socket.create_connection((ip, port), timeout=5)
        sock.settimeout(None)
        peer = PeerConnection(sock, self.my_name, self.port, self._wrap_cb())
        peer.send_hello()
        with self._lock:
            self.peers[key] = peer
        threading.Thread(target=peer.receive_loop, daemon=True).start()
        return peer

    def send_message(self, ip, port, text):
        self.connect_to_peer(ip, port).send_message(text)

    # --- gửi file: kết nối TCP độc lập, luồng riêng
    def send_file(self, ip, port, filepath, on_progress=None):
        threading.Thread(
            target=self._send_file_worker,
            args=(ip, port, filepath, on_progress),
            daemon=True).start()

    def _send_file_worker(self, ip, port, filepath, on_progress):
        filename = _safe_name(os.path.basename(filepath))
        size = os.path.getsize(filepath)
        try:
            with socket.create_connection((ip, port), timeout=5) as s:
                s.settimeout(None)
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
    time.sleep(1)# TCP Chat and File Transfer
