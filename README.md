# File Sync Tool

File Sync Tool is a Python-based desktop application that automatically synchronizes files from a source folder to one or more destination folders in real-time. It features a user-friendly GUI built with Tkinter, system tray integration, and persistent configuration. The app uses the `watchdog` library to monitor file system changes and supports recursive folder synchronization.

## Features

- **Real-Time Sync**: Automatically syncs files from a source folder to multiple destination folders when changes are detected.
- **GUI Interface**: Intuitive Tkinter-based interface for selecting source and destination folders.
- **System Tray Support**: Minimize the app to the system tray with options to restore or quit.
- **Persistent Configuration**: Saves source and destination folder settings to a JSON file for reuse.
- **Debounced Sync**: Prevents excessive syncing during rapid file changes using a debounce mechanism.
- **Cross-Platform**: Runs on Windows, macOS, and Linux (with appropriate dependencies).

## Requirements

- Python 3.6 or higher
- Required Python packages:
  - `watchdog`
  - `pystray`
  - `Pillow`
  - `tkinter` (usually included with Python)

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/file-sync-tool.git
   cd file-sync-tool
   ```

2. **Run the Application**:
   ```bash
   python FileSync.exe
   ```

## Usage

1. **Launch the App**:
   Run `FileSync.exe` to open the GUI.

2. **Select Source Folder**:
   Click "Browse" to choose the source folder you want to monitor for changes.

3. **Add Destination Folders**:
   Click "Add Destination Folder" to select one or more folders where files will be synced. Use the "-" button to remove destinations.

4. **Start Watching**:
   Click "Start Watching" to begin monitoring the source folder. Any changes (file additions, modifications, etc.) will trigger synchronization to all destination folders.

5. **Minimize to System Tray**:
   Minimize the window to hide it to the system tray. Right-click the tray icon to restore the window or quit the app.

6. **Stop Watching**:
   Click "Stop Watching" to pause file monitoring.

7. **View Logs**:
   The log panel displays sync activities, errors, and status updates.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Make your changes and commit (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

Please include tests and update documentation as needed.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Python](https://www.python.org/), [Tkinter](https://docs.python.org/3/library/tkinter.html), [watchdog](https://github.com/gorakhargosh/watchdog), [pystray](https://github.com/moses-palmer/pystray), and [Pillow](https://python-pillow.org/).
- Inspired by the need for simple, real-time file synchronization.

## Contact

For questions or support, please open an issue on GitHub or contact cysyiu@gmail.com.

---

Happy syncing! 🚀
