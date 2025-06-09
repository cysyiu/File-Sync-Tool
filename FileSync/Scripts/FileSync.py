import os
import sys
import json
import shutil
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw, ImageTk

# ----------------------------
# CONFIGURATION FILE HANDLING
# ----------------------------
CONFIG_FILE = "filesync_config.json"

def save_config(source, destinations):
    """Save configuration to a JSON file."""
    config = {
        "source": source,
        "destinations": destinations
    }
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        print("Configuration saved.")
    except Exception as e:
        print(f"Error saving configuration: {e}")

def load_config():
    """Load configuration from a JSON file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            return config.get("source", ""), config.get("destinations", [])
        except Exception as e:
            print(f"Error loading configuration: {e}")
    return "", []



# ----------------------------
# Debounced File System Handler
# ----------------------------
class DebounceHandler(FileSystemEventHandler):
    """
    An event handler that debounces rapid file system events.
    When activity settles, it triggers the provided callback.
    """
    def __init__(self, callback, debounce_interval=0.5):
        super().__init__()
        self.callback = callback
        self.debounce_interval = debounce_interval
        self.event_timer = None

    def on_any_event(self, event):
        if self.event_timer:
            self.event_timer.cancel()
        self.event_timer = threading.Timer(self.debounce_interval, self.trigger_callback)
        self.event_timer.start()

    def trigger_callback(self):
        self.callback()

# ----------------------------
# Synchronization Logic
# ----------------------------
def sync_source_to_dest(source, destinations, log_callback):
    """
    Walks through the source folder recursively,
    copying each file to every destination folder, preserving folder structure.
    """
    if not source or not destinations:
        log_callback("Source or destination not specified.")
        return

    log_callback("Starting sync...")
    for root, dirs, files in os.walk(source):
        rel_root = os.path.relpath(root, source)
        for dst in destinations:
            target_dir = os.path.join(dst, rel_root)
            if not os.path.exists(target_dir):
                try:
                    os.makedirs(target_dir)
                    log_callback(f"Created directory: {target_dir}")
                except Exception as ex:
                    log_callback(f"Error creating directory {target_dir}: {ex}")
        for f in files:
            source_file = os.path.join(root, f)
            for dst in destinations:
                target_file = os.path.join(dst, rel_root, f)
                try:
                    shutil.copy2(source_file, target_file)
                    log_callback(f"Copied: {source_file} -> {target_file}")
                except Exception as ex:
                    log_callback(f"Error copying {source_file} to {target_file}: {ex}")
    log_callback("Sync complete.")

# ----------------------------
# Tkinter App with System Tray Integration and Auto-Save Configuration
# ----------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Sync Tool")
        self.geometry("700x500")
        
        # Use Pillow to load the icon (ICO or PNG) for the window
        try:
            image = Image.open(r"C:\Users\samyiu\Desktop\Tasks\File Sync\FileSync_Icon.ico")
            self.icon_img = ImageTk.PhotoImage(image)
            self.iconphoto(True, self.icon_img)
        except Exception as e:
            print(f"Error loading icon for window: {e}")

        # Variables for source and destinations; load previous config if exists.
        self.source_dir, self.dest_dirs = load_config()
        
        # Watchdog observer (initialized later)
        self.observer = None

        # System tray icon object
        self.tray_icon = None

        # Set up the GUI
        self.create_widgets()

        # If configuration is loaded, update the UI.
        if self.source_dir:
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, self.source_dir)
        self.refresh_destinations()
        
        # Bind the minimize event (iconify) to hide the window into the system tray
        self.bind("<Unmap>", self.on_minimize)

        # Use protocol for clean exit
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        padding = {"padx": 5, "pady": 5}

        # Source selection row
        source_frame = tk.Frame(self)
        source_frame.pack(fill=tk.X, **padding)
        tk.Label(source_frame, text="Source Folder:").pack(side=tk.LEFT)
        self.source_entry = tk.Entry(source_frame, width=50)
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, **padding)
        tk.Button(source_frame, text="Browse", command=self.browse_source).pack(side=tk.LEFT, **padding)

        # Destination selection row using a container frame
        dest_container = tk.Frame(self)
        dest_container.pack(fill=tk.BOTH, expand=False, **padding)
        tk.Label(dest_container, text="Destination Folders:").pack(anchor=tk.W)
        # Container to hold each destination entry with its "-" removal button.
        self.destinations_container = tk.Frame(dest_container)
        self.destinations_container.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        tk.Button(dest_container, text="Add Destination Folder", command=self.add_destination).pack(**padding)

        # Control buttons
        controls_frame = tk.Frame(self)
        controls_frame.pack(fill=tk.X, **padding)
        self.start_button = tk.Button(controls_frame, text="Start Watching", command=self.start_watching)
        self.start_button.pack(side=tk.LEFT, **padding)
        self.stop_button = tk.Button(controls_frame, text="Stop Watching", command=self.stop_watching, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, **padding)
        
        # Log listbox
        log_frame = tk.Frame(self)
        log_frame.pack(fill=tk.BOTH, expand=True, **padding)
        tk.Label(log_frame, text="Log:").pack(anchor=tk.W)
        self.log_listbox = tk.Listbox(log_frame, height=15)
        self.log_listbox.pack(fill=tk.BOTH, expand=True, **padding)

    def refresh_destinations(self):
        """Repopulate the destination container with current destination folders."""
        # Clear existing widgets in the container.
        for widget in self.destinations_container.winfo_children():
            widget.destroy()
        # Create a frame for each destination with a remove button.
        for index, dest in enumerate(self.dest_dirs):
            frame = tk.Frame(self.destinations_container)
            frame.pack(fill=tk.X, pady=2)
            label = tk.Label(frame, text=dest, anchor="w")
            label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            remove_button = tk.Button(frame, text="-", command=lambda i=index: self.remove_destination(i), width=2)
            remove_button.pack(side=tk.RIGHT)

    def remove_destination(self, index):
        """Remove a destination folder by index and update the configuration."""
        try:
            dest = self.dest_dirs.pop(index)
            self.log(f"Removed destination folder: {dest}")
            self.refresh_destinations()
            save_config(self.source_dir, self.dest_dirs)
        except Exception as e:
            self.log(f"Error removing destination: {e}")

    def log(self, message):
        timestamp = time.strftime('%H:%M:%S')
        self.log_listbox.insert(tk.END, f"{timestamp} - {message}")
        self.log_listbox.yview(tk.END)

    def browse_source(self):
        path = filedialog.askdirectory(title="Select Source Folder")
        if path:
            self.source_dir = path
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, path)
            self.log(f"Selected source folder: {path}")
            save_config(self.source_dir, self.dest_dirs)

    def add_destination(self):
        path = filedialog.askdirectory(title="Select Destination Folder")
        if path:
            if path not in self.dest_dirs:
                self.dest_dirs.append(path)
                self.log(f"Added destination folder: {path}")
                self.refresh_destinations()
                save_config(self.source_dir, self.dest_dirs)
            else:
                messagebox.showinfo("Duplicate", "Destination already added.")

    def start_watching(self):
        if not self.source_dir:
            messagebox.showerror("Error", "Please select a source folder.")
            return
        if not self.dest_dirs:
            messagebox.showerror("Error", "Please add at least one destination folder.")
            return

        self.log("Starting file system watcher...")
        event_handler = DebounceHandler(callback=self.debounced_sync, debounce_interval=0.5)
        self.observer = Observer()
        self.observer.schedule(event_handler, path=self.source_dir, recursive=True)
        self.observer.start()

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.log("Watcher started.")

    def stop_watching(self):
        if self.observer:
            self.log("Stopping watcher...")
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.log("Watcher stopped.")

    def debounced_sync(self):
        self.after(0, self.perform_sync)

    def perform_sync(self):
        sync_source_to_dest(self.source_dir, self.dest_dirs, self.log)

    def create_tray_icon(self):
        try:
            image = Image.open(r"C:\Users\samyiu\Desktop\Tasks\File Sync\FileSync_Icon.ico")
        except Exception as e:
            self.log(f"Error loading icon for tray: {e}")
            image = Image.new("RGB", (64, 64), color=(0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rectangle((8, 8, 56, 56), fill=(255, 255, 255))
        menu = (
            item("Restore", self.restore_window),
            item("Quit", self.quit_app)
        )
        self.tray_icon = pystray.Icon("File Sync Tool", image, "File Sync Tool", menu)

    def on_minimize(self, event):
        if self.state() == "iconic":
            self.withdraw()
            #self.log("Application minimized to tray.")
            self.create_tray_icon()
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def restore_window(self, icon=None, item=None):
        self.deiconify()
        #self.log("Application restored from tray.")
        if self.tray_icon:
            self.tray_icon.stop()

    def quit_app(self, icon=None, item=None):
        self.on_close()

    def on_close(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()

if __name__ == "__main__":
    app = App()
    # Auto-start file sync if there is a valid configuration.
    if app.source_dir and app.dest_dirs:
        app.start_watching()
    app.mainloop()
