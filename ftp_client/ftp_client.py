"""
FTP Client for the File Manager application
"""

import ftplib
import os
import re
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import threading
import socket
import time
from ftp_client.utils.logger import FTPLogger

class FTPClient(QObject):
    """Class for managing FTP connections"""
    
    # Signal definitions for communication with the graphical interface
    connected = pyqtSignal(str)
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    directory_listed = pyqtSignal(list)
    file_downloaded = pyqtSignal(str)
    file_uploaded = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.ftp = None
        self.is_connected = False
        self.current_directory = "/"
        self.active_threads = []  # List to hold references to active threads
        self.connection_id = None  # Connection ID from the database
        self.host = None
        self.port = None
        self.logger = FTPLogger()  # Inițializează logger-ul
        
    def __del__(self):
        """Destructor to ensure all threads are properly stopped"""
        try:
            for thread in self.active_threads:
                if thread.isRunning():
                    thread.wait()  # Wait for the thread to finish
        except:
            pass
        
        # Închide logger-ul când obiectul este distrus
        if hasattr(self, 'logger'):
            self.logger.close()
        
    def connect(self, host, port=21, username="anonymous", password="", timeout=30):
        """
        Connect to the FTP server
        Returns True if connected successfully, False otherwise
        """
        self.logger.start_logging(host, port, username)
        self.logger.log(f"FTPClient.connect: Attempting to connect to {host}:{port} with {username}")
        
        try:
            # Close any existing connection
            if self.ftp:
                try:
                    self.logger.log(f"FTPClient.connect: Closing existing connection before connecting to {host}")
                    self.ftp.quit()
                except:
                    try:
                        self.ftp.close()
                    except:
                        pass
                self.ftp = None
                self.is_connected = False
                # Curățăm și thread-urile active
                for thread in self.active_threads[:]:
                    try:
                        if thread.isRunning():
                            thread.wait(500)  # Wait up to 0.5 seconds
                        self.active_threads.remove(thread)
                    except:
                        pass
                # Golim lista de thread-uri active
                self.active_threads.clear()
            
            # Salvăm host și port pentru utilizare ulterioară
            self.host = host
            self.port = port
            
            # Create a new connection
            self.ftp = ftplib.FTP()
            self.ftp.connect(host, port, timeout)
            
            # Attempt to authenticate
            try:
                self.ftp.login(username, password)
                self.is_connected = True
                self.current_directory = self.ftp.pwd()
                
                # Set passive mode
                self.ftp.set_pasv(True)
                
                # Verificăm conexiunea pentru a ne asigura că este încă activă
                try:
                    self.ftp.voidcmd("NOOP")
                    self.logger.log(f"FTPClient.connect: Connection check passed for {host}")
                except:
                    self.logger.log(f"FTPClient.connect: Connection check failed for {host}, reconnecting...")
                    try:
                        self.ftp.close()
                    except:
                        pass
                    # Încercăm să reconectăm
                    self.ftp = ftplib.FTP()
                    self.ftp.connect(host, port, timeout)
                    self.ftp.login(username, password)
                    self.ftp.set_pasv(True)
                    self.current_directory = self.ftp.pwd()
                
                self.logger.log(f"FTPClient.connect: Successfully connected to {host}, current directory: {self.current_directory}")
                self.connected.emit(f"Connected to {host}:{port}")
                return True
            except ftplib.error_perm as e:
                self.logger.log(f"FTPClient.connect: Authentication error: {str(e)}")
                # Check if the error is 530 (authentication failed)
                if "530" in str(e):
                    self.error.emit(f"Authentication failed: incorrect username or password")
                else:
                    self.error.emit(f"Permission error: {str(e)}")
                self.disconnect()
                return False
                
        except socket.gaierror:
            error_msg = f"Could not resolve hostname: {host}"
            self.logger.log(f"FTPClient.connect: Error: {error_msg}")
            self.error.emit(error_msg)
            return False
        except socket.timeout:
            error_msg = f"Connection timed out. Check the address and port."
            self.logger.log(f"FTPClient.connect: Error: {error_msg}")
            self.error.emit(error_msg)
            return False
        except ConnectionRefusedError:
            error_msg = f"Connection refused. Check if the FTP server is running."
            self.logger.log(f"FTPClient.connect: Error: {error_msg}")
            self.error.emit(error_msg)
            return False
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            self.logger.log(f"FTPClient.connect: Error: {error_msg}")
            self.error.emit(error_msg)
            return False
            
    def disconnect(self):
        """Disconnect from the FTP server"""
        if self.ftp and self.is_connected:
            self.logger.log("FTPClient.disconnect: Disconnecting from server")
            try:
                self.ftp.quit()
            except:
                self.ftp.close()
            finally:
                self.is_connected = False
                self.ftp = None
                self.disconnected.emit()
                self.logger.log("FTPClient.disconnect: Disconnected successfully")
                # Închide logger-ul la deconectare
                self.logger.close()
                
    def list_directory(self, directory=None):
        """List files in the current or specified directory"""
        if not self.is_connected:
            self.error.emit("You are not connected to an FTP server")
            return []
            
        try:
            if directory:
                self.logger.log(f"FTPClient: Listing specified directory: {directory}")
                self.ftp.cwd(directory)
                self.current_directory = self.ftp.pwd()
                self.logger.log(f"FTPClient: Current directory updated: {self.current_directory}")
            
            # Get the list of files and directories
            file_list = []
            self.ftp.retrlines('LIST', lambda x: file_list.append(x))
            
            # Handle cases differently based on the current directory
            if self.current_directory == '/':
                # In the root directory, drives are displayed
                parsed_list = self._parse_root_directory(file_list)
            else:
                # We are in a normal directory
                parsed_list = self._parse_regular_directory(file_list)
                    
            self.directory_listed.emit(parsed_list)
            self.logger.log(f"FTPClient: Listed directory {self.current_directory} with {len(parsed_list)} items")
            return parsed_list
        except ftplib.error_perm as e:
            error_msg = str(e)
            # Check if the message is actually a confirmation (250 Command successful)
            if "250" in error_msg and ("current directory" in error_msg.lower() or "successful" in error_msg):
                self.logger.log(f"FTPClient: Confirmation message received (not an error): {error_msg}")
                # Try again to list the current directory
                try:
                    # Get the list of files and directories again
                    file_list = []
                    self.ftp.retrlines('LIST', lambda x: file_list.append(x))
                    
                    # Parse the list and emit the signal
                    parsed_list = self._parse_regular_directory(file_list)
                    self.directory_listed.emit(parsed_list)
                    self.logger.log(f"FTPClient: Listed directory {self.current_directory} with {len(parsed_list)} items (second attempt)")
                    return parsed_list
                except Exception as inner_e:
                    self.logger.log(f"FTPClient: Secondary error during listing: {str(inner_e)}")
                    self.error.emit(f"Error listing directory: {str(inner_e)}")
                    return []
            else:
                self.logger.log(f"FTPClient: Permission error during listing: {error_msg}")
                self.error.emit(f"Error listing directory: {error_msg}")
                return []
        except Exception as e:
            error_msg = f"Error listing directory: {str(e)}"
            self.logger.log(f"FTPClient: {error_msg}")
            self.error.emit(error_msg)
            return []
            
    def _parse_root_directory(self, file_list):
        """Parse a root directory (drives)"""
        parsed_list = []
        
        # First attempt: look for drives in standard format
        for item in file_list:
            parts = item.split()
            if not parts:
                continue
                
            name = parts[-1]  # The last part is usually the name
            # If the element is just a letter (possible drive)
            if len(name) == 1 and name.isalpha():
                parsed_list.append({
                    'name': name.upper(),
                    'type': 'directory',  # Treat drives as directories
                    'size': '0',
                    'modified': '',
                    'raw': item
                })
        
        # Second attempt: look for other clues for drives
        if not parsed_list:
            windows_style = False
            
            # Check if we receive a Windows format (e.g., "Volume in drive C is...")
            for item in file_list:
                if "Volume in drive" in item or "Directory of" in item:
                    windows_style = True
                    break
            
            if windows_style:
                # Try to extract from Windows format
                for item in file_list:
                    if "<DIR>" in item:
                        parts = item.split()
                        if len(parts) >= 4:
                            name = parts[-1]
                            # Check if it has a drive format (C:, D:)
                            if len(name) == 2 and name[0].isalpha() and name[1] == ':':
                                parsed_list.append({
                                    'name': name[0].upper(),
                                    'type': 'directory',
                                    'size': '0',
                                    'modified': '',
                                    'raw': item
                                })
            else:
                # If we didn't find drives in Windows style,
                # use the simple method (look for unique letters)
                for item in file_list:
                    if item and item[0].isalpha():
                        parsed_list.append({
                            'name': item[0].upper(),
                            'type': 'directory',
                            'size': '0',
                            'modified': '',
                            'raw': item
                        })
        
        # If we still didn't find anything, add common drives as backup
        if not parsed_list:
            # Common drives in Windows
            for letter in ['C', 'D']:
                parsed_list.append({
                    'name': letter,
                    'type': 'directory',
                    'size': '0',
                    'modified': '',
                    'raw': ''
                })
                
        return parsed_list
        
    def _parse_regular_directory(self, file_list):
        """Parse a regular directory"""
        parsed_list = []
        
        # If we are not in the root directory, add .. for navigation up
        if self.current_directory != "/":
            parsed_list.append({
                'name': '..',
                'type': 'directory',
                'size': '0',
                'modified': '',
                'raw': ''
            })
            
        # Patterns for different FTP listing formats
        unix_pattern = r'^([d-])([rwxst-]{9})\s+\d+\s+\w+\s+\w+\s+(\d+)\s+(\w+\s+\d+\s+[\d:]+)\s+(.+)$'
        windows_pattern = r'^(\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}[AP]M)\s+(<DIR>|\d+)\s+(.+)$'
        
        for item in file_list:
            try:
                # First try UNIX format
                match = re.match(unix_pattern, item)
                if match:
                    dir_flag, perms, size, date, name = match.groups()
                    file_type = "directory" if dir_flag == 'd' else "file"
                    parsed_list.append({
                        'name': name,
                        'type': file_type,
                        'size': size,
                        'modified': date,
                        'raw': item
                    })
                    continue
                
                # Try Windows format
                match = re.match(windows_pattern, item)
                if match:
                    date, size_or_dir, name = match.groups()
                    file_type = "directory" if size_or_dir == "<DIR>" else "file"
                    size = "0" if size_or_dir == "<DIR>" else size_or_dir
                    parsed_list.append({
                        'name': name,
                        'type': file_type,
                        'size': size,
                        'modified': date,
                        'raw': item
                    })
                    continue
                
                # If it doesn't match known patterns, try to parse manually
                parts = item.split()
                if len(parts) >= 4:
                    # The last part is usually the name
                    name = parts[-1]
                    
                    # Check if it is a directory
                    is_dir = False
                    if item.startswith('d') or '<DIR>' in item:
                        is_dir = True
                    
                    # Find the size
                    size = '0'
                    for part in parts:
                        if part.isdigit() and not is_dir:
                            size = part
                            break
                    
                    # Modification date (assume it's in standard format)
                    modified = ''
                    if len(parts) > 5:
                        modified = ' '.join(parts[-4:-1])
                    
                    parsed_list.append({
                        'name': name,
                        'type': 'directory' if is_dir else 'file',
                        'size': size,
                        'modified': modified,
                        'raw': item
                    })
            except Exception as e:
                print(f"Error parsing item {item}: {str(e)}")
        
        return parsed_list
        
    def change_directory(self, path):
        """Change the current directory"""
        return self.list_directory(path)
        
    def download_file(self, remote_file, local_path):
        """Download a file from the server"""
        if not self.is_connected:
            self.error.emit("You are not connected to an FTP server")
            return False
            
        try:
            self.logger.log(f"FTPClient: Downloading {remote_file} to {local_path}")
            # Create all necessary directories
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Start a thread for downloading
            download_thread = DownloadThread(self.ftp, remote_file, local_path, self.logger)
            download_thread.download_complete.connect(
                lambda file: (self.file_downloaded.emit(file), self.clean_thread(download_thread))
            )
            download_thread.download_error.connect(
                lambda error: (self.error.emit(error), self.clean_thread(download_thread))
            )
            
            # Keep a reference to the thread
            self.active_threads.append(download_thread)
            
            download_thread.start()
            return True
        except Exception as e:
            error_msg = f"Error initiating download: {str(e)}"
            self.logger.log(f"FTPClient: {error_msg}")
            self.error.emit(error_msg)
            return False
            
    def upload_file(self, local_file, remote_dir=None):
        """Upload a file to the server"""
        if not self.is_connected:
            self.error.emit("You are not connected to an FTP server")
            return False
            
        try:
            # If no remote directory is specified, use the current directory
            if remote_dir is None:
                remote_dir = self.current_directory
                
            self.logger.log(f"FTPClient: Uploading {local_file} to {remote_dir}")
            
            # Start a thread for uploading
            upload_thread = UploadThread(self.ftp, local_file, remote_dir, self.logger)
            upload_thread.upload_complete.connect(
                lambda file: (self.file_uploaded.emit(file), self.clean_thread(upload_thread))
            )
            upload_thread.upload_error.connect(
                lambda error: (self.error.emit(error), self.clean_thread(upload_thread))
            )
            
            # Keep a reference to the thread
            self.active_threads.append(upload_thread)
            
            upload_thread.start()
            return True
        except Exception as e:
            error_msg = f"Error initiating upload: {str(e)}"
            self.logger.log(f"FTPClient: {error_msg}")
            self.error.emit(error_msg)
            return False
            
    def _make_dirs(self, path):
        """Recursively create necessary directories on the server"""
        if path == '/' or not path:
            return
            
        try:
            self.ftp.cwd(path)
            self.ftp.cwd('/')  # Return to root after verification
        except ftplib.error_perm:
            # Directory does not exist, needs to be created
            self._make_dirs(os.path.dirname(path))
            try:
                self.ftp.mkd(path)
            except ftplib.error_perm:
                pass
        
    def create_directory(self, directory_name):
        """Create a directory on the server"""
        if not self.is_connected:
            self.error.emit("You are not connected to an FTP server")
            return False
            
        try:
            self.ftp.mkd(directory_name)
            return True
        except Exception as e:
            self.error.emit(f"Error creating directory: {str(e)}")
            return False
            
    def delete_file(self, filename):
        """Delete a file from the server"""
        if not self.is_connected:
            self.logger.log("FTPClient: delete_file: You are not connected to an FTP server")
            return False
            
        try:
            self.ftp.delete(filename)
            self.logger.log(f"FTPClient: delete_file: Successfully deleted file: {filename}")
            return True
        except Exception as e:
            self.logger.log(f"FTPClient: delete_file: Error deleting file: {str(e)}")
            return False
            
    def delete_directory(self, directory_name):
        """Delete a directory from the server"""
        if not self.is_connected:
            self.logger.log("FTPClient: delete_directory: You are not connected to an FTP server")
            self.error.emit("You are not connected to an FTP server")
            return False
            
        try:
            self.ftp.rmd(directory_name)
            self.logger.log(f"FTPClient: delete_directory: Successfully deleted directory: {directory_name}")
            return True
        except Exception as e:
            self.logger.log(f"FTPClient: delete_directory: Error deleting directory: {str(e)}")
            self.error.emit(f"Error deleting directory: {str(e)}")
            return False
    
    def list_root_drives(self):
        """List root drives"""
        if not self.is_connected:
            self.logger.log("FTPClient: list_root_drives: You are not connected to an FTP server")
            return []
            
        try:
            # Navigate to root
            self.ftp.cwd('/')
            self.current_directory = '/'
            
            # Get the list of files and directories
            file_list = []
            self.ftp.retrlines('LIST', lambda x: file_list.append(x))
            
            # Parse the list to find drives
            drives = []
            
            # Check different patterns to identify drives
            for item in file_list:
                # Try to identify drives in standard format (e.g., "C:")
                if ':' in item:
                    parts = item.split()
                    for part in parts:
                        if len(part) == 2 and part[0].isalpha() and part[1] == ':':
                            drive_letter = part[0].upper()
                            if drive_letter not in [d['name'] for d in drives]:
                                drives.append({
                                    'name': drive_letter,
                                    'type': 'directory',
                                    'size': '0',
                                    'modified': '',
                                    'raw': item
                                })
                
                # Check specific Windows formats (e.g., "Volume in drive C is")
                if "Volume in drive" in item:
                    for char in item:
                        if char.isalpha() and char.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                            drive_letter = char.upper()
                            if drive_letter not in [d['name'] for d in drives]:
                                drives.append({
                                    'name': drive_letter,
                                    'type': 'directory',
                                    'size': '0',
                                    'modified': '',
                                    'raw': item
                                })
                
                # Check format "<DIR> C"
                if "<DIR>" in item:
                    parts = item.split()
                    if "<DIR>" in parts:
                        idx = parts.index("<DIR>")
                        if idx + 1 < len(parts) and len(parts[idx+1]) == 1 and parts[idx+1].isalpha():
                            drive_letter = parts[idx+1].upper()
                            if drive_letter not in [d['name'] for d in drives]:
                                drives.append({
                                    'name': drive_letter,
                                    'type': 'directory',
                                    'size': '0',
                                    'modified': '',
                                    'raw': item
                                })
            
            # If no drives were found, check for single letters
            if not drives:
                for item in file_list:
                    parts = item.split()
                    for part in parts:
                        if len(part) == 1 and part.isalpha():
                            drive_letter = part.upper()
                            if drive_letter not in [d['name'] for d in drives]:
                                drives.append({
                                    'name': drive_letter,
                                    'type': 'directory',
                                    'size': '0',
                                    'modified': '',
                                    'raw': item
                                })
            
            # If still no drives found, use common drives as fallback
            if not drives:
                for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                    drives.append({
                        'name': letter,
                        'type': 'directory',
                        'size': '0',
                        'modified': '',
                        'raw': ''
                    })
            
            # Emit the signal with the list of drives
            self.directory_listed.emit(drives)
            return drives
        except Exception as e:
            error_msg = f"Error listing root drives: {str(e)}"
            self.logger.log(f"FTPClient: {error_msg}")
            self.error.emit(error_msg)
            return []
            
    def navigate_to_ftp_path(self, path):
        """Navigate to a specified FTP path"""
        if not self.is_connected:
            self.logger.log("FTPClient: navigate_to_ftp_path: You are not connected to an FTP server")
            return False
            
        self.logger.log(f"FTPClient.navigate_to_ftp_path: Attempting to navigate to {path}")
        
        try:
            # Check if it's a Windows path (e.g., C:\...)
            if re.match(r'^[A-Za-z]:[/\\]', path):
                # Convert Windows path to FTP format
                path = '/' + path[0] + path[2:].replace('\\', '/')
            
            # Try to navigate to the specified path
            self.ftp.cwd(path)
            self.current_directory = self.ftp.pwd()
            self.logger.log(f"FTPClient.navigate_to_ftp_path: Successfully navigated to {self.current_directory}")
            
            # List the directory contents
            self.list_directory()
            return True
        except Exception as e:
            self.logger.log(f"FTPClient.navigate_to_ftp_path: Navigation error - {str(e)}")
            self.error.emit(f"Navigation error: {str(e)}")
            return False

    def clean_thread(self, thread):
        """Remove the thread from the list of active threads after it has finished"""
        if thread in self.active_threads:
            self.active_threads.remove(thread)


