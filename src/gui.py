# Tkinter GUI and message queue
import tkinter as tk
from tkinter import ttk, scrolledtext, ttk, filedialog

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
    profile_frame, text="Name: Quan (Port: 5000)", font=("Segoe UI", 10), bg="#f0f2f5"
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
        status_var.set("Status: Away")
        lbl_status.config(fg="#e65100")
        btn_toggle.config(text="Switch to Active")
    else:
        status_var.set("Status: Active")
        lbl_status.config(fg="#2e7d32")
        btn_toggle.config(text="Switch to Away")


btn_toggle = tk.Button(
    profile_frame, text="Switch to Away", command=toggle_status, font=("Segoe UI", 9)
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
peer_listbox.insert(tk.END, "Minh (192.168.1.12:6000) [Active] (2)")
peer_listbox.insert(tk.END, "Huy (192.168.1.20:5000) [Away]")

# ----------- Right frame: Chat box ---------------------

# Placeholder for display name and information of the peer currently chatting with (Current chatting with: Name (ip:tcp_port) [Status])
lbl_chat_header = tk.Label(
    right_frame,
    text="Currently chatting with: Minh (192.168.1.12:6000) [Active]",
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

display_message(
    "[14:20] Minh", "Hey Quan, have you finished preparing the report file yet?"
)
display_message("[14:21] You", "I have, want me to send it to you?")
display_message("[System]", "Minh is ready to receive the file...")

# ---------- Bottom layer (File sending and input bar)--------------
bottom_container = tk.Frame(right_frame, bg="#ffffff")
bottom_container.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

# File-transfer-progress area
progress_frame = tk.Frame(bottom_container, bg="#ffffff")
progress_frame.pack(fill=tk.X, pady=(0, 6))


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
progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
progress_bar.pack(fill=tk.X, pady=(2, 0))
progress_bar["value"] = 70  # placeholder

# User Input box and clickable buttons
input_frame = tk.Frame(bottom_container, bg="#ffffff")
input_frame.pack(fill=tk.X)


# send_file function
def send_file():
    filepath = filedialog.askopenfilename()
    if filepath:
        filename = filepath.split("/")[-1]  # grab file name
        display_message("[System]", f"You selected file: {filename}")


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
    msg = ent_message.get().strip()
    if msg:
        display_message("[You]", msg)
        ent_message.delete(0, tk.END)  # delete message box for next input


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

# Start the GUI
root.mainloop()
