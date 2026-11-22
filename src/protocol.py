# Constants, framing helpers, and recv_exact / recv_field

# Cổng UDP dùng để tìm kiếm các máy trong LAN
PORT = 9999

# Kích thước mỗi khối gửi/nhận file (32 KB) và độ dài tối đa 1 trường header
CHUNK_SIZE = 32 * 1024
MAX_FIELD_LEN = 1024


def recv_exact(sock, n):
    """Đọc chính xác n byte từ socket TCP; trả về None nếu đóng giữa chừng."""
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
        if b in (b"\r", b"\n"):
            raise ValueError("Ký tự không hợp lệ trong header")
        buf.extend(b)
        if len(buf) > MAX_FIELD_LEN:
            raise ValueError("Header quá dài")
