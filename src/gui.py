# Tkinter GUI and message queue
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import queue
import random  # for port
import sys

# -------- Login box -------------


def get_user_config():
    login_win = tk.Tk()
    login_win.title("Login - LAN Chat")
    login_win.geometry("360x260")
    login_win.resizable(False, False)  # lock the window

    result = {"name": None, "port": None}

    # Username input
    tk.Label(login_win, text="Username", font=("Segoe UI", 10, "bold")).pack(
        anchor="w", padx=20, pady=(15, 2)
    )
    ent_name = tk.Entry(login_win, font=("Segoe UI", 10))
    ent_name.pack(fill=tk.X, padx=20, ipady=3)
    ent_name.focus()  # place cursor on input box

    # TPC-Port Input + Randomizer
    tk.Label(
        login_win, text="TCP Port (1024 - 65535):", font=("Segoe UI", 10, "bold")
    ).pack(anchor="w", padx=20, pady=(10, 2))
    port_frame = tk.Frame(login_win)
    port_frame.pack(fill=tk.X, padx=20)

    ent_port = tk.Entry(port_frame, font=("Segoe UI", 10))
    ent_port.insert(0, "5000")  # default TCP-port to 5000
    ent_port.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

    def port_randomizer():
        ent_port.delete(0, tk.END)
        ent_port.insert(0, str(random.randint(5000, 9000)))

    btn_random = tk.Button(
        port_frame, text="Random", command=port_randomizer, font=("Segoe UI", 9), padx=8
    )
    btn_random.pack(side=tk.RIGHT, padx=(6, 0))

    # Error label (left blank by default)
    lbl_error = tk.Label(login_win, text="", font=("Segoe UI", 9), fg="#c53030")
    lbl_error.pack(pady=(6, 0))

    # check-input function and confirmation
    def submit():
        name = ent_name.get().strip()
        port_str = ent_port.get().strip()

        # Gate 1: Username mustn't be blank
        if not name:
            lbl_error.config(text="Username can not be empty.")
            return
        # Gate 2: Prohibit '|' in username as it is a divider of the protocol
        if "|" in name:
            lbl_error.config(text="Username can not contain '|'.")
            return
        # Gate 3: Port has to be an integer in range [1024,65535]
        try:
            port = int(port_str)
            if port < 1024 or port > 65535:
                raise ValueError
        except ValueError:
            lbl_error.config(text="Port must be an integer in range [1024,65535].")
            return
        # if not stopped by any gate
        result["name"] = name
        result["port"] = port
        login_win.destroy()

    btn_start = tk.Button(
        login_win,
        text="Start chat",
        command=submit,
        font=("Segoe UI", 10, "bold"),
        bg="#2b6cb0",
        fg="#ffffff",
        relief=tk.FLAT,
        pady=4,
    )
    btn_start.pack(fill=tk.X, padx=20, pady=(8, 15))

    # Pressing "enter" at username box or port box both confirms login
    ent_name.bind("<Return>", lambda event: submit())
    ent_port.bind("<Return>", lambda event: submit())

    login_win.mainloop()
    return result["name"], result["port"]


