# LAN Chat & File Sharing (P2P Socket Programming)

Ứng dụng nhắn tin và chia sẻ tệp tin trong mạng cục bộ (LAN) cho đồ án môn Mạng Máy Tính (`CSC10008`), viết bằng Python sử dụng Socket API gốc (UDP Broadcast kết hợp TCP Unicast), `threading`, `queue.Queue` và giao diện Tkinter.

## Nhóm thực hiện

- **Nguyễn Xuân Nhi** (`23127445`): UDP Discovery (`src/discovery.py`, `src/protocol.py`)
- **Ao Trường Giang** (`25127317`): TCP Chat & Truyền tệp (`src/network_tcp.py`, `src/protocol.py`)
- **Nguyễn Minh Nghĩa** (`25127429`): Giao diện Tkinter, hàng đợi `queue.Queue`, tích hợp & báo cáo (`src/gui.py`, `main.py`)

## Cấu trúc dự án

```text
├── src/
│   ├── __init__.py                         # Khởi tạo Python package
│   ├── protocol.py                         # Hằng số, framing recv_exact() & recv_field() chặn CR/LF
│   ├── discovery.py                        # Luồng UDP Broadcast (9999), bảng Peer & stop()
│   ├── network_tcp.py                      # TCP Server/Client, chat, truyền file, BYE| & timeout lỗi
│   └── gui.py                              # Hộp thoại Login, GUI 2 cột, Open File Location & check_queue()
├── main.py                                 # Điểm khởi chạy chính, kết nối discovery, TCPServer và GUI
├── 23127445_25127317_25127429_Report.pdf   # Báo cáo đồ án (9 trang)
├── docs/                                   # Đề bài, rubric và tài liệu hướng dẫn đồ án
├── downloads/                              # Tự động tạo khi nhận tệp (downloads/<tên_peer>/)
├── .gitignore                              # Bỏ qua __pycache__, downloads/, .vscode/ và .DS_Store
└── README.md                               # Hướng dẫn cài đặt, chạy và kiểm thử
```

## Yêu cầu & Cài đặt

- Python 3.8+ (chỉ dùng thư viện chuẩn: `tkinter`, `socket`, `threading`, `queue`, `ctypes`, `os`).
- Không cần cài thêm thư viện ngoài qua `pip`.

## Cách chạy ứng dụng

### 1. Chạy nhiều cửa sổ thử nghiệm trên cùng 1 máy

Mở 2 hoặc 3 cửa sổ terminal tại thư mục gốc dự án rồi chạy:

```bash
python main.py
```

- Cửa sổ 1: nhập Username (không trống, không chứa `|`), giữ cổng TCP mặc định `5000` (hoặc bấm `Random`).
- Cửa sổ 2: nhập Username khác, bấm `Random` để lấy cổng trong khoảng `5000 - 9000` rồi bấm `Start chat`.

### 2. Chạy trên 2+ máy trong cùng mạng LAN

1. Nối các máy vào cùng mạng LAN hoặc dùng Mobile Hotspot (tránh Wi-Fi công cộng bật AP/Client Isolation chặn UDP Broadcast).
2. Cho phép `python` đi qua Windows Defender Firewall ở cả Private và Public networks khi hộp thoại hiện lên, hoặc mở thủ công:
   - `UDP` cổng `9999` (Inbound/Outbound cho discovery broadcast).
   - `TCP` dải cổng `5000 - 9000` (Inbound/Outbound cho chat và truyền tệp).
3. Chạy `python main.py` trên mỗi máy. Trong tối đa 3 giây, danh sách `Currently online peers` tự cập nhật các máy còn lại.

## Đặc tả giao thức & cơ chế truyền tệp

- **UDP Broadcast (`255.255.255.255:9999`, chu kỳ 3s, timeout 10s):**
  `HELLO|<name>|<tcp_port>|<status>` (`status` là `online` hoặc `away`).
- **TCP Unicast (cổng riêng từng máy):**
  - Định danh (gói bắt buộc đầu tiên, `HANDSHAKE_TIMEOUT = 5s`): `HI|<name>|<tcp_port>|`
  - Tin nhắn chat: `MSG|<length_bytes>|<utf8_text>`
  - Truyền tệp (trên kết nối TCP riêng, `FILE_RECV_TIMEOUT = 10s`): `FILE|<filename>|<size_bytes>|<raw_bytes>`
  - Đóng phiên chủ động (`Leave Chat` / thoát app): `BYE|`

Tệp nhận về ghi tạm vào `downloads/<tên_peer>/<filename>.part` và chỉ gọi `os.replace()` sang tệp hoàn chỉnh khi nhận đủ 100% byte; phía gửi dùng `shutdown(socket.SHUT_WR)` và đọc cạn bộ đệm để tránh Winsock phát `TCP RST`. Sau khi xong, khung chat hiển thị nút **Open File Location** gọi Win32 `SHOpenFolderAndSelectItems` mở đúng thư mục con của peer và bôi chọn tệp.

## Hướng dẫn kiểm thử 5 kịch bản lỗi & Wireshark

1. **Chat với người vừa offline:** Tắt ứng dụng bên Máy B, Máy A nhắn ngay trước timeout 10 giây -> `connect_to_peer` (`timeout=3s`) bắt `OSError`/`ConnectionRefusedError`, hiện `[Error]` trên GUI, không crash.
2. **Peer thoát đột ngột khi đang chat:** Đóng ngang terminal bên B (không gửi `BYE|`) -> Máy A nhận EOF/`ConnectionResetError` và báo ngay `[Error] Connection lost with <peer>.` (khác với bấm `Leave Chat` gửi `BYE|` báo `left the chat`).
3. **Đứt mạng khi đang truyền tệp:** Ngắt Wi-Fi bên gửi ở mức `~50%` -> quá `FILE_RECV_TIMEOUT = 10s` bên nhận tự đóng file handle, xóa sạch `*.part`, báo `[Error]` và ẩn thanh tiến độ.
4. **Gói tin sai định dạng:** Dùng `nc <ip> <port>` (hoặc `python -c "import socket,sys; s=socket.create_connection((sys.argv[1],5000)); print(s.recv(1024)); s.sendall(b'abc\n'); print(s.recv(1024))" <ip>`) gửi `abc\n` -> `recv_field()` chặn CR/LF và ép `HI|`, đóng riêng kết nối rác; các phiên chat khác vẫn chạy bình thường.
5. **Chưa chọn peer / tệp lỗi:** Bấm `Send` / `Send file` khi chưa chọn đối tác bị GUI chặn; chọn tệp bị xóa/không đọc được bị `os.path.isfile()` hoặc `try/except OSError` chặn và báo lỗi an toàn.

**Bộ lọc Wireshark tham khảo (trên card mạng thật):**
- Gói UDP Discovery & Status: `udp.port == 9999`
- Bắt tay 3 bước TCP: `tcp.port == <port> && tcp.flags.syn == 1`
- Nội dung Framing (`HI`, `MSG`, `FILE`, `BYE`): chuột phải gói TCP -> `Follow -> TCP Stream`
