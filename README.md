# Socket Programming

Lab exercises and socket project implementation.

## Project Structure

```text
├── src/
│   ├── __init__.py        # Khởi tạo Python package
│   ├── protocol.py        # Hằng số, định dạng gói tin và hàm recv_exact
│   ├── discovery.py       # Module UDP Broadcast & Quản lý Peer (Thành viên A)
│   ├── network_tcp.py     # Module TCP Chat & Truyền File (Thành viên B)
│   └── gui.py             # Module Giao diện Tkinter & Hàng đợi (Thành viên C)
├── main.py                # Điểm khởi chạy ứng dụng (import từ src)
├── downloads/             # Thư mục lưu file nhận về
└── README.md              # Hướng dẫn cài đặt và chạy thử
```

### Reference & Demos
- `docs/`: Tài liệu hướng dẫn đồ án và seminar.
- `sample_code/`: Python socket sample scripts.
- `tcp_server_demo/`: TCP and UDP socket demos.
- `Ref/`: Reference projects and WinSock demos.

## Requirements

- Python 3.x
- C++ compiler (optional, for WinSock reference demos under `Ref/`)
