# LAN Chat & File Sharing (P2P Socket Programming)

Ứng dụng nhắn tin và chia sẻ tệp tin trong mạng cục bộ (LAN) viết bằng Python sử dụng Socket API gốc (UDP Broadcast kết hợp TCP Unicast), `threading`, `queue.Queue` và giao diện Tkinter.

## Cấu trúc dự án

```text
├── src/
│   ├── __init__.py        # Khởi tạo Python package
│   ├── protocol.py        # Hằng số UDP/TCP, framing recv_exact() & recv_field()
│   ├── discovery.py       # Luồng UDP Broadcast (9999) & quản lý bảng Peer (Thành viên A)
│   ├── network_tcp.py     # TCP Server/Client, chat, truyền file & BYE| (Thành viên B)
│   └── gui.py             # Hộp thoại Login, GUI Tkinter 2 cột & check_queue() (Thành viên C)
├── main.py                # Điểm khởi chạy chính, kết nối discovery, TCPServer và GUI
├── downloads/             # Thư mục lưu tệp nhận theo từng peer (downloads/<tên_peer>/)
├── docs/                  # Đề bài, rubric và tài liệu tham khảo
└── README.md              # Hướng dẫn cài đặt, chạy và kiểm thử
```

## Yêu cầu & Cài đặt

- Python 3.8+ (có sẵn `tkinter`, `socket`, `threading`, `queue`, `ctypes` trong thư viện chuẩn).
- Không cần cài thêm thư viện bên ngoài qua `pip`.

## Cách chạy ứng dụng

### 1. Chạy nhiều cửa sổ thử nghiệm trên cùng 1 máy

Mở 2 hoặc 3 cửa sổ terminal tại thư mục gốc dự án rồi chạy cùng một lệnh:

```bash
python main.py
```

- Cửa sổ 1: nhập Username (không chứa ký tự `|`), giữ cổng TCP mặc định `5000` (hoặc bấm `Random`).
- Cửa sổ 2: nhập Username khác, bấm `Random` để lấy cổng khác trong khoảng `5000 - 9000` rồi bấm `Start chat`.

### 2. Chạy trên 2+ máy trong cùng mạng LAN

1. Kết nối các máy vào cùng một mạng LAN hoặc dùng Mobile Hotspot (tránh Wi-Fi công cộng có bật AP/Client Isolation chặn UDP Broadcast).
2. Mở Windows Defender Firewall khi lần đầu chạy `python main.py` (tích cả Private và Public networks), hoặc mở thủ công:
   - `UDP` cổng `9999` (Inbound/Outbound cho discovery broadcast).
   - `TCP` khoảng cổng `5000 - 9000` (Inbound/Outbound cho chat và truyền file).
3. Chạy `python main.py` trên mỗi máy. Trong tối đa 3 giây, danh sách `Currently online peers` sẽ tự động hiển thị các máy còn lại.

## Đặc tả giao thức ngắn gọn

- **UDP Broadcast (`255.255.255.255:9999`, mỗi 3 giây, timeout 10 giây):**
  `HELLO|<name>|<tcp_port>|<status>` (`status` là `online` hoặc `away`).
- **TCP Unicast (cổng riêng từng máy):**
  - Định danh: `HI|<name>|<tcp_port>|`
  - Tin nhắn chat: `MSG|<length_bytes>|<utf8_text>`
  - Truyền file (trên kết nối TCP riêng): `FILE|<filename>|<size_bytes>|<raw_bytes>`
  - Rời cuộc trò chuyện: `BYE|`

File nhận được ghi tạm vào `downloads/<tên_peer>/<filename>.part` và chỉ đổi thành file hoàn chỉnh khi đủ 100% byte; nếu đứt kết nối giữa chừng sẽ tự động xóa `.part`.

## Hướng dẫn kiểm thử 5 kịch bản lỗi & Wireshark

1. **Chat với người vừa offline:** Tắt ứng dụng bên Máy B, Máy A nhắn ngay trước timeout 10 giây -> báo `[Error]`, không crash.
2. **Peer thoát đột ngột khi đang chat:** Đóng ngang cửa sổ terminal bên B -> Máy A nhận thông báo `Connection lost with <peer>.` ngay lập tức.
3. **Đứt mạng khi đang truyền file:** Tắt app hoặc ngắt Wi-Fi bên gửi ở mức `~50%` -> bên nhận ẩn progress bar, báo lỗi và xóa file `.part`.
4. **Gói tin sai định dạng:** Dùng netcat (`nc <ip> <port>`) kết nối vào cổng TCP của peer và gõ `abc` -> parser bắt `ValueError`, đóng riêng kết nối lỗi, chat hiện có vẫn chạy tiếp.
5. **Chưa chọn peer / file không hợp lệ:** Bấm `Send` / `Send file` khi chưa chọn peer hoặc file bị xóa -> GUI chặn hoặc báo `[Error]`.

**Bộ lọc Wireshark tham khảo (trên card mạng thật):**
- Gói UDP Discovery & Status: `udp.port == 9999`
- Bắt tay 3 bước TCP: `tcp.port == <port> && tcp.flags.syn == 1`
- Nội dung Framing (`HI`, `MSG`, `FILE`, `BYE`): chuột phải gói TCP -> `Follow -> TCP Stream`.
