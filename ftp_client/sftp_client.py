"""
SFTP Client for the File Manager application
"""

import os
import paramiko
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import threading
import socket
import time
from ftp_client.utils.logger import FTPLogger

class SFTPClient(QObject):
    """Class for managing SFTP connections"""
    
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
        self.transport = None
        self.sftp = None
        self.is_connected = False
        self.current_directory = None
        self.active_threads = []  # List to hold references to active threads
        self.connection_id = None  # Connection ID from the database
        self.host = None
        self.port = None
        self.logger = FTPLogger()  # Inițializează logger-ul
        
    def __del__(self):
        """Destructor to ensure all threads are stopped correctly"""
        try:
            for thread in self.active_threads:
                if thread.isRunning():
                    thread.wait()
        except:
            pass
            
        # Închide logger-ul când obiectul este distrus
        if hasattr(self, 'logger'):
            self.logger.close()
            
    def connect(self, host, port=22, username="", password="", timeout=10, key_file=None, key_passphrase=None):
        """Connect to the SFTP server"""
        self.logger.start_logging(host, port, username)
        self.logger.log(f"SFTPClient.connect: Attempting to connect to {host}:{port} with {username}")
        
        try:
            # Close any existing connection
            if self.transport:
                try:
                    self.logger.log(f"SFTPClient.connect: Closing existing connection before connecting to {host}")
                    self.transport.close()
                except:
                    pass
                self.transport = None
                self.sftp = None
                self.is_connected = False
                
                # Curățăm și thread-urile active
                for thread in self.active_threads[:]:
                    try:
                        if thread.isRunning():
                            thread.wait(500)  # Așteptăm până la 0.5 secunde
                        self.active_threads.remove(thread)
                    except:
                        pass
                # Golim lista de thread-uri active
                self.active_threads.clear()
                
                # Închide și clientul SSH dacă există
                if hasattr(self, '_ssh_client') and self._ssh_client:
                    try:
                        self._ssh_client.close()
                    except:
                        pass
                    self._ssh_client = None
                
            # Salvăm host și port pentru utilizare ulterioară
            self.host = host
            self.port = port
            
            # Explicitly initialize current_directory to avoid None issues
            self.current_directory = None
            
            # Check if we are using private key authentication
            if key_file and os.path.exists(key_file):
                self.logger.log(f"SFTPClient.connect: Trying to connect with private key: {key_file}")
                try:
                    # Create SSH client for easier key authentication
                    ssh_client = paramiko.SSHClient()
                    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    
                    # Build connection parameters
                    connect_kwargs = {
                        'hostname': host,
                        'port': int(port),
                        'username': username,
                        'timeout': timeout
                    }
                    
                    # Add the private key and optionally its passphrase
                    connect_kwargs['key_filename'] = key_file
                    if key_passphrase:
                        connect_kwargs['passphrase'] = key_passphrase
                        
                    # Attempt connection
                    ssh_client.connect(**connect_kwargs)
                    
                    # Obtain transport to create the SFTP client
                    self.transport = ssh_client.get_transport()
                    self.sftp = ssh_client.open_sftp()
                    
                    # Keep a reference to the SSH client for proper closure
                    self._ssh_client = ssh_client
                    
                    # Verificăm că transportul este activ
                    if not self.transport.is_active():
                        self.logger.log(f"SFTPClient.connect: Transport is not active, reconnecting...")
                        self.transport.close()
                        ssh_client.close()
                        
                        # Încercăm din nou
                        ssh_client = paramiko.SSHClient()
                        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        ssh_client.connect(**connect_kwargs)
                        self.transport = ssh_client.get_transport()
                        self.sftp = ssh_client.open_sftp()
                        self._ssh_client = ssh_client
                    
                    self.logger.log(f"SFTPClient.connect: Successfully connected with private key")
                except Exception as e:
                    self.logger.log(f"SFTPClient.connect: Private key authentication failed: {str(e)}")
                    # If key authentication fails, try password if available
                    if password:
                        self.logger.log(f"SFTPClient.connect: Trying password authentication instead")
                        return self._connect_with_password(host, port, username, password, timeout)
                    else:
                        raise Exception(f"Private key authentication failed: {str(e)}")
            else:
                # Standard password connection
                self.logger.log(f"SFTPClient.connect: Trying password authentication")
                return self._connect_with_password(host, port, username, password, timeout)
            
            # Verify connection and obtain current directory
            self.is_connected = True
            try:
                self.current_directory = self.sftp.getcwd()
                self.logger.log(f"SFTPClient.connect: Current directory set to {self.current_directory}")
            except Exception as e:
                self.logger.log(f"SFTPClient.connect: Could not get current directory: {str(e)}")
                # If we can't get the current directory, try listing
                try:
                    # Try listing the current directory (whatever is available)
                    self.sftp.listdir('.')
                    self.current_directory = '.'
                    self.logger.log(f"SFTPClient.connect: Current directory set to '.' after listing")
                except Exception as e2:
                    self.logger.log(f"SFTPClient.connect: Could not list current directory: {str(e2)}")
                    # Try other possible paths
                    for test_path in ['/', '/home/' + username, '~', '.']:
                        try:
                            self.sftp.chdir(test_path)
                            self.current_directory = test_path
                            self.logger.log(f"SFTPClient.connect: Current directory set to {test_path} after testing")
                            break
                        except Exception as e3:
                            self.logger.log(f"SFTPClient.connect: Could not chdir to {test_path}: {str(e3)}")
                    else:
                        # If no path worked, use a virtual directory
                        self.current_directory = "/"
                        self.logger.log(f"SFTPClient.connect: Fallback to virtual directory '/'")
                        
            # Ensure current_directory is not None
            if self.current_directory is None:
                self.current_directory = "."
                self.logger.log(f"SFTPClient.connect: Fallback to default directory '.'")
                    
            self.connected.emit(f"Connected to {host}")
            self.logger.log(f"SFTPClient.connect: Connection established successfully")
            return True
            
        except Exception as e:
            error_msg = f"SFTP connection error: {str(e)}"
            self.logger.log(f"SFTPClient.connect: {error_msg}")
            
            # Clean up resources in case of error
            if hasattr(self, '_ssh_client'):
                try:
                    self._ssh_client.close()
                except:
                    pass
                del self._ssh_client
                
            if self.sftp:
                try:
                    self.sftp.close()
                except:
                    pass
                self.sftp = None
                
            if self.transport:
                try:
                    self.transport.close()
                except:
                    pass
                self.transport = None
                
            self.error.emit(error_msg)
            return False
            
    def _connect_with_password(self, host, port, username, password, timeout):
        """Helper method for connecting using password authentication"""
        try:
            self.logger.log(f"SFTPClient._connect_with_password: Trying to connect with password")
            # Create SSH transport
            self.transport = paramiko.Transport((host, int(port)))
            self.transport.connect(username=username, password=password)
            
            # Create SFTP client
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)
            
            # Verificăm că transportul este activ
            if not self.transport.is_active():
                self.logger.log(f"SFTPClient._connect_with_password: Transport is not active, reconnecting...")
                self.transport.close()
                
                # Încercăm din nou
                self.transport = paramiko.Transport((host, int(port)))
                self.transport.connect(username=username, password=password)
                self.sftp = paramiko.SFTPClient.from_transport(self.transport)
            
            self.is_connected = True
            try:
                self.current_directory = self.sftp.getcwd()
                self.logger.log(f"SFTPClient._connect_with_password: Current directory set to {self.current_directory}")
            except Exception as e:
                self.logger.log(f"SFTPClient._connect_with_password: Could not get current directory: {str(e)}")
                self.current_directory = "/"
                
            self.connected.emit(f"Connected to {host}")
            self.logger.log(f"SFTPClient._connect_with_password: Connection established successfully")
            return True
            
        except Exception as e:
            error_msg = f"SFTP connection error with password: {str(e)}"
            self.logger.log(f"SFTPClient._connect_with_password: {error_msg}")
            
            # Clean up resources in case of error
            if self.sftp:
                try:
                    self.sftp.close()
                except:
                    pass
                self.sftp = None
                
            if self.transport:
                try:
                    self.transport.close()
                except:
                    pass
                self.transport = None
                
            self.error.emit(error_msg)
            return False
            
    def disconnect(self):
        """Disconnect from the SFTP server"""
        try:
            self.logger.log("SFTPClient.disconnect: Disconnecting from server")
            # Stop all active threads before disconnecting
            for thread in self.active_threads[:]:
                if thread.isRunning():
                    try:
                        thread.wait(1000)  # Wait up to 1 second
                    except:
                        pass
                self.active_threads.remove(thread)
            
            # Clear the thread list
            self.active_threads.clear()
            
            # Close the SFTP client
            if self.sftp:
                try:
                    self.sftp.close()
                except:
                    pass
                self.sftp = None
                
            # Close the SSH transport
            if self.transport:
                try:
                    self.transport.close()
                except:
                    pass
                self.transport = None
                
            # Close the SSH client if it was used for key authentication
            if hasattr(self, '_ssh_client') and self._ssh_client:
                try:
                    self._ssh_client.close()
                except:
                    pass
                self._ssh_client = None
                
            self.is_connected = False
            self.disconnected.emit()
            self.logger.log("SFTPClient.disconnect: Disconnected successfully")
            # Închide logger-ul la deconectare
            self.logger.close()
            
        except Exception as e:
            error_msg = f"Disconnection error: {str(e)}"
            self.logger.log(f"SFTPClient.disconnect: {error_msg}")
            self.error.emit(error_msg)
            
    def is_directory(self, path):
        """Check if a path is a directory on the SFTP server"""
        if not self.is_connected:
            return False
        
        try:
            try:
                # Try to list the directory
                self.sftp.listdir(path)
                return True
            except Exception:
                # Try the alternative method: chdir
                try:
                    # Save the current directory
                    old_dir = self.sftp.getcwd()
                    # Try to enter the directory
                    self.sftp.chdir(path)
                    # If successful, it's a directory
                    # Return to the original directory
                    self.sftp.chdir(old_dir)
                    return True
                except Exception:
                    return False
                
        except Exception:
            return False

    def list_directory(self, path=None, show_output=True):
        """List the contents of a directory"""
        if not self.is_connected:
            self.error.emit("Not connected to the server")
            return False
            
        try:
            if path is None:
                path = self.current_directory if self.current_directory else '.'
                
            # Get the list of files
            files = self.sftp.listdir_attr(path)
            
            # Convert to the format expected by the interface
            file_list = []
            for file in files:
                # Check more carefully if it is a directory or file using multiple methods
                
                # Method 1: Check the S_IFDIR bit (standard)
                is_dir = bool(file.st_mode & 0o40000)  # 0o40000 is S_IFDIR in octal
                
                # Method 2: Directly check the directory when unclear
                if not is_dir:
                    # Build the full path
                    test_path = path + '/' + file.filename if not path.endswith('/') else path + file.filename
                    # Check using our specialized method
                    is_dir = self.is_directory(test_path)
                
                # Method 3: Check for special directories on Ubuntu
                # On some Ubuntu servers, directories can be hidden in a special way
                if not is_dir and file.filename.startswith('.') and file.st_size == 4096:
                    is_dir = True
                
                file_info = {
                    'name': file.filename,
                    'size': file.st_size,
                    'type': 'dir' if is_dir else 'file',  # Use 'dir', not 'directory' for compatibility
                    'modified': file.st_mtime
                }
                file_list.append(file_info)
            
            # Emit the signal only if show_output is True
            if show_output:
                self.directory_listed.emit(file_list)
                
            # Always return the file list
            return file_list
            
        except Exception as e:
            error_msg = f"Directory listing error: {str(e)}"
            self.error.emit(error_msg)
            return False
            
    def download_file(self, remote_path, local_path):
        """Download a file from the server"""
        if not self.is_connected:
            self.error.emit("Not connected to the server")
            return
            
        try:
            self.logger.log(f"SFTPClient: Downloading {remote_path} to {local_path}")
            # Create a thread for downloading
            download_thread = DownloadThread(self.sftp, remote_path, local_path, self.logger)
            download_thread.progress_updated.connect(self.progress_updated.emit)
            download_thread.finished.connect(lambda: self.file_downloaded.emit(local_path))
            download_thread.error.connect(self.error.emit)
            
            self.active_threads.append(download_thread)
            download_thread.start()
            
        except Exception as e:
            error_msg = f"Download error: {str(e)}"
            self.logger.log(f"SFTPClient: {error_msg}")
            self.error.emit(error_msg)
            
    def upload_file(self, local_path, remote_path):
        """Upload a file to the server"""
        if not self.is_connected:
            self.error.emit("Not connected to the server")
            return
            
        try:
            self.logger.log(f"SFTPClient: Uploading {local_path} to {remote_path}")
            # Create a thread for uploading
            upload_thread = UploadThread(self.sftp, local_path, remote_path, self.logger)
            upload_thread.progress_updated.connect(self.progress_updated.emit)
            upload_thread.finished.connect(lambda: self.file_uploaded.emit(local_path))
            upload_thread.error.connect(self.error.emit)
            
            self.active_threads.append(upload_thread)
            upload_thread.start()
            
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            self.logger.log(f"SFTPClient: {error_msg}")
            self.error.emit(error_msg)
            
    def create_directory(self, path):
        """Create a new directory"""
        if not self.is_connected:
            self.logger.log("SFTPClient: create_directory: Not connected to the server")
            self.error.emit("Not connected to the server")
            return
            
        try:
            self.sftp.mkdir(path)
            self.logger.log(f"SFTPClient: create_directory: Successfully created directory: {path}")
            self.list_directory()  # Refresh the list
        except Exception as e:
            error_msg = f"Directory creation error: {str(e)}"
            self.logger.log(f"SFTPClient: create_directory: {error_msg}")
            self.error.emit(error_msg)
            
    def delete_file(self, path):
        """Delete a file or directory"""
        if not self.is_connected:
            self.logger.log("SFTPClient: delete_file: Not connected to the server")
            self.error.emit("Not connected to the server")
            return
            
        try:
            # Check if it is a directory or file
            try:
                self.sftp.rmdir(path)  # Try to delete as a directory
                self.logger.log(f"SFTPClient: delete_file: Successfully deleted directory: {path}")
            except:
                self.sftp.remove(path)  # If it doesn't work, delete as a file
                self.logger.log(f"SFTPClient: delete_file: Successfully deleted file: {path}")
                
            self.list_directory()  # Refresh the list
        except Exception as e:
            error_msg = f"Deletion error: {str(e)}"
            self.logger.log(f"SFTPClient: delete_file: {error_msg}")
            self.error.emit(error_msg)
            
    def delete_directory(self, path):
        """Delete a directory"""
        if not self.is_connected:
            self.logger.log("SFTPClient: delete_directory: Nu sunteți conectat la server")
            self.error.emit("Nu sunteți conectat la server")
            return False
            
        try:
            # Verificăm dacă este un director
            if self.is_directory(path):
                try:
                    # Încercăm să ștergem directorul direct
                    self.sftp.rmdir(path)
                    self.logger.log(f"SFTPClient: delete_directory: Director șters cu succes: {path}")
                    self.list_directory()  # Reîmprospătăm lista
                    return True
                except Exception as dir_error:
                    # Este posibil ca directorul să nu fie gol
                    # Afișăm o eroare specifică
                    error_msg = f"Eroare la ștergerea directorului: {str(dir_error)}"
                    self.logger.log(f"SFTPClient: delete_directory: {error_msg}")
                    self.error.emit(error_msg)
                    return False
            else:
                error_msg = f"{path} nu este un director"
                self.logger.log(f"SFTPClient: delete_directory: {error_msg}")
                self.error.emit(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Eroare la ștergerea directorului: {str(e)}"
            self.logger.log(f"SFTPClient: delete_directory: {error_msg}")
            self.error.emit(error_msg)
            return False
            
    def change_directory(self, path):
        """Change the current directory"""
        if not self.is_connected:
            self.error.emit("Not connected to the server")
            return False
            
        try:
            # Save the current directory to revert in case of error
            # If current_directory is None, use "." as a fallback
            old_directory = self.current_directory if self.current_directory else "."
            
            try:
                # Check if it is a relative or absolute navigation
                if path == "..":
                    # Navigate up
                    # If we are in the root directory, do nothing
                    if self.current_directory in ["/", ".", None]:
                        return True
                        
                    # Otherwise, manually build the parent path
                    if self.current_directory and self.current_directory.endswith('/'):
                        parent_dir = self.current_directory[:-1]  # Remove the trailing slash
                    elif self.current_directory:
                        parent_dir = self.current_directory
                    else:
                        # If current_directory is None, try using getcwd
                        try:
                            parent_dir = self.sftp.getcwd()
                        except:
                            # If that doesn't work, use the default path
                            parent_dir = "."
                        
                    # Find the last slash (but only if we have parent_dir)
                    if parent_dir and parent_dir not in [".", "/"]:
                        last_slash = parent_dir.rfind('/')
                        if last_slash >= 0:
                            parent_dir = parent_dir[:last_slash] or "/"
                        else:
                            parent_dir = "/"
                        
                    # Try to navigate using the absolute parent path
                    self.sftp.chdir(parent_dir)
                    self.current_directory = parent_dir
                elif path and path.startswith('/'):
                    # Absolute navigation
                    self.sftp.chdir(path)
                    self.current_directory = path
                else:
                    # Relative navigation - use the directory name directly
                    self.sftp.chdir(path)
                    
                    try:
                        # Update current_directory with the real value
                        self.current_directory = self.sftp.getcwd()
                    except Exception:
                        # If we can't get the current path, build one manually
                        if self.current_directory:
                            if self.current_directory.endswith('/'):
                                self.current_directory = self.current_directory + path
                            else:
                                self.current_directory = f"{self.current_directory}/{path}"
                        else:
                            # Use the path directly if we don't have a current_directory
                            self.current_directory = path
                
                try:
                    # Try to verify if we reached the correct location
                    pwd_result = self.sftp.getcwd()
                    self.current_directory = pwd_result
                except Exception:
                    # Do not mark as error - use the value we calculated
                    pass
                
                # List the contents
                self.list_directory()
                return True
                
            except Exception as e:
                error_msg = f"Directory change error: {str(e)}"
                self.error.emit(error_msg)
                
                # Revert to the previous directory
                try:
                    self.sftp.chdir(old_directory)
                    self.current_directory = old_directory
                except Exception:
                    # Try the home directory
                    try:
                        self.sftp.chdir('.')
                        self.current_directory = '.'
                    except:
                        pass
                
                return False
                
        except Exception as e:
            error_msg = f"Directory change error: {str(e)}"
            self.error.emit(error_msg)
            return False

class DownloadThread(QThread):
    """Thread for downloading files"""
    progress_updated = pyqtSignal(int)
    error = pyqtSignal(str)
    
    def __init__(self, sftp, remote_path, local_path, logger=None):
        super().__init__()
        self.sftp = sftp
        self.remote_path = remote_path
        self.local_path = local_path
        self.logger = logger
        
    def run(self):
        try:
            if self.logger:
                self.logger.log(f"DownloadThread: Starting download of {self.remote_path}")
                
            # Get the file size
            file_size = self.sftp.stat(self.remote_path).st_size
            
            # Download the file with a progress callback
            self.sftp.get(self.remote_path, self.local_path, 
                         callback=lambda x, y: self.progress_updated.emit(int(x * 100 / y)))
                         
            if self.logger:
                self.logger.log(f"DownloadThread: Successfully downloaded {self.remote_path} to {self.local_path}")
                
        except Exception as e:
            error_msg = str(e)
            if self.logger:
                self.logger.log(f"DownloadThread: Error: {error_msg}")
            self.error.emit(error_msg)

class UploadThread(QThread):
    """Thread for uploading files"""
    progress_updated = pyqtSignal(int)
    error = pyqtSignal(str)
    
    def __init__(self, sftp, local_path, remote_path, logger=None):
        super().__init__()
        self.sftp = sftp
        self.local_path = local_path
        self.remote_path = remote_path
        self.logger = logger
        
    def run(self):
        try:
            if self.logger:
                self.logger.log(f"UploadThread: Starting upload of {self.local_path} to {self.remote_path}")
                
            # Get the file size
            file_size = os.path.getsize(self.local_path)
            
            # Upload the file with a progress callback
            self.sftp.put(self.local_path, self.remote_path,
                         callback=lambda x, y: self.progress_updated.emit(int(x * 100 / y)))
                         
            if self.logger:
                self.logger.log(f"UploadThread: Successfully uploaded {self.local_path} to {self.remote_path}")
                
        except Exception as e:
            error_msg = str(e)
            if self.logger:
                self.logger.log(f"UploadThread: Error: {error_msg}")
            self.error.emit(error_msg)