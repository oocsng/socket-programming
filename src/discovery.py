# UDP Broadcast and Peer Management

import socket
import time
import threading

from .protocol import PORT

ten = ""
port = ""
my_status = "online"
_running = False

members = {}
lock = threading.Lock()


def _create_send_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    return sock


# Socket UDP dùng để gửi broadcast
s_send = _create_send_socket()


# Gửi packet HELLO
def send_hello():
    packet = f"HELLO|{ten}|{port}|{my_status}".encode()
    try:
        s_send.sendto(packet, ("255.255.255.255", PORT))
    except OSError:
        pass


# Thread 1: Gửi HELLO mỗi 3 giây
def hello_loop():
    while _running:
        send_hello()
        time.sleep(3)


# Thread 2: Lắng nghe packet từ các máy khác
def listen_loop():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", PORT))
    s.settimeout(1)

    try:
        while _running:
            # Xóa peer offline quá 10 giây
            now = time.time()

            with lock:
                for name in list(members.keys()):
                    if now - members[name][3] > 10:
                        print(f"[-] {name} da offline")
                        del members[name]

            try:
                data, addr = s.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                text = data.decode()
            except UnicodeDecodeError:
                continue

            parts = text.split("|")

            if len(parts) != 4 or parts[0] != "HELLO":
                continue

            name = parts[1]
            mem_port = parts[2]
            status = parts[3]

            # Bỏ qua packet của chính mình
            if name == ten and mem_port == port:
                continue

            with lock:
                old = members.get(name)

                if old is None:
                    print(f"[+] {name} vua online ({addr[0]}:{mem_port}), {status}")

                elif old[2] != status:
                    print(f"[*] {name} doi trang thai: {status}")

                elif old[0] != addr[0] or old[1] != mem_port:
                    print(f"[!] {name} doi dia chi: {addr[0]}:{mem_port}")

                members[name] = (
                    addr[0],
                    mem_port,
                    status,
                    time.time()
                )
    finally:
        try:
            s.close()
        except OSError:
            pass


# Khởi động hệ thống discovery
def start(name, cong_tcp):
    global ten, port, _running, s_send

    ten = name
    port = str(cong_tcp)
    _running = True
    if s_send is None or s_send.fileno() == -1:
        s_send = _create_send_socket()

    threading.Thread(
        target=hello_loop,
        daemon=True
    ).start()

    threading.Thread(
        target=listen_loop,
        daemon=True
    ).start()


# Dừng hệ thống discovery và giải phóng socket
def stop():
    global _running
    _running = False
    try:
        s_send.close()
    except OSError:
        pass


# Thay đổi trạng thái
def set_status(status):
    global my_status

    if status not in ("online", "away"):
        return False

    my_status = status
    send_hello()

    return True


# Lấy danh sách peer
def get_peers():
    with lock:
        return [
            {
                "name": name,
                "ip": info[0],
                "tcp_port": info[1],
                "status": info[2]
            }
            for name, info in members.items()
        ]
