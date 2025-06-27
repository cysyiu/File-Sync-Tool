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
import atexit
import psutil

def resource_path(relative_path):
    """Get the absolute path to a resource, works for development and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ----------------------------
# Single Instance Check
# ----------------------------
LOCK_FILE = "filesync_lock.pid"

def is_instance_running():
    """Check if another instance is running by checking the lock file and process."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                return True
            os.remove(LOCK_FILE)  # Clean up stale lock file
        except (ValueError, psutil.Error):
            os.remove(LOCK_FILE)  # Clean up invalid lock file
    return False

def create_lock_file():
    """Create a lock file with the current process ID."""
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    atexit.register(remove_lock_file)

def remove_lock_file():
    """Remove the lock file when the application exits."""
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

# ----------------------------
# CONFIGURATION FILE HANDLING
# ----------------------------
CONFIG_FILE = "filesync_config.json"

def save_config(source, destinations, delay):
    """Save configuration to a JSON file."""
    config = {
        "source": source,
        "destinations": destinations,
        "delay": delay
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
            return config.get("source", ""), config.get("destinations", []), config.get("delay", 1.0)
        except Exception as e:
            print(f"Error loading configuration: {e}")
    return "", [], 1.0

# ----------------------------
# Debounced File System Handler
# ----------------------------
class DebounceHandler(FileSystemEventHandler):
    def __init__(self, callback, delay=1.0):
        super().__init__()
        self.callback = callback
        self.delay = delay
        self.event_timer = None
        self.last_event_time = 0
        self.lock = threading.Lock()

    def on_any_event(self, event):
        with self.lock:
            current_time = time.time()
            # Only start a new timer if none is active or the previous delay has completed
            if self.event_timer is None or not self.event_timer.is_alive():
                self.last_event_time = current_time
                self.event_timer = threading.Timer(self.delay, self.trigger_callback)
                self.event_timer.start()

    def trigger_callback(self):
        with self.lock:
            self.callback()
            self.event_timer = None  # Reset timer after callback

# ----------------------------
# Synchronization Logic
# ----------------------------
def sync_source_to_dest(source, destinations, log_callback):
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
# Tkinter App with System Tray Integration
# ----------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Sync Tool")
        self.geometry("700x500")
        
        try:
            image = Image.open(resource_path("FileSync_Icon.ico"))
            self.icon_img = ImageTk.PhotoImage(image)
            self.iconphoto(True, self.icon_img)
        except Exception as e:
            print(f"Error loading icon for window: {e}")

        self.source_dir, self.dest_dirs, self.delay = load_config()
        self.observer = None
        self.tray_icon = None
        self.ui_initialized = False

        self.create_widgets()
        if self.source_dir:
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, self.source_dir)
        self.refresh_destinations()
        self.delay_spinbox.delete(0, tk.END)
        self.delay_spinbox.insert(0, str(self.delay))
        
        self.bind("<Unmap>", self.on_minimize)
        self.bind("<Map>", self.on_map)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_map(self, event):
        """Called when the window is mapped (visible). Start watching if needed."""
        if not self.ui_initialized:
            self.ui_initialized = True
            if self.source_dir and self.dest_dirs:
                self.start_watching()

    def create_widgets(self):
        padding = {"padx": 5, "pady": 5}
        source_frame = tk.Frame(self)
        source_frame.pack(fill=tk.X, **padding)
        tk.Label(source_frame, text="Source Folder:").pack(side=tk.LEFT)
        self.source_entry = tk.Entry(source_frame, width=50)
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, **padding)
        tk.Button(source_frame, text="Browse", command=self.browse_source).pack(side=tk.LEFT, **padding)

        dest_container = tk.Frame(self)
        dest_container.pack(fill=tk.BOTH, expand=False, **padding)
        tk.Label(dest_container, text="Destination Folders:").pack(anchor=tk.W)
        self.destinations_container = tk.Frame(dest_container)
        self.destinations_container.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        tk.Button(dest_container, text="Add Destination Folder", command=self.add_destination).pack(**padding)

        controls_frame = tk.Frame(self)
        controls_frame.pack(fill=tk.X, **padding)
        self.start_button = tk.Button(controls_frame, text="Start Watching", command=self.start_watching)
        self.start_button.pack(side=tk.LEFT, **padding)
        self.stop_button = tk.Button(controls_frame, text="Stop Watching", command=self.stop_watching, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, **padding)
        # Add spacer to push delay Spinbox to the right
        tk.Label(controls_frame, text="").pack(side=tk.RIGHT, fill=tk.X, expand=True)
        tk.Label(controls_frame, text="Delay (s):").pack(side=tk.RIGHT, **padding)
        self.delay_spinbox = tk.Spinbox(
            controls_frame,
            from_=0.1,
            to=300.0,  # Increased max delay to support up to 5 minutes
            increment=0.1,
            width=5,
            command=self.update_delay
        )
        self.delay_spinbox.pack(side=tk.RIGHT, **padding)
        # Bind Return key to update delay when typing
        self.delay_spinbox.bind("<Return>", lambda event: self.update_delay())

        log_frame = tk.Frame(self)
        log_frame.pack(fill=tk.BOTH, expand=True, **padding)
        tk.Label(log_frame, text="Log:").pack(anchor=tk.W)
        self.log_listbox = tk.Listbox(log_frame, height=15)
        self.log_listbox.pack(fill=tk.BOTH, expand=True, **padding)

    def log(self, message):
        """Log a message to the listbox, with fallback to console if UI not ready."""
        try:
            timestamp = time.strftime('%H:%M:%S')
            self.log_listbox.insert(tk.END, f"{timestamp} - {message}")
            self.log_listbox.yview(tk.END)
        except AttributeError:
            print(f"Log (UI not ready): {message}")

    def update_delay(self):
        """Update the delay value from the Spinbox and save to config."""
        try:
            new_delay = float(self.delay_spinbox.get())
            if new_delay < 0.1:
                new_delay = 0.1
                self.delay_spinbox.delete(0, tk.END)
                self.delay_spinbox.insert(0, str(new_delay))
            self.delay = new_delay
            save_config(self.source_dir, self.dest_dirs, self.delay)
            self.log(f"Delay updated to {self.delay} seconds")
        except ValueError:
            self.log("Invalid delay value entered; reverting to previous value")
            self.delay_spinbox.delete(0, tk.END)
            self.delay_spinbox.insert(0, str(self.delay))

    def refresh_destinations(self):
        for widget in self.destinations_container.winfo_children():
            widget.destroy()
        for index, dest in enumerate(self.dest_dirs):
            frame = tk.Frame(self.destinations_container)
            frame.pack(fill=tk.X, pady=2)
            label = tk.Label(frame, text=dest, anchor="w")
            label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            remove_button = tk.Button(frame, text="-", command=lambda i=index: self.remove_destination(i), width=2)
            remove_button.pack(side=tk.RIGHT)

    def remove_destination(self, index):
        try:
            dest = self.dest_dirs.pop(index)
            self.log(f"Removed destination folder: {dest}")
            self.refresh_destinations()
            save_config(self.source_dir, self.dest_dirs, self.delay)
        except Exception as e:
            self.log(f"Error removing destination: {e}")

    def browse_source(self):
        path = filedialog.askdirectory(title="Select Source Folder")
        if path:
            self.source_dir = path
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, path)
            self.log(f"Selected source folder: {path}")
            save_config(self.source_dir, self.dest_dirs, self.delay)

    def add_destination(self):
        path = filedialog.askdirectory(title="Select Destination Folder")
        if path:
            if path not in self.dest_dirs:
                self.dest_dirs.append(path)
                self.log(f"Added destination folder: {path}")
                self.refresh_destinations()
                save_config(self.source_dir, self.dest_dirs, self.delay)
            else:
                messagebox.showinfo("Duplicate", "Destination already added.")

    def start_watching(self):
        if not self.ui_initialized:
            self.after(1000, self.start_watching)  # Retry after 1 second
            return
        if not self.source_dir:
            messagebox.showerror("Error", "Please select a source folder.")
            return
        if not self.dest_dirs:
            messagebox.showerror("Error", "Please add at least one destination folder.")
            return
        self.log("Starting file system watcher...")
        event_handler = DebounceHandler(
            callback=self.debounced_sync,
            delay=self.delay
        )
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
            image = Image.open(resource_path("FileSync_Icon.ico"))
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
            if not self.tray_icon:
                self.create_tray_icon()
                if self.tray_icon:
                    threading.Thread(target=self.tray_icon.run, daemon=True).start()
                else:
                    self.log("Failed to create system tray icon.")

    def restore_window(self, icon=None, item=None):
        self.deiconify()
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def quit_app(self, icon=None, item=None):
        self.on_close()

    def on_close(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        if self.tray_icon:
            self.tray_icon.stop()
        remove_lock_file()
        self.destroy()

if __name__ == "__main__":
    if is_instance_running():
        print("Another instance is already running.")
        sys.exit(0)
    create_lock_file()
    app = App()
    app.mainloop()