class DownloadThread(QThread):
    """Thread for downloading files"""
    download_complete = pyqtSignal(str)
    download_error = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, ftp, remote_file, local_path, logger=None):
        super().__init__()
        self.ftp = ftp
        self.remote_file = remote_file
        self.local_path = local_path
        self.logger = logger
        
    def run(self):
        try:
            if self.logger:
                self.logger.log(f"DownloadThread: Starting download of {self.remote_file}")
                
            # Open the local file for writing
            with open(self.local_path, 'wb') as local_file:
                # Download the file
                self.ftp.retrbinary(f'RETR {self.remote_file}', local_file.write)
            
            if self.logger:
                self.logger.log(f"DownloadThread: Successfully downloaded {self.remote_file} to {self.local_path}")
                
            # Emit signal when download is complete
            self.download_complete.emit(self.local_path)
        except Exception as e:
            error_msg = f"Download error: {str(e)}"
            
            if self.logger:
                self.logger.log(f"DownloadThread: {error_msg}")
                
            self.download_error.emit(error_msg)


class UploadThread(QThread):
    """Thread for uploading files"""
    upload_complete = pyqtSignal(str)
    upload_error = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, ftp, local_file, remote_dir, logger=None):
        super().__init__()
        self.ftp = ftp
        self.local_file = local_file
        self.remote_dir = remote_dir
        self.logger = logger
        
    def run(self):
        current_dir = None
        try:
            if self.logger:
                self.logger.log(f"UploadThread: Starting upload of {self.local_file} to {self.remote_dir}")
                
            # Check if the file exists
            if not os.path.exists(self.local_file):
                raise FileNotFoundError(f"The file {self.local_file} does not exist")
                
            if not os.path.isfile(self.local_file):
                raise IsADirectoryError(f"{self.local_file} is a directory, not a file")
                
            # Save the current directory
            current_dir = self.ftp.pwd()
                
            # Navigate to the remote directory
            try:
                self.ftp.cwd(self.remote_dir)
            except ftplib.error_perm as e:
                raise Exception(f"Could not access directory {self.remote_dir}: {str(e)}")
            
            # Get the filename
            filename = os.path.basename(self.local_file)
            
            # Upload the file
            try:
                with open(self.local_file, 'rb') as local_file:
                    try:
                        self.ftp.storbinary(f'STOR {filename}', local_file)
                    except ftplib.error_perm as e:
                        raise Exception(f"The server refused to save the file: {str(e)}")
                    except Exception as e:
                        raise Exception(f"Error uploading file to server: {str(e)}")
            except PermissionError:
                raise Exception(f"You do not have permission to read the file {self.local_file}")
            except Exception as e:
                raise Exception(f"Could not open the file {self.local_file}: {str(e)}")
            
            if self.logger:
                self.logger.log(f"UploadThread: Successfully uploaded {self.local_file} to {self.remote_dir}/{filename}")
                
            # Emit signal when upload is complete
            self.upload_complete.emit(self.local_file)
            
        except Exception as e:
            error_message = f"Upload error: {str(e)}"
            
            if self.logger:
                self.logger.log(f"UploadThread: {error_message}")
                
            self.upload_error.emit(error_message)
        finally:
            # Ensure we return to the initial directory
            if current_dir:
                try:
                    self.ftp.cwd(current_dir)
                except:
                    pass

