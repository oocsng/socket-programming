# Constants, packet formatting, and recv_exact helper

import struct

# Cổng UDP dùng để tìm kiếm các máy trong LAN
PORT = 9999

# Header 4 byte lưu độ dài dữ liệu TCP
HEADER_SIZE = 4


def encode_frame(data):
    """Đóng gói dữ liệu theo định dạng length-prefix."""
    header = struct.pack("!I", len(data))
    return header + data


def recv_exact(sock, n):
    """Nhận chính xác n byte từ socket TCP."""
    data = b""

    while len(data) < n:
        packet = sock.recv(n - len(data))

        if not packet:
            return None

        data += packet

    return data
