import os
import queue
import threading
import time
from tkinter import messagebox

from src import discovery
from src.gui import get_user_config, start_gui
from src.network_tcp import DOWNLOAD_DIR, TCPServer, _safe_name


def main():
    # 1. Call login dialog to get Username and TCP Port
    my_name, my_port = get_user_config()
    if my_name is None:
        return

    # 2. Shared event queue for GUI thread
    event_queue = queue.Queue()
    running = True

    # 3. Callbacks when TCPServer (Member B) receives messages or files
    def on_tcp_message(sender_name, text):
        if sender_name:
            event_queue.put(("new_message", {"sender": sender_name, "text": text}))

    def on_tcp_file_progress(sender_name, filename, percent):
        if percent < 0:
            part_path = os.path.join(
                DOWNLOAD_DIR, _safe_name(sender_name or "unknown"), filename + ".part"
            )
            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except OSError:
                    pass
            event_queue.put(
                (
                    "file_progress",
                    {
                        "filename": filename,
                        "percent": 0,
                        "done": True,
                        "action": "Receiving",
                        "error": True,
                    },
                )
            )
            event_queue.put(
                (
                    "system_error",
                    {
                        "message": f"File receive interrupted: {filename} (partial file deleted)"
                    },
                )
            )
        else:
            event_queue.put(
                (
                    "file_progress",
                    {
                        "filename": filename,
                        "percent": percent,
                        "done": percent >= 100,
                        "action": "Receiving",
                    },
                )
            )

    def on_tcp_file_done(sender_name, saved_path):
        event_queue.put(
            (
                "system_info",
                {
                    "message": f"Received file from {sender_name}: {saved_path}",
                    "file_path": os.path.abspath(saved_path),
                    "peer": sender_name,
                },
            )
        )

    tcp_callbacks = {
        "on_message": on_tcp_message,
        "on_file_progress": on_tcp_file_progress,
        "on_file_done": on_tcp_file_done,
    }

    # 4. Start TCP Server (Member B)
    try:
        tcp_server = TCPServer(my_name, port=my_port, callbacks=tcp_callbacks)
        tcp_server.start()
    except OSError as exc:
        messagebox.showerror("Port Error", f"Cannot bind TCP port {my_port}:\n{exc}")
        return

    # 5. Start UDP Discovery (Member A) and bridge peer list to event_queue
    try:
        discovery.start(my_name, my_port)
    except OSError as exc:
        tcp_server.stop()
        messagebox.showerror("UDP Error", f"Cannot start UDP discovery:\n{exc}")
        return

    def sync_discovery_loop():
        known_names = set()
        while running:
            current_peers = discovery.get_peers()
            current_names = set()

            for p in current_peers:
                name = p["name"]
                current_names.add(name)
                event_queue.put(
                    (
                        "peer_update",
                        {
                            "name": name,
                            "ip": p["ip"],
                            "port": int(p["tcp_port"]),
                            "status": p["status"],
                        },
                    )
                )

            for gone_name in known_names - current_names:
                event_queue.put(("peer_offline", {"name": gone_name}))

            known_names = current_names
            time.sleep(1.0)

    threading.Thread(target=sync_discovery_loop, daemon=True).start()

    # 6. Outbound callbacks from GUI (Member C) to UDP/TCP modules
    def handle_send_msg(partner_name, partner_addr, text):
        if not partner_addr:
            event_queue.put(
                ("system_error", {"message": f"Cannot find address for {partner_name}."})
            )
            return

        ip, port = partner_addr

        def _worker():
            try:
                tcp_server.send_message(ip, int(port), text)
            except OSError as exc:
                event_queue.put(
                    (
                        "system_error",
                        {"message": f"Cannot send message to {partner_name}: {exc}"},
                    )
                )

        threading.Thread(target=_worker, daemon=True).start()

    def handle_send_file(partner_name, partner_addr, filepath):
        if not partner_addr:
            event_queue.put(
                ("system_error", {"message": f"Cannot find address for {partner_name}."})
            )
            return
        if not os.path.isfile(filepath):
            event_queue.put(("system_error", {"message": f"File not found: {filepath}"}))
            return

        ip, port = partner_addr

        def on_send_progress(filename, percent):
            if percent < 0:
                event_queue.put(
                    (
                        "file_progress",
                        {
                            "filename": filename,
                            "percent": 0,
                            "done": True,
                            "action": "Sending",
                            "error": True,
                        },
                    )
                )
                event_queue.put(
                    ("system_error", {"message": f"Failed to send file: {filename}"})
                )
            else:
                event_queue.put(
                    (
                        "file_progress",
                        {
                            "filename": filename,
                            "percent": percent,
                            "done": percent >= 100,
                            "action": "Sending",
                        },
                    )
                )
                if percent >= 100:
                    event_queue.put(
                        (
                            "system_info",
                            {
                                "message": f"Finished sending file to {partner_name}: {filename}",
                                "file_path": os.path.abspath(filepath),
                                "peer": partner_name,
                            },
                        )
                    )

        tcp_server.send_file(ip, int(port), filepath, on_progress=on_send_progress)

    def handle_status_change(new_status):
        discovery.set_status(new_status)

    def handle_leave_chat(partner_name, partner_addr):
        if partner_addr:
            key = (partner_addr[0], int(partner_addr[1]))
            with tcp_server._lock:
                conn = tcp_server.peers.pop(key, None)
            if conn:
                conn.close()

    def handle_close():
        nonlocal running
        running = False
        tcp_server.stop()

    # 7. Launch GUI
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
