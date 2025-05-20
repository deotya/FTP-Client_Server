"""
Script for creating the executable with PyInstaller for FTP Client
"""

import os
import shutil
import subprocess

def build_client():
    """Builds the executable for the client"""
    print("Building FTP Client...")
    subprocess.run([
        'pyinstaller',
        '--name=FTP_Client',
        # Do not use the icon if it does not exist
        # '--icon=ftp_client/ui/resources/client_icon.ico',
        '--windowed',
        '--onedir',  # Use onedir to create a directory with all components
        '--clean',
        # Explicitly include necessary packages
        '--hidden-import=PyQt5',
        '--hidden-import=PyQt5.QtWidgets',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=pyftpdlib',
        '--hidden-import=paramiko',
        '--hidden-import=cryptography',
        '--hidden-import=bcrypt',
        '--hidden-import=colorama',
        'main.py'
    ], check=True)

def cleanup():
    """Cleans up temporary directories"""
    print("Cleaning up temporary files...")
    for path in ['build', '__pycache__']:
        if os.path.exists(path):
            shutil.rmtree(path)
    
    spec_files = [f for f in os.listdir('.') if f.endswith('.spec')]
    for file in spec_files:
        os.remove(file)

def main():
    # Build the executable for the client
    build_client()
    
    # Clean up temporary files
    cleanup()
    
    print("\nThe executable has been created in the 'dist' directory")
    print("To create an installer, use Inno Setup with the 'client_installer.iss' file")

if __name__ == "__main__":
    main() 