def start_gui(
    my_name,
    my_port,
    event_queue,
    on_send_msg=None,
    on_send_file=None,
    on_status_change=None,
    on_close=None,
):

    # Create the main window
    root = tk.Tk()

    # Set window title
    root.title("LAN Chat & File Sharing (P2P)")

    # Set window size
    root.geometry("900x600")

    # Set min window size
    root.minsize(750, 480)
    # ------------------------------------------------- #

    # Create left panel
    left_frame = tk.Frame(root, width=280, bg="#f0f2f5")
    left_frame.pack(side=tk.LEFT, fill=tk.Y)
    # Stop left panel from auto-minimizing
    left_frame.pack_propagate(False)

    # Create right panel
    right_frame = tk.Frame(root, bg="#ffffff")
    right_frame.pack(side=tk.RIGHT, fill="both", expand=True)

    # ---------Personal information block----------- #

    profile_frame = tk.LabelFrame(
        left_frame,
        text=" Your information ",
        font=("Segoe UI", 9, "bold"),
        bg="#f0f2f5",
        padx=10,
        pady=8,
    )

    profile_frame.pack(fill=tk.X, padx=10, pady=10)

    # Display name and TCP port (placeholder)
    lbl_user = tk.Label(
        # profile_frame, text="Name: Quan (Port: 5000)", font=("Segoe UI", 10), bg="#f0f2f5"
        profile_frame,
        text=f"Name: {my_name} Port: {my_port}",
        font=("Segoe UI", 10),
        bg="#f0f2f5",
    )

    lbl_user.pack(anchor="w")

    # Create variable to manage status, initialized as "Active"
    status_var = tk.StringVar(value="Status: Active")

    lbl_status = tk.Label(
        profile_frame,
        textvariable=status_var,
        font=("Segoe UI", 9, "italic"),
        fg="#2e7d32",
        bg="#f0f2f5",
    )

    lbl_status.pack(anchor="w", pady=(2, 6))

    # Define status toggler
    def toggle_status():
        if "Active" in status_var.get():
            new_status = "Away"
            status_var.set("Status: Away")
            lbl_status.config(fg="#e65100")
            btn_toggle.config(text="Switch to Active")
        else:
            new_status = "Active"
            status_var.set("Status: Active")
            lbl_status.config(fg="#2e7d32")
            btn_toggle.config(text="Switch to Away")
        if on_status_change:
            on_status_change(new_status)

    btn_toggle = tk.Button(
        profile_frame,
        text="Switch to Away",
        command=toggle_status,
        font=("Segoe UI", 9),
    )

    btn_toggle.pack(fill=tk.X, padx=10)

    # -----------Online peers list block-------------- #

    # Create peers list title
    lbl_peers = tk.Label(
        left_frame,
        text="Currently online peers:",
        font=("Segoe UI", 9, "bold"),
        bg="#f0f2f5",
    )

    lbl_peers.pack(anchor="w", padx=10, pady=(12, 4))
    # Create container box for Peer's listbox and scrollbar
    list_container = tk.Frame(left_frame)
    list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    # Container 1. Create VERTICAL scrollbar
    scrollbar = tk.Scrollbar(list_container, orient=tk.VERTICAL)

    # Container 2. Create Peer's listbox, only 1 selectable object at a time
    peer_listbox = tk.Listbox(
        list_container,
        yscrollcommand=scrollbar.set,
        font=("Segoe UI", 10),
        selectmode=tk.SINGLE,
    )

    # Container 3. Connect listbox and scrollbar together
    # Listbox scrolls as scrollbar scrolls
    scrollbar.config(command=peer_listbox.yview)

    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    peer_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Placeholder online peers initialize (Name (ip:tcp_port) [Status] (Unread msgs))
    # peer_listbox.insert(tk.END, "Minh (192.168.1.12:6000) [Active] (2)")
    # peer_listbox.insert(tk.END, "Huy (192.168.1.20:5000) [Away]")

    # ----------- Right frame: Chat box ---------------------

    # Placeholder for display name and information of the peer currently chatting with (Current chatting with: Name (ip:tcp_port) [Status])
    lbl_chat_header = tk.Label(
        right_frame,
        text="Select a peer from the left list to start chatting",
        font=("Segoe UI", 11, "bold"),
        bg="#ffffff",
        fg="#1a365d",
        anchor="w",
        padx=15,
        pady=10,
    )
    lbl_chat_header.pack(fill=tk.X)

    # Divider for chat box
    divider = tk.Frame(right_frame, height=1, bg="#e2e8f0")
    divider.pack(fill=tk.X)

    # Chat area declaration

    chat_area = scrolledtext.ScrolledText(
        right_frame,
        wrap=tk.WORD,
        font=("Segoe UI", 10),
        bg="#fafafa",
        padx=10,
        pady=10,
        state="disabled",
    )

    chat_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 5))

    # display_message function

    def display_message(sender, message):
        chat_area.config(state="normal")  # unlock for inserting dialogues
        chat_area.insert(tk.END, f"{sender}: {message}\n")  # append at the end
        chat_area.config(state="disabled")  # re-lock
        chat_area.see(tk.END)  # auto-scroll the latest line

    # placeholder conversation

    # display_message(
    #     "[14:20] Minh", "Hey Quan, have you finished preparing the report file yet?"
    # )
    # display_message("[14:21] You", "I have, want me to send it to you?")
    # display_message("[System]", "Minh is ready to receive the file...")

    # ---------- Bottom layer (File sending and input bar)--------------
    bottom_container = tk.Frame(right_frame, bg="#ffffff")
    bottom_container.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

    # File-transfer-progress area
    progress_frame = tk.Frame(bottom_container, bg="#ffffff")
    progress_frame.pack(fill=tk.X, pady=(0, 6))
    progress_frame.pack_forget()

    lbl_progress = tk.Label(
        progress_frame,
        text="File transfer: network_report.pdf (70% - 2.1 MB /  3.0 MB)",
        font=("Segoe UI", 9, "italic"),
        bg="#ffffff",
        fg="#4a5568",
        anchor="w",
    )
    lbl_progress.pack(fill=tk.X)

    # Progression bar, determinate-mode (0 to 100 percent*)
    progress_bar = ttk.Progressbar(
        progress_frame, orient="horizontal", mode="determinate"
    )
    progress_bar.pack(fill=tk.X, pady=(2, 0))
    progress_bar["value"] = 70  # placeholder

    # User Input box and clickable buttons
    input_frame = tk.Frame(bottom_container, bg="#ffffff")
    input_frame.pack(fill=tk.X)

    # send_file function
    def send_file():
        if (
            current_chat_partner is None
        ):  # Situation where no peer has been chosen to chat
            display_message("[System]", "Please select a peer from the list first!")
            return
        filepath = filedialog.askopenfilename()
        if filepath:
            filename = filepath.split("/")[-1]
            display_message("[System]", f"Sending file: {filename}...")
            if on_send_file:
                partner_addr = peer_addresses.get(current_chat_partner)
                on_send_file(current_chat_partner, partner_addr, filepath)

    btn_file = tk.Button(
        input_frame,
        text="Send file",
        command=send_file,
        font=("Segoe UI", 9),
        bg="#edf2f7",
        relief=tk.GROOVE,
    )
    btn_file.pack(side=tk.LEFT, padx=(0, 6))

    # Text input box (one line)
    ent_message = tk.Entry(input_frame, font=("Segoe UI", 10))
    ent_message.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=3)

    # send_message function
    def send_message():
        if current_chat_partner is None:
            display_message("[System]", "Please select a peer from the list first!")
            return
        msg = ent_message.get().strip()
        if msg:
            display_message("[You]", msg)
            if current_chat_partner not in chat_histories:
                chat_histories[current_chat_partner] = []
            chat_histories[current_chat_partner].append(("[You]", msg))
            if on_send_msg:
                partner_addr = peer_addresses.get(current_chat_partner)
                on_send_msg(current_chat_partner, partner_addr, msg)
            ent_message.delete(0, tk.END)

    btn_send = tk.Button(
        input_frame,
        text="Send",
        command=send_message,
        font=("Segoe UI", 9, "bold"),
        bg="#2b6cb0",
        fg="#ffffff",
        padx=12,
        relief=tk.FLAT,
    )
    btn_send.pack(side=tk.RIGHT)

    # bind enter to execute send_message function
    ent_message.bind("<Return>", lambda event: send_message())

    # -------------- Chat history and peer selection --------------------

    # Implement *Dictionary* to store each peer's chat history
    # Structure: { "Name": [list of messages]}

    chat_histories = {  ## placeholders
        # "Minh": [
        #     (
        #         "[14:20] Minh",
        #         "Hey Quan, have you finished preparing the report file yet?",
        #     ),
        #     ("[14:21] You", "I have, want me to send it to you?"),
        #     ("[System]", "Minh is ready to receive the file..."),
        # ],
        # "Huy": [
        #     ("[13:00] Huy", "Chào Quan, chiều nay mấy giờ nhóm mình họp thế?"),
        #     ("[13:02] You", "Tầm 3 giờ chiều nhé Huy!"),
        # ],
    }

    peer_addresses = {}  # Save {"Name": (ip,port)} to know where to TCP is sent to

    # Variable to remember which person did user last open a conversation with
    current_chat_partner = None

    # on_select_partner function (mouse click event)
    def on_select_partner(event):
        nonlocal current_chat_partner

        # Take the index of the current selected line in Listbox
        selected_indices = peer_listbox.curselection()

        if not selected_indices:
            return

        index = selected_indices[0]  # Current index of the selected peer in Listbox

        # Extract string, for example: "Minh (192.168.1.12:6000) [Active] (2)"
        selected_text = peer_listbox.get(selected_indices[0])

        # Extract name (first index before the "space")
        partner_name = selected_text.split(" (")[0]
        current_chat_partner = partner_name

        # Remove *Unread* messages icon:
        # If it has unread messages icon, for example " (2) ", extract the "tail" of the string
        if "(" in selected_text and selected_text.endswith(")"):
            parts = selected_text.rsplit("(", 1)  # split from r to l
            clean_text = parts[0].rstrip()
            # Update in Listbox
            peer_listbox.delete(index)
            peer_listbox.insert(index, clean_text)
            peer_listbox.select_set(index)
            selected_text = clean_text

        # Update chat header label on the top on the chat box (current chatting with ... )
        lbl_chat_header.config(text=f"Currently chatting with: {selected_text}")

        # Clear the current chat area to blank (and to paste in current-selected-peer's chat history if there is any)
        chat_area.config(state="normal")
        chat_area.delete("1.0", tk.END)  # remove from line 1, 0th index
        chat_area.config(state="disabled")

        # Paste in chat history of selected peer (if there is any)
        if partner_name in chat_histories:
            for sender, msg in chat_histories[partner_name]:
                display_message(sender, msg)
        else:  # empty history
            chat_histories[partner_name] = []
            display_message(
                "[System]", f"Start a new conversation with {partner_name}."
            )

    # receive_message_from_peer function
    def receive_message_from_peer(sender_name, text):
        # Save the message into the sender's chat history with user
        if sender_name not in chat_histories:
            chat_histories[sender_name] = []
        chat_histories[sender_name].append((f"[{sender_name}]", text))

        # 1. If two peers are both chatting with each other
        if sender_name == current_chat_partner:
            display_message(f"[{sender_name}]", text)
        # 2. If user is chatting with another peer (or haven't selected a peer to chat with)
        else:
            # find the index of in selected_indices of the sender to update *unread* messages
            for i in range(peer_listbox.size()):
                item_text = peer_listbox.get(i)
                if item_text.startswith(sender_name):
                    # count current unread messages
                    unread_count = 1
                    if "(" in item_text and item_text.endswith(")"):
                        try:  # add 1 to old unread-messages count
                            old_count = int(item_text.rsplit("(", 1)[1].rstrip(")"))
                            unread_count = old_count + 1
                        except ValueError:
                            unread_count = 1
                        base_text = item_text.rsplit("(", 1)[0].rstrip()
                    else:
                        base_text = item_text

                    # Update unread message count
                    peer_listbox.delete(i)
                    peer_listbox.insert(i, f"{base_text} ({unread_count})")
                    break  # PREVENT CHECKING OTHER PEOPLE IF NAME IS FOUND

    # Bind left mouse click to Listbox elements
    peer_listbox.bind("<<ListboxSelect>>", on_select_partner)

    # ----------------- File sending progress controller -------------------

    def update_file_progress(filename, percent, is_done=False):
        # show progress bar if hidden
        progress_frame.pack(fill=tk.X, pady=(0, 6), before=input_frame)

        # update percentage-value on the progress bar (0 to 100)
        progress_bar["value"] = percent

        # update progress announcer
        if is_done or percent >= 100:
            lbl_progress.config(
                text=f"Finished sending file: {filename}, (100%)", fg="#2e7d32"
            )
            # use root.after to set a timer for 1 second then hide the progress bar
            root.after(1000, progress_frame.pack_forget)
        else:
            lbl_progress.config(text=f"Sending: {filename}, ({percent}%)", fg="#4a5568")

    # ------------------ Automatic peer-list updater --------------------

    def add_or_update_peer(name, ip, port, status):
        peer_addresses[name] = (ip, port)  # Actual IP/Port of each peer
        # Standardize string format, for example "Minh (192.168.1.12:6000) [Active]"
        new_entry = f"{name} ({ip}:{port}) [{status}]"

        # check if peer already existed  in Listbox
        found = False
        for i in range(peer_listbox.size()):
            item_text = peer_listbox.get(i)
            if item_text.startswith(name):
                # keep the unread messages (for example: (2))
                unread_part = ""
                if item_text.endswith(")") and not item_text.endswith(f"[{status}]"):
                    if "(" in item_text.rsplit("[", 1)[-1]:
                        unread_part = " " + item_text.rsplit(" ", 1)[-1]
                peer_listbox.delete(i)
                peer_listbox.insert(i, new_entry + unread_part)
                found = True
                break
        # if new LAN peer then add to bottom of Listbox
        if not found:
            peer_listbox.insert(tk.END, new_entry)
            display_message(
                "[System]", f"New peer joined the network: {name} ({ip}:{port})"
            )

    def remove_peer(name):
        for i in range(peer_listbox.size()):
            if peer_listbox.get(i).startswith(name):
                peer_listbox.delete(i)
                peer_addresses.pop(name, None)
                display_message("[System]", f"{name} has left the network.")
                break

    # ------------- Multi-threaded event queue ---------------------

    # Queue already initialized in start_gui()

    # check_queue() function every 100ms
    def on_window_close():
        if on_close:
            on_close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_window_close)

    def check_queue():
        # get all elements in queue
        while not event_queue.empty():
            try:
                # get an element out without stopping the program (get_nowait)
                # each element is a pair of (event_type, data)
                event_type, data = event_queue.get_nowait()

                # 1. Event from UDP flow: New LAN peer joins or status switch
                if event_type == "peer_update":
                    add_or_update_peer(
                        data["name"], data["ip"], data["port"], data["status"]
                    )
                # 2. Event from UDP flow: Connection lost over 10 seconds (Offline)
                elif event_type == "peer_offline":
                    remove_peer(data["name"])
                # 3. Event from TCP flow: New income message over TCP
                elif event_type == "new_message":
                    receive_message_from_peer(data["sender"], data["text"])
                # 4. Event from TCP flow: Update send/receive file progression
                elif event_type == "file_progress":
                    update_file_progress(
                        data["filename"], data["percent"], data.get("done", False)
                    )
                # 5. Error events (connection lost, connection refused, file error)
                elif event_type == "system_error":
                    display_message("[Error]", data["message"])
            except queue.Empty:
                break  # quit after having finished all elements in queue
        # auto-call this function again after 100ms
        root.after(100, check_queue)

        # # placeholder test-------------------------------------
        # root.after(
        #     2000,
        #     lambda: event_queue.put(
        #         (
        #             "peer_update",
        #             {"name": "Lan", "ip": "192.168.1.30", "port": 7000, "status": "Active"},
        #         )
        #     ),
        # )
        # # Sau 4 giây: Giả lập Bạn B nhận được tin nhắn từ "Huy" (bạn sẽ thấy số chưa đọc của Huy nhảy lên (1))
        # root.after(
        #     4000,
        #     lambda: event_queue.put(
        #         (
        #             "new_message",
        #             {"sender": "Huy", "text": "Quan ơi nhận được tin nhắn qua Queue chưa?"},
        #         )
        #     ),
        # )
        # # Sau 6 giây: Giả lập Bạn B đang truyền file đạt 80%
        # root.after(
        #     6000,
        #     lambda: event_queue.put(
        #         ("file_progress", {"filename": "demo_socket.zip", "percent": 80, "done": False})
        #     ),
        # )

    # Start the queue check
    check_queue()
    # Start the GUI
    root.mainloop()


if __name__ == "__main__":
    name, port = get_user_config()
    if name is not None:
        start_gui(name, port, queue.Queue())
