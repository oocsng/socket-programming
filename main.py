import queue
from src.gui import get_user_config, start_gui


def main():
    # 1. Call login box
    my_name, my_port = get_user_config()
    if my_name is None:
        return
    # 2. Create event queue for
    event_queue = queue.Queue()

    # 3. Placeholder functions for now, (A and B is going to plug in)
    def handle_send_msg(partner_name, partner_addr, text):
        print(f"[DEBUG -> TCP] Send message to {partner_name} {partner_addr}: {text}")

    def handle_send_file(partner_name, partner_addr, filepath):
        print(f"[DEBUG -> FILE] Send file {filepath} to {partner_name} {partner_addr}")

    def handle_status_change(new_status):
        print(f"[DEBUG -> UDP] Change status to: {new_status}")

    def handle_leave_chat(partner_name, partner_addr):
        print(f"[DEBUG -> TCP] Leave chat with {partner_name} {partner_addr}")

    def handle_close():
        print(f"[DEBUG -> SYSTEM] Closing socket and background resources...")

    # 4. Call GUI
    start_gui(
        my_name=my_name,
        my_port=my_port,
        event_queue=event_queue,
        on_send_msg=handle_send_msg,
        on_send_file=handle_send_file,
        on_status_change=handle_status_change,
        on_leave_chat=handle_leave_chat,
        on_close=handle_close,
    )


if __name__ == "__main__":
    main()
