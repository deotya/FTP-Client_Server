# File Manager with Integrated FTP Client

A graphical application for managing files and directories, developed in Python with PyQt5. Includes an integrated FTP client that allows managing files both on the local system and on remote FTP servers.

## Features

- **Local filesystem navigation**:
  - Intuitive navigation through directory structure
  - Quick file content preview
  - File and directory search

- **Operations on local files**:
  - Create new directories
  - Copy and paste files and directories
  - Rename and delete files and directories
  - Open files with default applications

- **Integrated FTP client**:
  - Connect to FTP servers with authentication
  - Navigate remote directory structure
  - Upload and download files
  - Create and delete directories on the FTP server

- **Easy transfer between local system and FTP**:
  - Direct copying between panels with a single click
  - Simultaneous view of local and remote content

## Project Structure

The project is organized in a modular way to facilitate maintenance and extensibility:

```
/
├── main.py             # Application entry point
├── requirements.txt    # Project dependencies
├── setup.bat           # Setup script for Windows
├── ftp_users.db        # FTP users database
├── ftp_client/         # File manager and FTP client
│   ├── __init__.py     # Package initialization
│   ├── ftp_client.py   # FTP client implementation
│   ├── sftp_client.py  # SFTP client implementation
│   ├── file_manager.py # File manager core functionality
│   ├── ui/             # UI packages and modules
│   │   ├── __init__.py
│   │   ├── file_manager_window.py  # Main window
│   │   ├── ftp_panel.py            # FTP panel
│   │   ├── local_panel.py          # Local system panel
│   │   ├── connection_dialog.py    # FTP connection dialog
│   │   ├── file_system_model.py    # File system model
│   │   └── common/                 # Common components
│   │       ├── __init__.py
│   │       └── styles.py           # Common CSS styles
│   └── utils/          # Utility functions
│       ├── __init__.py
│       ├── file_utils.py           # File operations utilities
│       └── database.py             # Database operations
├── ftp_server/         # FTP server implementation
│   ├── ftp_server.py              # FTP server core
│   ├── ftp_server_ui.py           # FTP server UI
│   ├── user_manager.py            # User management
│   └── WindowsRootFS              # Windows root filesystem config
└── logs/               # Application logs
    └── events.log      # Event log file
```

## Requirements

- Python 3.7 or newer
- PyQt5 5.15.6 or newer
- pyftpdlib 1.5.6 or newer
- paramiko 3.5.0 or newer (for SFTP support)
- cryptography 45.0.0 or newer (for secure authentication)
- bcrypt>=4.0.0 (for password hashing)
- pywin32 228 or newer (for Windows only - provides win32api)

## Installation

### From source (recommended for development)

1. Clone or download this repository

2. create enviroment
``` 
python -m venv .venv
.venv\Scripts\Activate
```
3. Select the virtual environment in the code editor

4. Install dependencies:
    ```
   pip install -r requirements.txt
   ```
5. Run the application:
   ```
   python main.py
   ```

### Installation as a package


Install the package in development mode:
   ```
   pip install -e .
   ```

After installation, you can run the application using the command:
```
file_manager
```
## Usage

### Local system navigation
- Use the left panel to navigate the local file system
- Double-click on a directory to open it
- Enter a path in the "Local site" field and press Enter to navigate directly

### FTP Connection
- Click on the "Connect FTP" button in the right panel
- Fill in the connection details (server, port, user, password)
- After connecting, use the right panel to navigate on the FTP server

### File transfer
- Select a file in the local panel and click the "➡" button to upload it to FTP
- Select a file in the FTP panel and click the "⬅" button to download it locally

## Contribute

Contributions are welcome! If you want to contribute to this project:

1. Fork the repository
2. Create a branch for your feature or fix
3. Submit a pull request with your changes

## License

This project is licensed under the terms of the MIT license. 