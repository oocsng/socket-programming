# Tkinter GUI and message queue
import tkinter as tk

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
# Stop left panel from auto-minizing
left_frame.pack_propagate(False)

# Create right panel
right_frame = tk.Frame(root, bg="#ffffff")
right_frame.pack(side=tk.RIGHT, fill="both", expand=True)

# Start the GUI
root.mainloop()
