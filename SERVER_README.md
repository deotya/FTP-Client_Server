# Creating an Installation Package for FTP Server

This document explains the steps to create an installation package for the FTP Server application, which will automatically install the server on disk C in Windows.

## Prerequisites

1. Python 3.7 or newer
2. Python virtual environment (recommended)
3. The following dependencies:
   - PyQt5>=5.15.6
   - pyftpdlib==1.5.9
   - pywin32==306
4. [Inno Setup](https://jrsoftware.org/isdl.php) - for creating the Windows installer

## Steps for Creating the Installation Package

### 1. Install Dependencies

```
pip install PyQt5>=5.15.6 pyftpdlib==1.5.9 pywin32==306 pyinstaller
```

### 2. Generate the Executable with PyInstaller

Run the build_server.py script to create the executable for the server:

```
python build_server.py
```

This script will create the `dist\FTP_Server` directory containing all the files needed to run the application.

### 3. Create the Installer with Inno Setup

1. Install [Inno Setup](https://jrsoftware.org/isdl.php)
2. Open the `server_installer.iss` file with Inno Setup Compiler
3. Press the "Compile" button (F9) to create the installer

The installer will be created in the `installer` directory with the name `FTP_Server_Setup.exe`.

### 4. Distributing the Installer

The created installation package can now be distributed to users. Upon installation:

- The application will be installed by default in the `C:\FTP Server` directory
- Shortcuts will be created in the Start menu
- Optionally, a shortcut can be created on the desktop

## Customizing the Installation Package

You can customize the installer by modifying the `server_installer.iss` file. Common options:

- Change application details (name, version, publisher)
- Modify the default installation directory
- Add custom images and icons
- Add additional configuration steps

## Important Notes

- Make sure you use the correct versions of the libraries (PyQt5>=5.15.6, pyftpdlib==1.5.9, pywin32==306)
- Test the installer on a clean system to verify that all components are installed correctly 