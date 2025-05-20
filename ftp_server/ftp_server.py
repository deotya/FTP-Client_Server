import os
import sys
import sqlite3
import hashlib
import uuid
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.filesystems import AbstractedFS, FilesystemError
import win32api

# Class for managing the SQLite database
class UserDatabase:
    """Class for managing the user database"""
    
    def __init__(self, db_path="ftp_users.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initializes the database and creates necessary tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create the table for users
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            permissions TEXT NOT NULL,
            home_dir TEXT NOT NULL
        )
        ''')
        
        # Check if the default user 'user' exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("user",))
        if cursor.fetchone()[0] == 0:
            # Add the default user 'user' with password 'password'
            self.add_user("user", "password", "elradfmwMT", "/")
            print("Default user created: user/password")
            
        # Check if the default user 'admin' exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
        if cursor.fetchone()[0] == 0:
            # Add the default user 'admin' with password 'admin'
            self.add_user("admin", "admin", "elradfmwMT", "/")
            print("Admin user created: admin/admin")
        
        conn.commit()
        conn.close()
    
    def _hash_password(self, password, salt=None):
        """Generates a hash for a password with salt"""
        print(f"_hash_password: Generating hash for password (salt: {'newly generated' if salt is None else 'existing'})")
        try:
            if salt is None:
                salt = uuid.uuid4().hex
                print(f"_hash_password: New salt generated: {salt[:5]}...")
            else:
                print(f"_hash_password: Existing salt used: {salt[:5]}...")
            
            # Ensure that the password and salt are strings
            if not isinstance(password, str):
                print(f"_hash_password: WARNING - Password is not a string, but {type(password)}")
                password = str(password)
                
            if not isinstance(salt, str):
                print(f"_hash_password: WARNING - Salt is not a string, but {type(salt)}")
                salt = str(salt)
            
            # Display debugging details (partial, without revealing the entire password)
            print(f"_hash_password: Password length: {len(password)}, Salt length: {len(salt)}")
            print(f"_hash_password: First characters of the password: '{password[:2]}...' (for verification)")
            print(f"_hash_password: First characters of the salt: '{salt[:5]}...' (for verification)")
            
            # Combine the password with the salt and generate the hash
            combined = password + salt
            print(f"_hash_password: Combined string length: {len(combined)}")
            
            password_hash = hashlib.sha256(combined.encode()).hexdigest()
            print(f"_hash_password: Generated hash: {password_hash[:10]}...")
            
            return password_hash, salt
        except Exception as e:
            print(f"_hash_password: ERROR generating hash: {str(e)}")
            print(f"_hash_password: Exception details: {repr(e)}")
            # Return an empty hash in case of error, making authentication impossible
            return "", salt or ""
    
    def add_user(self, username, password, permissions, home_dir):
        """Adds a new user to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Generate the password hash
            password_hash, salt = self._hash_password(password)
            
            # Normalize the home_dir path in Windows format, if applicable
            if home_dir and len(home_dir) >= 2 and home_dir[1] == ":":
                # It's a Windows path (e.g., C:\Users)
                # Leave it as is, it will be handled correctly in ftp_server
                pass
                
            # Insert the user into the database
            cursor.execute('''
            INSERT INTO users (username, password_hash, salt, permissions, home_dir)
            VALUES (?, ?, ?, ?, ?)
            ''', (username, password_hash, salt, permissions, home_dir))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # User already exists
            return False
        finally:
            conn.close()
    
    def update_user(self, username, password=None, permissions=None, home_dir=None):
        """Updates the information of an existing user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if the user exists
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
            if not user:
                return False  # User does not exist
            
            # Build the update query
            update_fields = []
            params = []
            
            if password:
                password_hash, salt = self._hash_password(password)
                update_fields.extend(["password_hash = ?", "salt = ?"])
                params.extend([password_hash, salt])
                
            if permissions:
                update_fields.append("permissions = ?")
                params.append(permissions)
                
            if home_dir:
                update_fields.append("home_dir = ?")
                params.append(home_dir)
                
            if update_fields:
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE username = ?"
                params.append(username)
                
                cursor.execute(query, params)
                conn.commit()
                return True
            
            return False
        finally:
            conn.close()
    
    def delete_user(self, username):
        """Deletes a user from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted
        finally:
            conn.close()
    
    def authenticate_user(self, username, password):
        """Verifies user credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print(f"authenticate_user: Verifying credentials for '{username}'")
        
        try:
            cursor.execute('''
            SELECT password_hash, salt, permissions, home_dir 
            FROM users 
            WHERE username = ?
            ''', (username,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                print(f"authenticate_user: User '{username}' does not exist in the database")
                return None  # User does not exist
                
            stored_hash, salt, permissions, home_dir = user_data
            print(f"authenticate_user: User found, salt: {salt[:5]}..., home_dir: {home_dir}")
            
            # Verify the password
            password_hash, _ = self._hash_password(password, salt)
            
            # Display partial hashes for debugging
            print(f"authenticate_user: Verifying hashes:")
            print(f"  - Hash stored in DB: {stored_hash[:10]}...{stored_hash[-5:]}")
            print(f"  - Calculated hash: {password_hash[:10]}...{password_hash[-5:]}")
            
            if password_hash == stored_hash:
                print(f"authenticate_user: Password verification successful for '{username}'")
                return {
                    "username": username,
                    "permissions": permissions,
                    "home_dir": home_dir
                }
            
            print(f"authenticate_user: Password verification failed for '{username}'")
            print(f"authenticate_user: Hashes do not match")
            return None  # Incorrect password
        except Exception as e:
            print(f"authenticate_user: Error during authentication: {str(e)}")
            print(f"authenticate_user: Exception details: {repr(e)}")
            return None
        finally:
            conn.close()
    
    def get_all_users(self):
        """Returns the list of all users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT username, permissions, home_dir FROM users")
            users = cursor.fetchall()
            
            return [
                {
                    "username": username,
                    "permissions": permissions,
                    "home_dir": home_dir
                }
                for username, permissions, home_dir in users
            ]
        finally:
            conn.close()

class WindowsRootFS(AbstractedFS):
    """Virtual filesystem that allows access to all Windows drives"""
    
    def __init__(self, root, cmd_channel):
        super().__init__(root, cmd_channel)
        # Use a virtual root
        self.root = "/"
        self._cwd = "/"
        self.cmd_channel = cmd_channel
        
    def ftp2fs(self, ftppath):
        """Converts an FTP path to a system path"""
        print(f"ftp2fs: Converting FTP path: {ftppath}")
        
        if ftppath == "/":
            return self.root
            
        # Remove the initial slash
        if ftppath.startswith("/"):
            ftppath = ftppath[1:]
            
        # Handle the '..' path specially for navigating back
        if ftppath == "..":
            # If we're already at root, stay there
            if self._cwd == "/":
                return self.root
                
            # If we're on a drive (e.g., /C), go back to root
            if self._cwd.count('/') == 1 and len(self._cwd) == 2:
                return self.root
                
            # Otherwise, go one level up in the Windows directory hierarchy
            current_fs_path = self.getcwfs()
            parent_dir = os.path.dirname(current_fs_path)
            print(f"ftp2fs: Navigating back: {current_fs_path} -> {parent_dir}")
            return parent_dir
        
        # If it doesn't contain path separators and is just a letter, it might be a drive
        if len(ftppath) == 1 and ftppath.isalpha():
            # Check if it's a valid drive
            drive = ftppath.upper() + ":\\"
            print(f"ftp2fs: Possible drive: {drive}")
            if os.path.exists(drive):
                return drive
                
        # Check if we're in a subpath of a drive (e.g., C/Users or /C/Users)
        parts = ftppath.split("/")
        if parts and len(parts[0]) == 1 and parts[0].isalpha():
            drive_letter = parts[0].upper()
            drive_path = drive_letter + ":\\"
            
            # If it's just the drive without subfolders
            if len(parts) == 1:
                return drive_path
                
            # Build the Windows path for the remaining components
            rest_path = "\\".join(parts[1:])
            full_path = os.path.join(drive_path, rest_path)
            print(f"ftp2fs: Complete path for drive+subdirectories: {full_path}")
            
            return full_path
            
        # If we're already in a drive folder, handle the path relative to the current directory
        if self._cwd != "/":
            # Get the current Windows path
            current_fs_path = self.getcwfs()
            
            # Add the relative path to the current path
            new_path = os.path.normpath(os.path.join(current_fs_path, ftppath))
            print(f"ftp2fs: Relative path from {current_fs_path} -> {new_path}")
            return new_path
        
        # Shouldn't reach here, but return the root path for safety
        print(f"ftp2fs: Unexpected case, returning root for {ftppath}")
        return self.root
    def fs2ftp(self, fspath):
        """Convert a system path to an FTP path"""
        print(f"fs2ftp: Converting system path: {fspath}")
        
        if fspath == self.root or fspath == "/":
            return "/"
        
        # Check if it's a Windows drive path (e.g., C:\)
        if len(fspath) >= 2 and fspath[1] == ":":
            drive_letter = fspath[0].upper()
            
            # If it's just the drive (e.g., C:\ or C:)
            if len(fspath) <= 3:
                return "/" + drive_letter
            
            # Otherwise, build the FTP path with the remaining components
            path_parts = fspath[3:].replace("\\", "/").split("/")
            path_parts = [p for p in path_parts if p]  # Remove empty components
            
            if not path_parts:
                return "/" + drive_letter
                
            ftp_path = "/" + drive_letter + "/" + "/".join(path_parts)
            print(f"fs2ftp: FTP path for drive: {ftp_path}")
            return ftp_path
        
        # Unexpected case, return root
        print(f"fs2ftp: Unexpected case, returning root for {fspath}")
        return "/"
    
    def getcwfs(self):
        """Get the current path in file system format"""
        return self.ftp2fs(self.getcwd())
    
    def listdir(self, path):
        """List the contents of the directory"""
        try:
            print(f"listdir: Listing directory {path}")
            
            # Special case when we receive '.' or '' and are on a drive
            if (path == '.' or path == '') and self._cwd.startswith('/') and len(self._cwd) == 2:
                disk_letter = self._cwd[1]
                disk_path = disk_letter + ":\\"
                print(f"listdir: Special case - listing for current directory {disk_path}")
                
                try:
                    items = os.listdir(disk_path)
                    print(f"listdir: Found {len(items)} items in the current drive {disk_path}")
                    return items
                except Exception as e:
                    print(f"listdir: Error listing the current drive {disk_path}: {e}")
                    raise
            
            if path == self.root or path == "/":
                # At root, display all available drives
                drives = []
                for d in win32api.GetLogicalDriveStrings().split('\000'):
                    if d:  # Check that d is not an empty string
                        # Extract only the drive letter
                        drive_letter = d[0].upper()
                        drives.append(drive_letter)
                print(f"listdir: Returning drives: {drives}")
                return drives
            
            # Check if it's a valid drive (e.g., C:\)
            if (len(path) == 3 and path[1:] == ":\\") or path.endswith(":\\"):
                try:
                    items = os.listdir(path)
                    print(f"listdir: Found {len(items)} items in drive {path}")
                    return items
                except Exception as e:
                    print(f"listdir: Error listing the drive {path}: {e}")
                    raise
            
            # Check the case where we have an absolute Windows path
            if os.path.exists(path) and os.path.isdir(path):
                try:
                    items = os.listdir(path)
                    print(f"listdir: Found {len(items)} items in directory {path}")
                    return items
                except Exception as e:
                    print(f"listdir: Error listing the directory {path}: {e}")
                    raise
            
            # Special case - if we receive only a drive letter, build the complete path
            if len(path) == 1 and path.isalpha():
                disk_path = path.upper() + ":\\"
                if os.path.exists(disk_path):
                    try:
                        items = os.listdir(disk_path)
                        print(f"listdir: Found {len(items)} items in the drive {disk_path}")
                        return items
                    except Exception as e:
                        print(f"listdir: Error listing the drive {disk_path}: {e}")
                        raise
            
            # Invalid path
            raise OSError(f"Invalid or inaccessible path: {path}")
            
        except Exception as e:
            # Log error
            print(f"listdir: Error listing the directory {path}: {str(e)}")
            raise
    
    def chdir(self, path):
        """Change the current directory"""
        print(f"chdir: Attempting to change directory to {path}")
        
        # If it's the root, just update the current path
        if path == self.root or path == "/":
            self._cwd = "/"
            print("chdir: Set directory to root (/)")
            return
        
        # If it's navigating back (..), handle specially
        if path == "..":
            # If we're at the root, stay there
            if self._cwd == "/":
                print("chdir: Already at root, staying there")
                return
                
            # If we're on a drive (e.g., /C), go back to /
            if self._cwd.count('/') == 1 and len(self._cwd) == 2:
                self._cwd = "/"
                print("chdir: Navigating back to root from drive")
                return
                
            # Otherwise, navigate back in the directory hierarchy
            parent_dir = os.path.dirname(self.getcwfs())
            self._cwd = self.fs2ftp(parent_dir)
            print(f"chdir: Navigating back to {self._cwd}")
            return
        
        # Check if it's a single letter (possible drive)
        if len(path) == 1 and path.isalpha():
            drive = path.upper() + ":\\"
            if os.path.exists(drive):
                # Update the current FTP path
                self._cwd = "/" + path.upper()
                print(f"chdir: Set directory to drive {self._cwd}")
                return
                
        # Case where we receive a complete drive path (e.g., C:\)
        if len(path) == 3 and path[1:] == ":\\":
            drive_letter = path[0].upper()
            if os.path.exists(path):
                self._cwd = "/" + drive_letter
                print(f"chdir: Set directly to drive {self._cwd}")
                return
        
        # For any other case, check if the path exists and is a directory
        try:
            # Check if path is absolute or relative
            if os.path.isabs(path):
                # If it's absolute, check if it exists
                if not os.path.exists(path):
                    raise OSError(f"Directory does not exist: {path}")
                    
                if not os.path.isdir(path):
                    raise OSError(f"Not a directory: {path}")
                    
                # Update the current FTP path directly
                self._cwd = self.fs2ftp(path)
                print(f"chdir: Set directory to absolute path: {self._cwd}")
            else:
                # If it's relative, combine it with the current directory
                current_fs_path = self.getcwfs()
                new_path = os.path.join(current_fs_path, path)
                
                if not os.path.exists(new_path):
                    raise OSError(f"Directory does not exist: {new_path}")
                    
                if not os.path.isdir(new_path):
                    raise OSError(f"Not a directory: {new_path}")
                
                # Update the current FTP path
                self._cwd = self.fs2ftp(new_path)
                print(f"chdir: Set directory to relative path: {self._cwd}")
        except OSError as e:
            print(f"chdir: Error - {str(e)}")
            raise
    
    # IMPORTANT: Override the method to ignore root directory check
    def validpath(self, path):
        """Check if a path is valid.
        Unlike the standard implementation, we allow access anywhere,
        without root directory restrictions."""
        # Always return True to allow access anywhere
        return True
    
    def getcwd(self):
        """Get the current directory"""
        return self._cwd
    
    def isfile(self, path):
        """Check if the path is a file"""
        # Root is not a file
        if path == self.root or path == "/":
            return False
            
        # If it's just a letter at the root, it's a drive
        if len(path) == 1 and path.isalpha():
            return False
            
        # Otherwise, use the standard check
        try:
            return os.path.isfile(path)
        except:
            return False
    
    def isdir(self, path):
        """Check if the path is a directory"""
        # Root is a directory
        if path == self.root or path == "/":
            return True
            
        # If it's just a letter, check if a drive with that letter exists
        if len(path) == 1 and path.isalpha():
            return os.path.exists(path.upper() + ":\\")
        
        # If it's a complete drive (e.g., "C:\\")
        if len(path) == 3 and path[1:] == ":\\":
            return os.path.exists(path)
            
        # Otherwise, use the standard check
        try:
            return os.path.isdir(path)
        except:
            return False
            
    def realpath(self, path):
        """Return the absolute path"""
        return path
        
    def chmod(self, path, mode):
        """Change file permissions - ignored for Windows"""
        pass

    def mkdir(self, path):
        """Create a directory"""
        print(f"mkdir: Attempting to create directory {path}")
        
        # Determine the complete path in the file system
        fs_path = self.ftp2fs(path)
        
        # Check if the directory already exists
        if os.path.exists(fs_path):
            if os.path.isdir(fs_path):
                print(f"mkdir: Directory already exists: {fs_path}")
                # It's not an error if the directory already exists
                return
            else:
                raise OSError(f"Cannot create directory. A file with the same name already exists: {fs_path}")
                
        try:
            os.makedirs(fs_path)
            print(f"mkdir: Directory created successfully: {fs_path}")
        except OSError as e:
            print(f"mkdir: Error creating directory {fs_path}: {str(e)}")
            raise
            
    def rmdir(self, path):
        """Delete a directory"""
        print(f"rmdir: Attempting to delete directory {path}")
        
        # Determine the complete path in the file system
        fs_path = self.ftp2fs(path)
        
        # Check if the directory exists
        if not os.path.exists(fs_path):
            print(f"rmdir: Directory does not exist: {fs_path}")
            raise OSError(f"Directory does not exist: {fs_path}")
            
        # Check if it's a directory
        if not os.path.isdir(fs_path):
            print(f"rmdir: Not a directory: {fs_path}")
            raise OSError(f"Not a directory: {fs_path}")
            
        # Check if the directory is empty
        if os.listdir(fs_path):
            print(f"rmdir: Directory is not empty: {fs_path}")
            raise OSError(f"Directory is not empty: {fs_path}")
            
        try:
            os.rmdir(fs_path)
            print(f"rmdir: Directory deleted successfully: {fs_path}")
        except OSError as e:
            print(f"rmdir: Error deleting directory {fs_path}: {str(e)}")
            raise
            
    def remove(self, path):
        """Delete a file"""
        print(f"remove: Attempting to delete file {path}")
        
        # Determine the complete path in the file system
        fs_path = self.ftp2fs(path)
        
        # Check if the file exists
        if not os.path.exists(fs_path):
            print(f"remove: File does not exist: {fs_path}")
            raise OSError(f"File does not exist: {fs_path}")
            
        # Check if it's a file (not a directory)
        if not os.path.isfile(fs_path):
            print(f"remove: Not a file: {fs_path}")
            raise OSError(f"Not a file: {fs_path}")
            
        try:
            os.remove(fs_path)
            print(f"remove: File deleted successfully: {fs_path}")
        except OSError as e:
            print(f"remove: Error deleting file {fs_path}: {str(e)}")
            raise

class SQLiteAuthorizer(DummyAuthorizer):
    """Authorizer that uses SQLite for authentication"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        
        # Initialize the dictionary for virtual locations
        self.virtual_locations = {}
        
        # Load users from the database
        self._load_users_from_db()
    
    def _load_users_from_db(self):
        """Load users from the database into the authorizer"""
        try:
            users = self.db_manager.get_all_users()
            
            for user in users:
                username = user["username"]
                permissions = user["permissions"]
                home_dir = user["home_dir"]
                
                # Add the user to the authorizer
                # Do not set the password here, as we will override validate_authentication
                try:
                    self.add_user(username, "dummy_password", home_dir, perm=permissions)
                    print(f"User loaded from database: {username}")
                    
                    # Generate virtual locations for the user
                    self.virtual_locations[username] = self._generate_virtual_locations(home_dir)
                except ValueError as e:
                    print(f"Error loading user {username}: {str(e)}")
        except Exception as e:
            print(f"Error loading users from database: {str(e)}")
            # Ensure the dictionary exists even if there are errors during loading
            self.virtual_locations = {}
    
    def _generate_virtual_locations(self, home_dir):
        """Generate virtual locations to access other drives"""
        virtual_locs = {}
        
        # If home_dir is a specific drive (e.g., C:\)
        if len(home_dir) >= 2 and home_dir[1] == ':':
            home_drive = home_dir[0].upper()
            
            # For each available drive, add a virtual folder if it's not the home drive
            for drive_letter in self._get_available_drives():
                if drive_letter != home_drive:
                    virtual_folder = f"Disc_{drive_letter}"
                    virtual_locs[virtual_folder] = f"{drive_letter}:\\"
        
        return virtual_locs
    
    def _get_available_drives(self):
        """Return the list of available drives in the system"""
        drives = []
        for d in win32api.GetLogicalDriveStrings().split('\000'):
            if d:  # Check that d is not an empty string
                # Extract only the drive letter
                drive_letter = d[0].upper()
                drives.append(drive_letter)
        return drives
    
    def validate_authentication(self, username, password, handler):
        """Verify user authentication using the database"""
        print(f"validate_authentication: Verifying authentication for '{username}'")
        
        # Check anonymous authentication first to avoid unnecessary checks
        if username == 'anonymous':
            print(f"validate_authentication: Anonymous authentication accepted")
            handler.initial_cwd = "/"
            return True
        
        # Check credentials in the database
        user_data = self.db_manager.authenticate_user(username, password)
        
        if user_data:
            # Successful authentication - set the initial directory for the user
            handler.initial_cwd = user_data["home_dir"]
            print(f"validate_authentication: User '{username}' successfully authenticated")
            print(f"validate_authentication: Home directory set: {user_data['home_dir']}")
            return True
        
        # Failed authentication - display additional details for debugging
        print(f"validate_authentication: Authentication failed for '{username}'")
        print(f"validate_authentication: Check password hashes and salts in the logging above")
        return False
    
    def get_home_dir(self, username):
        """Return the home directory for the user"""
        if username == 'anonymous':
            return "/"
            
        # Get the user from the database
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT home_dir FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            
            if result:
                home_dir = result[0]
                if home_dir:
                    return home_dir
        finally:
            conn.close()
            
        # Return the root directory as a fallback
        return "/"
    
    def get_virtual_locations(self, username):
        """Return the dictionary with virtual locations for the user"""
        # Check if the user exists in the dictionary
        if not hasattr(self, 'virtual_locations'):
            self.virtual_locations = {}
        return self.virtual_locations.get(username, {})
    
    def has_perm(self, username, perm, path=None):
        """Check if the user has the necessary permissions for the specified path"""
        print(f"has_perm: Checking permissions for {username}, perm={perm}, path={path}")
        
        # Always allow navigation and listing in the root directory
        if path == "/":
            if perm in ('e', 'l'):
                print(f"has_perm: Allowing access to root for {username}")
                return True
                
        if username == 'anonymous':
            return perm in ('e', 'l', 'r')
            
        # Get user information from the database
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT permissions, home_dir FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            
            if result:
                user_permissions, home_dir = result
                
                # Check if the user has the specific permission
                if perm not in user_permissions:
                    return False
                
                # If no specific path is provided or the user has access to everything (/)
                if not path or home_dir == "/":
                    return True
                
                # Convert the path to Windows format for comparison
                win_path = self._ftp_path_to_windows(path)
                
                # Check if the user is trying to navigate to a specific drive
                if win_path.startswith("/"):
                    if len(win_path) > 1 and win_path[1].isalpha():
                        # It's a path like /C or /C/...
                        if len(home_dir) >= 2 and home_dir[1] == ":":
                            # Home dir is a specific drive (C:\) or a specific directory (C:\Users\...)
                            home_disk = home_dir[0].upper()
                            path_disk = win_path[1].upper()
                            
                            # If navigating to root or the drive is different
                            if win_path == "/" or (path_disk != home_disk):
                                # If it's just an attempt to list available drives, allow it
                                if win_path == "/" and perm == "l":
                                    print(f"Allowing user {username} to list root to see drives")
                                    return True
                                else:
                                    print(f"Access denied: User {username} is trying to access drive {path_disk} instead of {home_disk}")
                                    return False
                            
                            # If the user is trying to navigate exactly to the home drive, allow it
                            if win_path == f"/{home_disk}" and len(home_dir) == 3 and home_dir[1:] == ":\\":
                                return True
                            
                            # Check if trying to access a subdirectory of the home directory
                            # Normalize both paths for comparison
                            if len(home_dir) > 3:  # Home dir is a specific folder, not just a drive
                                # Convert the FTP path to Windows format
                                if win_path.startswith(f"/{home_disk}/"):
                                    # Reconstruct the full path
                                    full_path = f"{home_disk}:{win_path[3:]}"
                                    
                                    # Normalize paths for comparison
                                    full_path_norm = os.path.normpath(full_path).replace("\\", "/")
                                    home_dir_norm = os.path.normpath(home_dir).replace("\\", "/")
                                    
                                    # Allow access if:
                                    # 1. It is exactly the home directory
                                    # 2. It is a subdirectory of the home directory
                                    if full_path_norm == home_dir_norm or full_path_norm.startswith(home_dir_norm + "/"):
                                        return True
                                    else:
                                        print(f"Access denied: {full_path_norm} is not within {home_dir_norm}")
                                        return False
                
                # If it's not a normal path or the format is not recognized, check directly
                return self._is_path_allowed(win_path, home_dir)
                
        finally:
            conn.close()
            
        return False
    
    def _ftp_path_to_windows(self, path):
        """Convert an FTP path to Windows format for comparison"""
        if not path:
            return ""
            
        # Keep the FTP path for direct comparison
        return path
    
    def _is_path_allowed(self, path, home_dir):
        """Check if a path is allowed relative to the home directory"""
        # If home_dir is root, all paths are allowed
        if home_dir == "/":
            return True
            
        try:
            # Check if home_dir is a drive (e.g., C:\)
            if len(home_dir) == 3 and home_dir[1:] == ":\\":
                home_disk = home_dir[0].upper()
                
                # Handle case for FTP paths (/C/...)
                if path.startswith("/"):
                    if len(path) > 1 and path[1].isalpha():
                        path_disk = path[1].upper()
                        return path_disk == home_disk
                    return False
                    
                # Handle case for Windows paths (C:\...)
                if len(path) >= 2 and path[1] == ":":
                    path_disk = path[0].upper()
                    return path_disk == home_disk
                    
                return False
                
            # For specific directories, check if path starts with home_dir
            # Normalize paths for comparison
            norm_path = os.path.normpath(path).replace("\\", "/")
            norm_home = os.path.normpath(home_dir).replace("\\", "/")
            
            return norm_path == norm_home or norm_path.startswith(norm_home + "/")
        except Exception as e:
            print(f"is_path_allowed: Error checking path {path}: {str(e)}")
            return False

    def make_list_producer(self, drives=None):
        """Create a producer to list files"""
        print(f"make_list_producer: Current FTP path: {self.fs._cwd}")
        
        # Special case for listing drives
        if drives and self.fs._cwd == "/":
            print(f"make_list_producer: Listing drives: {drives}")
            
            from pyftpdlib._compat import b
            from io import StringIO
            from time import localtime
            
            timefunc = localtime
            
            assert self._current_type in ("a", "i")
            is_binary = self._current_type == "i"
            
            # Create a temporary file to collect results
            iterator = StringIO()
            
            # For each drive, add a line in the standard LIST format
            for drive in drives:
                # Generate a line in DIR format that simulates a directory
                # Standard format: "drwxr-xr-x   1 owner    group           0 Jan 01  1970 dirname"
                line = f"drwxr-xr-x   1 owner    group           0 Jan 01  1970 {drive}\r\n"
                iterator.write(line)
            
            # Reset position to the beginning
            iterator.seek(0)
            
            # Create the producer function
            def producer():
                """Return the content of the iterator"""
                done = False
                
                while not done:
                    data = iterator.read(8192)  # Read in blocks
                    if not data:
                        done = True
                    elif is_binary:
                        yield b(data)
                    else:
                        yield data
            
            return producer
        else:
            # Use the standard implementation for other cases
            return super().make_list_producer()

class CustomFTPHandler(FTPHandler):
    def __init__(self, conn, server, ioloop=None):
        super().__init__(conn, server, ioloop)
        self.initial_cwd = None  # Will be set upon authentication
        # Store the result of authentication validation for later use
        self.authentication_validated = False
        
        # Ensure the file system is initialized before authentication
        if not hasattr(self, 'fs') or self.fs is None:
            try:
                # Initialize FS with the specified AbstractedFS class
                self.fs = self.abstracted_fs('/', self)
                self.fs._cwd = "/"
                print("__init__: Initialized the filesystem")
            except Exception as e:
                print(f"__init__: Error initializing FS: {str(e)}")
                # Try directly with WindowsRootFS
                self.fs = WindowsRootFS('/', self)
                self.fs._cwd = "/"
                print("__init__: Initialized the filesystem directly with WindowsRootFS")
    
    def ftp_PASS(self, line):
        """Override the ftp_PASS method to ensure correct authentication"""
        # Check if a USER has been provided
        if not self.username:
            self.respond("503 USER command required before PASS.")
            return
            
        print(f"ftp_PASS: Checking password for user '{self.username}'")
        
        # Store the password for debugging
        password = line
        
        # Verify authentication directly through validate_authentication
        if self.authorizer.validate_authentication(self.username, password, self):
            self.authentication_validated = True
            # Successful authentication
            print(f"ftp_PASS: Successful authentication for '{self.username}'")
            
            # Set the user as authenticated
            self.authenticated = True
            
            # Check if it's anonymous or not
            if not self.username == 'anonymous':
                self.respond('230 Successful authentication.')
                self.log("USER '%s' logged in." % self.username)
            else:
                self.respond('230 Anonymous authentication accepted.')
                self.log("Anonymous USER logged in.")
                
            # Call on_login to initialize the current directory
            self.on_login(self.username)
        else:
            # Failed authentication
            print(f"ftp_PASS: Authentication failed for '{self.username}'")
            
            # Reset authentication
            self.authenticated = False
            self.username = ""
            
            # Increase the failed attempts counter
            self.attempted_logins += 1
            
            # Respond with an error message
            self.respond('530 Authentication failed: incorrect username or password.')
            self.log("Authentication failed (invalid credentials).", self.username)
            
    def on_login(self, username):
        """Override the on_login method to navigate directly to the home directory"""
        # Check if authentication has been validated
        if not self.authentication_validated:
            print(f"on_login: WARNING - Login attempt without validation for {username}")
            return
            
        try:
            # Call the parent method to ensure correct initialization of fs
            super().on_login(username)
            
            # Ensure initial_cwd is set
            if not hasattr(self, 'initial_cwd') or self.initial_cwd is None:
                if username == 'anonymous':
                    self.initial_cwd = "/"
                else:
                    # Get home directory from authorizer
                    try:
                        self.initial_cwd = self.authorizer.get_home_dir(username)
                    except Exception as e:
                        print(f"on_login: Error obtaining home directory: {str(e)}")
                        self.initial_cwd = "/"
                        
            print(f"on_login: User {username} has home directory: {self.initial_cwd}")
            
            # Check if fs is correctly initialized
            if not hasattr(self, 'fs') or self.fs is None:
                print(f"on_login: fs object is not initialized, creating a new one")
                # Create and initialize a new AbstractedFS object
                self.fs = self.abstracted_fs('/', self)
            
            # Navigate directly to the user's home directory
            if self.initial_cwd:
                if self.initial_cwd == "/":
                    # Leave as is, user remains in root
                    self.fs._cwd = "/"
                    print(f"on_login: User {username} has been set to root")
                elif os.path.exists(self.initial_cwd):
                    # Convert Windows path to FTP format
                    if len(self.initial_cwd) >= 2 and self.initial_cwd[1] == ':':
                        # It's a drive path (C:\...)
                        drive_letter = self.initial_cwd[0].upper()
                        
                        if len(self.initial_cwd) == 3 and self.initial_cwd.endswith(':\\'):
                            # It's just a drive (C:\)
                            ftp_path = f"/{drive_letter}"
                        else:
                            # It's a subdirectory (C:\Users\...)
                            subpath = self.initial_cwd[3:].replace('\\', '/')
                            ftp_path = f"/{drive_letter}/{subpath}"
                            
                        # Update the current path
                        self.fs._cwd = ftp_path
                        print(f"on_login: User {username} has been directed to {ftp_path}")
        except Exception as e:
            print(f"on_login: General error: {str(e)}")
            # Ensure there is a valid fs object
            if not hasattr(self, 'fs') or self.fs is None:
                self.fs = self.abstracted_fs('/', self)
            # Set path to root in case of error
            self.fs._cwd = "/"
            print(f"on_login: Set path to root following error")
    
    def ftp_CWD(self, path):
        # Check if it is a virtual location
        try:
            if hasattr(self.authorizer, 'get_virtual_locations') and callable(getattr(self.authorizer, 'get_virtual_locations')):
                virtual_locations = self.authorizer.get_virtual_locations(self.username)
                current_dir = self.fs.getcwd()
                
                # If we are in the home directory and path is a virtual folder
                if path in virtual_locations:
                    target_location = virtual_locations[path]
                    print(f"ftp_CWD: Virtual redirection {path} -> {target_location}")
                    
                    # Convert to FTP path
                    if len(target_location) >= 2 and target_location[1] == ':':
                        drive_letter = target_location[0].upper()
                        ftp_path = f"/{drive_letter}"
                        
                        # Check if the user has access to this drive
                        if not self.authorizer.has_perm(self.username, 'e', target_location):
                            self.respond('550 Not enough privileges.')
                            return
                            
                        self.fs._cwd = ftp_path
                        self.respond('250 Virtual navigation successful.')
                        return
        except Exception as e:
            print(f"ftp_CWD: Error checking virtual locations: {str(e)}")
        
        # Normal processing for other paths
        try:
            print(f"ftp_CWD: Navigation request to {path}")
            
            # Special case for navigating to root
            if path == "/":
                # Allow navigation to root if the user has access to everything
                if hasattr(self, 'initial_cwd') and self.initial_cwd == "/":
                    self.fs._cwd = "/"
                    self.respond('250 Navigation to root successful.')
                else:
                    # For other users, send them to their home directory
                    if hasattr(self, 'on_login') and callable(getattr(self, 'on_login')):
                        self.on_login(self.username)
                    self.respond('250 Navigation to home directory successful.')
                return
            
            # Handle drives (C:, C:\, etc.) specially
            if len(path) == 2 and path[1] == ":" or (len(path) == 3 and path[1:] == ":\\"):
                disk = path[0].upper()
                disk_path = disk + ":\\"
                
                if os.path.exists(disk_path):
                    # Check if the user has access to this drive
                    if not self.authorizer.has_perm(self.username, 'e', disk_path):
                        self.respond('550 Not enough privileges.')
                        return
                        
                    print(f"ftp_CWD: Special navigation to drive {disk_path}")
                    self.fs._cwd = "/" + disk
                    self.respond('250 Navigation to drive successful.')
                    return
            
            # Case for a single character (possible drive)
            if len(path) == 1 and path.isalpha():
                disk = path.upper()
                disk_path = disk + ":\\"
                
                if os.path.exists(disk_path):
                    # Check if the user has access to this drive
                    if not self.authorizer.has_perm(self.username, 'e', disk_path):
                        self.respond('550 Not enough privileges.')
                        return
                        
                    print(f"ftp_CWD: Navigation to drive {disk_path}")
                    self.fs._cwd = "/" + disk
                    self.respond('250 Navigation to drive successful.')
                    return
            
            # Normal processing for other types of paths
            fs_path = self.fs.ftp2fs(path)
            print(f"ftp_CWD: Path converted to {fs_path}")
            
            if not self.fs.isdir(fs_path):
                why = f"'{path}' is not a valid directory."
                print(f"ftp_CWD: Error - {why}")
                self.respond("550 %s" % why)
            else:
                # Check permissions
                if not self.authorizer.has_perm(self.username, 'e', path):
                    self.respond('550 Not enough privileges.')
                    return
                    
                self.fs.chdir(fs_path)
                print(f"ftp_CWD: Current directory after navigation: {self.fs._cwd}")
                self.respond('250 Directory change command successful.')
        except FilesystemError as err:
            print(f"ftp_CWD: Error - {str(err)}")
            self.respond('550 %s.' % err)
        except Exception as e:
            print(f"ftp_CWD: General error: {str(e)}")
            self.respond('550 Navigation error.')
    
    def ftp_LIST(self, path):
        """Override the LIST method to correctly handle directory listing and virtual folders"""
        try:
            print(f"ftp_LIST: Listing request for {path}")
            
            # Check if fs is correctly initialized
            if not hasattr(self, 'fs') or self.fs is None:
                print(f"ftp_LIST: fs object is not initialized, creating a new one")
                self.fs = self.abstracted_fs('/', self)
                self.fs._cwd = "/"
            
            # Check if we are in the home directory and need to display virtual folders
            try:
                if hasattr(self.authorizer, 'get_virtual_locations') and callable(getattr(self.authorizer, 'get_virtual_locations')):
                    virtual_locations = self.authorizer.get_virtual_locations(self.username)
                    current_dir = self.fs.getcwd()
                    
                    # Check if we are in the user's home directory and need to display virtual locations
                    if hasattr(self, 'initial_cwd') and self.initial_cwd != "/" and (path == "" or path == ".") and virtual_locations:
                        # Check if it's the user's home directory
                        if current_dir.startswith("/"):
                            # Prepare the response
                            self.respond('150 Directory listing in progress.')
                            
                            try:
                                # Open the connection for transfer
                                with self.dtp_handler.get_data_sock(self._current_type) as sock:
                                    # Get the normal listing
                                    normal_list = []
                                    
                                    # Use the standard implementation to list normal content
                                    # But capture the result to combine it with virtual folders
                                    original_respond = self.respond
                                    self.respond = lambda x: None  # Temporarily disable responses
                                    
                                    try:
                                        # Get the normal listing using super().ftp_LIST
                                        super().ftp_LIST(path)
                                    except Exception as e:
                                        print(f"Error listing normal content: {e}")
                                    
                                    # Reactivate responses
                                    self.respond = original_respond
                                    
                                    # Now add virtual folders
                                    from pyftpdlib._compat import b
                                    from io import StringIO
                                    from time import localtime
                                    
                                    # Create a producer for normal content and virtual folders
                                    iterator = StringIO()
                                    
                                    # Add virtual folders in DIR format
                                    for folder_name in virtual_locations:
                                        line = f"drwxr-xr-x   1 owner    group           0 Jan 01  2023 {folder_name}\r\n"
                                        iterator.write(line)
                                    
                                    # Reset position to the beginning
                                    iterator.seek(0)
                                    
                                    # Producer function
                                    def producer():
                                        """Return the content of the iterator"""
                                        done = False
                                        is_binary = self._current_type == "i"
                                        
                                        while not done:
                                            data = iterator.read(8192)  # Read in blocks
                                            if not data:
                                                done = True
                                            elif is_binary:
                                                yield b(data)
                                            else:
                                                yield data
                                    
                                    # Send the data
                                    producer().send(sock)
                                
                                self.respond('226 Transfer complete.')
                                return
                            except Exception as e:
                                print(f"ftp_LIST: Error listing virtual folders: {e}")
                                self.respond('550 Error: ' + str(e))
                                return
            except Exception as e:
                print(f"ftp_LIST: Error checking virtual locations: {str(e)}")
            
            # For all other cases, use the standard implementation
            return super().ftp_LIST(path)
            
        except Exception as e:
            print(f"ftp_LIST: General error: {str(e)}")
            self.respond(f"550 Listing error: {str(e)}")

def main():
    # Initialize the database manager
    db_manager = UserDatabase()
    
    # Create an authorizer that uses the database
    authorizer = SQLiteAuthorizer(db_manager)
    
    # Add an anonymous user with read permissions
    authorizer.add_anonymous("/", perm="elr")
    
    # Configure handler
    handler = CustomFTPHandler
    handler.authorizer = authorizer
    handler.abstracted_fs = WindowsRootFS
    
    # Disable checking if the directory is in root (not relevant for our virtual system)
    handler.permit_foreign_addresses = True
    handler.permit_privileged_ports = True
    
    # Set the format for logging (correct)
    handler.log_prefix = "%(username)s@%(remote_ip)s"
    handler.use_sendfile = False  # Disable sendfile for more compatibility
    
    # Enable debugging to track errors
    handler.dtp_handler.ac_in_buffer_size = 32768
    handler.dtp_handler.ac_out_buffer_size = 32768
    
    # Increase the timeout for operations
    handler.timeout = 300  # 5 minutes
    
    # We can set welcome messages
    handler.banner = "Welcome to the FTP server with access to all drives! Authentication with SQLite."
    
    # Define the address for the server (0.0.0.0 to listen on all interfaces)
    address = ("0.0.0.0", 2121)
    server = FTPServer(address, handler)
    
    # Set the connection limit
    server.max_cons = 256
    server.max_cons_per_ip = 5
    
    print(f"FTP server running at {address[0]}:{address[1]}")
    print(f"Or anonymous connection")
    print("Press Ctrl+C to stop the server")
    
    # Start the server
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping FTP server...")
    except Exception as e:
        print(f"Server error: {str(e)}")
    finally:
        print("FTP server stopped")