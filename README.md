**File Sync Tool**

**File Sync Tool** is a lightweight, automated file synchronization application built using Python, Tkinter, and Watchdog. It monitors a designated source folder and efficiently syncs changes to multiple destination folders in real time. The tool features a system tray integration for background operation and auto-start functionality when Windows boots.

**Features**
- Real-time File Sync: Monitors a source folder and automatically syncs changes to multiple destinations.
- Minimalistic UI: Easy-to-use graphical interface built with Tkinter.
- System Tray Support: Runs silently in the tray with restore and quit options.
- Auto-Save Configuration: Stores source and destination folder selections in a JSON file.
- Automatic Sync on Startup: Starts file sync automatically if a valid configuration exists.
- Dynamic Folder Management: Easily add or remove destination folders with a "-" button.

**Installation**
Clone the repository:

bash
git clone https://github.com/cysyiu/FileSyncTool.git
cd FileSyncTool
Install dependencies:

bash
pip install -r requirements.txt
Run the application:

bash
python FileSync.py
Packaging with PyInstaller
To create an executable with your custom icon:

bash
pyinstaller --onefile --windowed --icon="FileSync_Icon.ico" FileSync.py
Ensure FileSync_Icon.ico is in the same directory.

**Dependencies**

- Python 3.x
- tkinter
- watchdog
- pystray
- PIL (Pillow)

**License**

This project is licensed under MIT License.
