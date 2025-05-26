"""
Panel for navigating and managing files on an FTP server
"""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QPushButton,
                             QMessageBox, QFileDialog, QMenu, QAction, QInputDialog,
                             QDialog, QMainWindow, QApplication)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from ftp_client import FTPClient
from ftp_client.ui.connection_dialog import FTPConnectionDialog
from ftp_client.ui.common.styles import TITLE_LABEL_STYLE


class FTPPanel(QWidget):
    """Panel for navigating an FTP server"""

    def __init__(self, parent=None, file_manager=None):
        """Initialize FTP panel
        
        Args:
            parent: Parent component
            file_manager: Reference to the main window
        """
        super().__init__(parent)
        
        # Reference to the main window for displaying messages
        self.file_manager = file_manager
        
        # Initialize member variables
        self.ftp_client = None
        self.current_directory = ""
        self.connection_type = "ftp"  # ftp or sftp
        self.connection_id = None  # Connection ID from the database, if it exists
        
        # Double-click protection to avoid threading issues
        self.double_click_protection = False
        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self.reset_click_protection)
        
        # Initialize UI
        self.setup_ui()
        self.connect_signals()
        
        # Initialize FTPClient
        from ftp_client import FTPClient
        self.ftp_client = FTPClient()
        self.connect_signals()

    def closeEvent(self, event):
        """Handles the widget close event"""
        # Ensure we disconnect from FTP when the panel is closed
        if self.ftp_client and self.ftp_client.is_connected:
            self.ftp_client.disconnect()
        super().closeEvent(event)

    def hideEvent(self, event):
        """Handles the widget hide event"""
        # Ensure threads terminate when the application closes
        if self.ftp_client and self.ftp_client.is_connected:
            self.ftp_client.disconnect()
        super().hideEvent(event)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)  # Smaller margins for a modern look

        # Connection buttons
        connection_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect FTP")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        self.status_label = QLabel("Disconnected")

        connection_layout.addWidget(self.connect_btn)
        connection_layout.addWidget(self.disconnect_btn)
        connection_layout.addWidget(self.status_label)
        connection_layout.addStretch()

        layout.addLayout(connection_layout)

        # Add field for FTP navigation path
        path_layout = QHBoxLayout()
        path_label = QLabel('Remote site:')
        
        # Add a button for navigating back
        self.back_btn = QPushButton("↑")
        self.back_btn.setToolTip("Navigate to parent directory")
        self.back_btn.setFixedWidth(30)
        self.back_btn.setEnabled(False)  # Initially disabled until connected
        
        self.ftp_path_input = QLineEdit()
        self.ftp_path_input.setPlaceholderText('Enter path...')
        self.ftp_path_input.returnPressed.connect(self.navigate_to_ftp_path)
        # Initially disabled until connected
        self.ftp_path_input.setEnabled(False)

        path_layout.addWidget(path_label)
        path_layout.addWidget(self.back_btn)
        path_layout.addWidget(self.ftp_path_input)
        layout.addLayout(path_layout)

        # FTP file list
        self.file_list = QListWidget()
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(
            self.show_context_menu)

        layout.addWidget(self.file_list)

        # Button bar
        buttons_layout = QHBoxLayout()

        self.upload_btn = QPushButton("Upload")
        self.download_btn = QPushButton("Download")
        self.create_dir_btn = QPushButton("Create Directory")
        self.delete_btn = QPushButton("Delete")

        buttons_layout.addWidget(self.upload_btn)
        buttons_layout.addWidget(self.download_btn)
        buttons_layout.addWidget(self.create_dir_btn)
        buttons_layout.addWidget(self.delete_btn)

        layout.addLayout(buttons_layout)

    def connect_signals(self):
        # Buttons
        self.connect_btn.clicked.connect(self.show_connection_dialog)
        self.disconnect_btn.clicked.connect(self.disconnect)
        self.upload_btn.clicked.connect(self.upload_file)
        self.download_btn.clicked.connect(self.download_file)
        self.create_dir_btn.clicked.connect(self.create_directory)
        self.delete_btn.clicked.connect(self.delete_item)
        
        # Back navigation button
        if hasattr(self, 'back_btn'):
            self.back_btn.clicked.connect(self.navigate_back_directly)

        # Double-click on item
        self.file_list.itemDoubleClicked.connect(self.item_double_clicked)

        # Disconnect existing signals to avoid double connections
        if self.ftp_client:
            try:
                self.ftp_client.connected.disconnect()
                self.ftp_client.disconnected.disconnect()
                self.ftp_client.error.disconnect()
                self.ftp_client.directory_listed.disconnect()
                self.ftp_client.file_downloaded.disconnect()
                self.ftp_client.file_uploaded.disconnect()
            except (TypeError, RuntimeError):
                # Ignore disconnection errors - can occur if no signals are connected
                pass

        if self.ftp_client:
            # FTP signals
            self.ftp_client.connected.connect(self.on_connected)
            self.ftp_client.disconnected.connect(self.on_disconnected)
            self.ftp_client.error.connect(self.on_error)
            self.ftp_client.directory_listed.connect(
                self.display_directory_contents)
            self.ftp_client.file_downloaded.connect(self.on_file_downloaded)
            self.ftp_client.file_uploaded.connect(self.on_file_uploaded)

    def show_connection_dialog(self):
        dialog = FTPConnectionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            connection_info = dialog.get_connection_info()

            # Display connection type for debugging
            connection_type = connection_info.get("connection_type", "ftp")
            key_file = connection_info.get("key_file")
            key_file_info = f"\nPrivate key: {key_file}" if key_file else ""

            # Replace QMessageBox with an informative message in the message area
            self.show_message(
                f"Connecting to {connection_info['host']}:{connection_info['port']} as {connection_info['username']}", 
                "info"
            )

            # Save the connection ID to pass it to the appropriate client
            self.connection_id = connection_info.get("id")
            self.connection_type = connection_type

            # Create the appropriate client
            if connection_type == "sftp":
                from ftp_client.sftp_client import SFTPClient
                self.ftp_client = SFTPClient()
            else:
                from ftp_client import FTPClient
                self.ftp_client = FTPClient()

            # Reconnect signals for the new client
            self.connect_signals()

            self.connect_to_ftp(
                connection_info["host"],
                connection_info["port"],
                connection_info["username"],
                connection_info["password"],
                connection_info.get("key_file"),
                connection_info.get("key_passphrase")
            )

            # Update last use in the database if it was a saved connection
            if connection_info.get("save") and "id" in connection_info:
                from ftp_client.utils.database import ConnectionDatabase
                db = ConnectionDatabase()
                db.update_last_used(connection_info["id"])

    def connect_to_ftp(self, host, port, username, password, key_file=None, key_passphrase=None):
        """Connect to FTP/SFTP server"""
        self.status_label.setText("Connecting...")
        
        # Verificăm dacă există o încercare de conectare în progres
        if hasattr(self, 'connection_thread') and self.connection_thread and self.connection_thread.isRunning():
            # Încercăm să anulăm vechiul thread de conectare
            try:
                self.status_label.setText("Anulare conexiune anterioară...")
                self.connection_thread.terminate()
                self.connection_thread.wait(1000)  # Așteptăm maxim 1 secundă
                self.show_message("Încercare de conectare anterioară anulată", "warning")
                # Restaurăm cursorul normal dacă a fost în mod de așteptare
                QApplication.restoreOverrideCursor()
            except Exception as e:
                self.show_message(f"Nu s-a putut anula conexiunea anterioară: {str(e)}", "error")
                # Restaurăm cursorul normal în caz de eroare
                QApplication.restoreOverrideCursor()
        
        # Close any existing connection before trying to connect to a new one
        if hasattr(self, 'ftp_client') and self.ftp_client and self.ftp_client.is_connected:
            self.status_label.setText("Închidere conexiune existentă...")
            try:
                self.ftp_client.disconnect()
                # Wait briefly for threads to close
                import time
                time.sleep(0.5)
            except Exception as e:
                self.show_message(f"Eroare la închiderea conexiunii: {str(e)}", "error")
                # Restaurăm cursorul normal în caz de eroare
                QApplication.restoreOverrideCursor()
        
        # Add visual indicator that the application is working
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        self.show_message(f"Connecting to {host}:{port}...", "info")

        # Create a connection thread to avoid blocking the UI
        class ConnectionThread(QThread):
            connection_result = pyqtSignal(bool, str)
            
            def __init__(self, parent, ftp_client, host, port, username, password, key_file=None, key_passphrase=None):
                super().__init__(parent)
                self.ftp_client = ftp_client
                self.host = host
                self.port = port
                self.username = username
                self.password = password
                self.key_file = key_file
                self.key_passphrase = key_passphrase
                self.connection_type = getattr(parent, 'connection_type', 'ftp')
                # Adăugăm un flag pentru a verifica dacă thread-ul este anulat manual
                self.is_cancelled = False
                
            def run(self):
                try:
                    if self.is_cancelled:
                        self.connection_result.emit(False, "Connection cancelled by user")
                        return
                        
                    # Setăm un timeout pentru conexiune
                    import socket
                    old_timeout = socket.getdefaulttimeout()
                    socket.setdefaulttimeout(15)  # Timeout de 15 secunde pentru conectare
                    
                    try:
                        if self.connection_type == 'sftp' and self.key_file:
                            success = self.ftp_client.connect(
                                self.host,
                                self.port,
                                self.username,
                                self.password,
                                key_file=self.key_file,
                                key_passphrase=self.key_passphrase
                            )
                        else:
                            success = self.ftp_client.connect(self.host, self.port, self.username, self.password)
                        
                        if self.is_cancelled:
                            # Dacă s-a anulat între timp, ne deconectăm
                            if success and self.ftp_client.is_connected:
                                self.ftp_client.disconnect()
                            self.connection_result.emit(False, "Connection cancelled by user")
                        else:
                            self.connection_result.emit(success, "")
                    finally:
                        # Resetăm timeout-ul la valoarea inițială
                        socket.setdefaulttimeout(old_timeout)
                        
                except socket.timeout:
                    self.connection_result.emit(False, "Connection timed out. Check the address and port.")
                except Exception as e:
                    if not self.is_cancelled:
                        self.connection_result.emit(False, str(e))
                        
            def terminate(self):
                """Suprascriem metoda terminate pentru a seta flag-ul de anulare"""
                self.is_cancelled = True
                super().terminate()

        # Create and start the connection thread
        self.connection_thread = ConnectionThread(
            self, self.ftp_client, host, port, username, password, key_file, key_passphrase
        )
        
        # Connect the result signal
        self.connection_thread.connection_result.connect(self.handle_connection_result)
        
        # Adăugăm un timer pentru a verifica timeout-ul conexiunii (după 20 de secunde)
        connection_timeout = QTimer(self)
        connection_timeout.setSingleShot(True)
        connection_timeout.timeout.connect(self._connection_timeout)
        connection_timeout.start(20000)  # 20 secunde
        
        # Salvăm referința la timer pentru a-l putea opri când conexiunea este stabilită
        self.connection_timeout_timer = connection_timeout
        
        # Start the thread
        self.connection_thread.start()

        # Return True to indicate that the connection attempt has started
        return True
        
    def _connection_timeout(self):
        """Handler pentru timeout-ul conexiunii"""
        # Verificăm dacă încă există un thread de conectare
        if hasattr(self, 'connection_thread') and self.connection_thread and self.connection_thread.isRunning():
            # Oprim thread-ul
            try:
                self.connection_thread.terminate()
                self.connection_thread.wait(1000)
                
                # Resetăm cursorul
                QApplication.restoreOverrideCursor()
                
                # Afișăm mesajul
                self.status_label.setText("Connection timed out")
                self.show_message("Connection timed out. Check the address and port.", "error", auto_clear=False)
            except Exception as e:
                self.show_message(f"Error handling connection timeout: {str(e)}", "error")
                QApplication.restoreOverrideCursor()

    def handle_connection_result(self, success, error_message):
        """Handle the asynchronous connection result"""
        # Oprim timer-ul de timeout
        if hasattr(self, 'connection_timeout_timer') and self.connection_timeout_timer.isActive():
            self.connection_timeout_timer.stop()
            
        # Restore the normal cursor
        QApplication.restoreOverrideCursor()
        
        if success:
            # Update the status in the UI
            self.status_label.setText(f"Connected to {self.ftp_client.host}:{self.ftp_client.port}")
            
            # Stochează ID-ul conexiunii în obiectul client pentru utilizare ulterioară
            if hasattr(self, 'connection_id'):
                self.ftp_client.connection_id = self.connection_id
        else:
            self.status_label.setText("Connection error")
            if error_message:
                self.show_message(f"Connection error: {error_message}", "error", auto_clear=False)

    def disconnect(self):
        """Disconnect the FTP client and update the user interface"""
        # Asigură-te că cursorul este normal
        QApplication.restoreOverrideCursor()
        
        # Check if the FTP client exists and is connected before attempting to disconnect
        if self.ftp_client and self.ftp_client.is_connected:
            self.ftp_client.disconnect()

            # Directly update the buttons in the toolbar using the reference to FileManager
            if self.file_manager:
                self.file_manager.disconnect_btn.setEnabled(False)
                self.file_manager.connect_btn.setEnabled(True)
                self.file_manager.status_label.setText("Disconnected")

                # Use the dedicated method if it exists
                if hasattr(self.file_manager, 'update_connection_status'):
                    self.file_manager.update_connection_status(
                        False, "Disconnected")

            # Explicitly apply changes to the user interface
            self.on_disconnected()

    def on_connected(self, message):
        self.status_label.setText(message)
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.upload_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.create_dir_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.ftp_path_input.setEnabled(True)  # Enable the FTP path field
        self.back_btn.setEnabled(True)  # Enable the back navigation button
        
        # Update the buttons in the toolbar using the reference to FileManager
        if self.file_manager:
            # Enable the disconnect button directly from the toolbar
            self.file_manager.disconnect_btn.setEnabled(True)
            self.file_manager.connect_btn.setEnabled(False)
            self.file_manager.status_label.setText(message)
            
            # Use the dedicated method if it exists
            if hasattr(self.file_manager, 'update_connection_status'):
                self.file_manager.update_connection_status(True, message)
        
        # Check connection type and manage the current directory accordingly
        if hasattr(self, 'connection_type') and self.connection_type == 'sftp':
            # For SFTP, use the method from the SFTPClient class
            try:
                # Update current directory information
                if self.ftp_client.current_directory:
                    self.ftp_path_input.setText(self.ftp_client.current_directory)
                    self.status_label.setText(f"Connected to directory: {self.ftp_client.current_directory}")
                else:
                    self.ftp_path_input.setText(".")
                    self.status_label.setText("Connected, but could not determine directory")
                    
                # Try to list the current directory
                success = self.ftp_client.list_directory()
                if not success:
                    # If the first listing fails, try to check if the ftp directory exists
                    # (common on many Ubuntu servers)
                    try:
                        result = QMessageBox.question(
                            self,
                            "FTP Directory",
                            "Could not list the current directory. Would you like to check if an 'ftp' directory exists?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        
                        if result == QMessageBox.Yes:
                            # First try /home/{username}/ftp
                            success = self.ftp_client.change_directory("/home/ftpuser/ftp")
                            if not success:
                                # Then try just 'ftp'
                                success = self.ftp_client.change_directory("ftp") 
                                
                            if success:
                                self.ftp_path_input.setText(self.ftp_client.current_directory)
                                self.status_label.setText(f"Successfully navigated to: {self.ftp_client.current_directory}")
                            else:
                                # If still unsuccessful, try the input dialog
                                self.show_directory_input_dialog()
                        else:
                            # If the user refuses, show the standard dialog
                            self.show_directory_input_dialog()
                    except Exception as e:
                        self.status_label.setText(f"Navigation error: {str(e)}")
                        # Try the dialog anyway as a last option
                        self.show_directory_input_dialog()
            except Exception as e:
                self.status_label.setText(f"SFTP directory listing error: {str(e)}")
        else:
            # For FTP, continue with the existing method
            try:
                # Get the current directory from the server
                current_dir = self.ftp_client.ftp.pwd()
                self.ftp_client.current_directory = current_dir
                self.current_directory = current_dir  # Also update our property
                self.ftp_path_input.setText(
                    current_dir)  # Set the initial path
                self.status_label.setText(
                    f"Current directory listing: {current_dir}")

                # List the contents of the current directory
                self.ftp_client.list_directory()
            except Exception as e:
                self.status_label.setText(
                    f"FTP directory listing error: {str(e)}")

                # Try to use the standard method as a fallback
                try:
                    self.ftp_client.list_directory()
                except Exception as e2:
                    self.status_label.setText(
                        f"Directory listing error: {str(e2)}")

    def on_disconnected(self):
        self.status_label.setText("Disconnected")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.create_dir_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.file_list.clear()
        # Disable the FTP path field
        self.ftp_path_input.setEnabled(False)
        self.ftp_path_input.clear()  # Clear the FTP path field
        self.back_btn.setEnabled(False)  # Disable the back navigation button
        self.current_directory = "/"  # Reset to root directory

        # Update the buttons in the toolbar using the reference to FileManager
        if self.file_manager:
            self.file_manager.disconnect_btn.setEnabled(False)
            self.file_manager.connect_btn.setEnabled(True)
            self.file_manager.status_label.setText("Disconnected")

    def on_error(self, error_message):
        self.status_label.setText(f"Error: {error_message}")
        # Use the message area instead of QMessageBox
        self.show_message(f"Error: {error_message}", "error", auto_clear=False)

    def display_directory_contents(self, items):
        self.file_list.clear()

        # Add option for back navigation
        if self.ftp_client.current_directory != "/":
            back_item = QListWidgetItem("..")
            back_item.setData(
                Qt.UserRole, {"name": "..", "type": "parent_dir", "modified": "", "size": 0})
            self.file_list.addItem(back_item)

        # Check connection type
        if hasattr(self, 'connection_type') and self.connection_type == 'sftp':
            # Print information for debugging
            # dir_count = sum(1 for item in items if item["type"] == "dir")
            # file_count = sum(1 for item in items if item["type"] == "file")
            # print(
            #     f"FTPPanel.display_directory_contents: Displaying {len(items)} SFTP items: {dir_count} directories, {file_count} files")

            # For SFTP, handle directory and file display specially
            # Add directories first
            for item in items:
                if item["type"] == "dir":
                    list_item = QListWidgetItem(f"📁 {item['name']}")

                    # Ensure all items have the 'modified' field
                    if "modified" not in item:
                        item["modified"] = ""

                    list_item.setData(Qt.UserRole, item)
                    self.file_list.addItem(list_item)
                    # print(
                    #     f"FTPPanel.display_directory_contents: Added SFTP directory: {item['name']}")

            # Then add files
            for item in items:
                if item["type"] == "file":
                    try:
                        size_text = item.get("size", "0")
                        list_item = QListWidgetItem(
                            f"📄 {item['name']} ({size_text} bytes)")
                    except:
                        list_item = QListWidgetItem(f"📄 {item['name']}")

                    # Ensure all items have the 'modified' field
                    if "modified" not in item:
                        item["modified"] = ""

                    list_item.setData(Qt.UserRole, item)
                    self.file_list.addItem(list_item)
        else:
            # For standard FTP
            # Check if we are in the root directory (where drives are displayed)
            if self.ftp_client.current_directory == "/":
                # For root, handle drive display specially
                for item in items:
                    # Check if the item is a single letter (drive)
                    if len(item["name"]) == 1 and item["name"].isalpha():
                        # Create an item for the drive
                        list_item = QListWidgetItem(f"💿 Drive {item['name']}:")
                        # Set type to directory to allow navigation
                        item_data = {
                            "name": item["name"], "type": "directory", "modified": "", "size": 0}
                        list_item.setData(Qt.UserRole, item_data)
                        self.file_list.addItem(list_item)
                    else:
                        # For other items
                        if item["type"] == "directory":
                            list_item = QListWidgetItem(f"📁 {item['name']}")
                        else:
                            try:
                                size_text = item.get("size", "0")
                                list_item = QListWidgetItem(
                                    f"📄 {item['name']} ({size_text} bytes)")
                            except:
                                list_item = QListWidgetItem(
                                    f"📄 {item['name']}")

                        # Ensure all items have the 'modified' field
                        if "modified" not in item:
                            item["modified"] = ""

                        list_item.setData(Qt.UserRole, item)
                        self.file_list.addItem(list_item)
            else:
                # For regular directories, display directories first
                for item in items:
                    if item["type"] == "directory":
                        list_item = QListWidgetItem(f"📁 {item['name']}")

                        # Ensure all items have the 'modified' field
                        if "modified" not in item:
                            item["modified"] = ""

                        list_item.setData(Qt.UserRole, item)
                        self.file_list.addItem(list_item)

                # Then add files
                for item in items:
                    if item["type"] == "file":
                        try:
                            size_text = item.get("size", "0")
                            list_item = QListWidgetItem(
                                f"📄 {item['name']} ({size_text} bytes)")
                        except:
                            list_item = QListWidgetItem(f"📄 {item['name']}")

                        # Ensure all items have the 'modified' field
                        if "modified" not in item:
                            item["modified"] = ""

                        list_item.setData(Qt.UserRole, item)
                        self.file_list.addItem(list_item)

    def reset_click_protection(self):
        """Reset protection against multiple clicks"""
        self.double_click_protection = False

    def item_double_clicked(self, item):
        # Check if protection is active
        if self.double_click_protection:
            return
        
        # Activate protection
        self.double_click_protection = True
        
        # Start timer for unlocking after 1 second
        self.click_timer.start(300)
        
        # Check if item or item_data is None
        if item is None:
            self.double_click_protection = False  # Reset protection in case of error
            return
        
        try:
            item_data = item.data(Qt.UserRole)
            if item_data is None:
                self.double_click_protection = False  # Reset protection in case of error
                return
            
            
            # First check if it is a back navigation item
            if item_data.get("name") == ".." and (item_data.get("type") == "parent_dir" or item_data.get("type") == "directory"):
                # Common back navigation for both connection types
                self.navigate_back()
                return
            
            # Check connection type
            if hasattr(self, 'connection_type') and self.connection_type == 'sftp':
                # For SFTP, check if it is a directory
                if item_data.get("type") == "dir":
                    try:
                        # Direct navigation using only the directory name
                        dir_name = item_data.get("name", "")
                        if not dir_name:
                            self.status_label.setText("Error: directory name is missing")
                            return
                        
                        self.status_label.setText(f"Navigating to {dir_name}...")
                        
                        # Use the directory name directly
                        success = self.ftp_client.change_directory(dir_name)
                        
                        if success:
                            # Update path field
                            if self.ftp_client.current_directory:
                                self.ftp_path_input.setText(self.ftp_client.current_directory)
                                self.status_label.setText(f"Successfully navigated to: {self.ftp_client.current_directory}")
                            else:
                                # In case current_directory is None after navigate
                                self.ftp_path_input.setText(dir_name)
                                self.status_label.setText(f"Successfully navigated to: {dir_name}")
                        else:
                            self.status_label.setText(f"Failed to navigate to: {dir_name}")
                    except Exception as e:
                        self.status_label.setText(f"Navigation error: {str(e)}")
                else:
                    # Download the selected file
                    self.download_file()
            else:
                # Code for standard FTP - use a simpler and more robust approach
                if item_data.get("type") == "directory":
                    try:
                        # Navigate to the selected directory
                        dir_name = item_data.get("name", "")
                        if not dir_name:
                            self.status_label.setText("Error: directory name is missing")
                            return
                        
                        self.status_label.setText(f"Navigating to {dir_name}...")
                        
                        # Save the current directory to be able to return in case of error
                        old_dir = self.ftp_client.current_directory if self.ftp_client.current_directory else "/"
                        
                        try:
                            # Try to navigate to the selected directory
                            self.ftp_client.ftp.cwd(dir_name)
                            
                            # Update the current path
                            try:
                                self.ftp_client.current_directory = self.ftp_client.ftp.pwd()
                            except:
                                # If we cannot get the path, construct a relative one
                                if old_dir.endswith('/'):
                                    self.ftp_client.current_directory = old_dir + dir_name
                                else:
                                    self.ftp_client.current_directory = old_dir + '/' + dir_name
                            
                            # List contents
                            self.status_label.setText(f"Directory: {dir_name}")
                            self.ftp_client.list_directory()
                            
                            # Update path field
                            self.update_ftp_path_display()
                            
                        except Exception as e:
                            self.status_label.setText(f"Navigation error: {str(e)}")
                            
                            # Try to return to the previous directory
                            try:
                                self.ftp_client.ftp.cwd(old_dir)
                                self.ftp_client.current_directory = old_dir
                                self.update_ftp_path_display()
                            except:
                                # If that doesn't work either, try to navigate to root
                                try:
                                    self.ftp_client.ftp.cwd("/")
                                    self.ftp_client.current_directory = "/"
                                    self.update_ftp_path_display()
                                    self.ftp_client.list_directory()
                                except:
                                    pass
                    except Exception as e:
                        self.status_label.setText(f"Severe error: {str(e)}")
                else:
                    # Download the selected file
                    self.download_file()
        except Exception as e:
            # Capture all errors to prevent application crash
            self.status_label.setText(f"Error: {str(e)}")
            self.show_message(f"An unexpected error occurred: {str(e)}", "error", auto_clear=False)
            
            # Reset protection
            self.double_click_protection = False
            
            # Try to refresh the list to stay in the current directory
            try:
                self.ftp_client.list_directory()
            except:
                pass

    def navigate_back(self):
        """Common method for navigating back for both connection types"""
        # Check if protection is active, but continue anyway
        # This is a modification to allow better behavior
        # if self.double_click_protection:
        #     print("FTPPanel.navigate_back: Navigation with active protection, but continuing")
        
        # Activate protection
        self.double_click_protection = True
        
        # Start timer for unlocking after 300 ms (instead of 1 second)
        # to make navigation more responsive
        self.click_timer.start(300)
        
        try:
            self.status_label.setText("Navigating back...")
            
            if hasattr(self, 'connection_type') and self.connection_type == 'sftp':
                # For SFTP, use our method
                success = self.ftp_client.change_directory("..")
                
                if success:
                    # Update path field
                    if self.ftp_client.current_directory:
                        self.ftp_path_input.setText(self.ftp_client.current_directory)
                        self.status_label.setText(f"Successfully navigated to: {self.ftp_client.current_directory}")
                else:
                    self.status_label.setText("Error navigating back")
            else:
                # For standard FTP
                # Save the current directory to be able to return in case of error
                old_dir = self.ftp_client.current_directory if self.ftp_client.current_directory else "/"
                
                try:
                    # Try to navigate back
                    self.ftp_client.ftp.cwd("..")
                    
                    # Update the current path
                    try:
                        self.ftp_client.current_directory = self.ftp_client.ftp.pwd()
                    except:
                        # If we cannot get the path, assume we are at root
                        self.ftp_client.current_directory = "/"
                    
                    # List contents
                    try:
                        self.ftp_client.list_directory()
                        self.status_label.setText(f"Parent directory: {self.ftp_client.current_directory}")
                    except:
                        self.status_label.setText("Error listing parent directory")
                    
                    # Update path field
                    self.update_ftp_path_display()
                    
                except Exception as e:
                    self.status_label.setText(f"Error navigating back: {str(e)}")
                    
                    # Try to return to the previous directory
                    try:
                        self.ftp_client.ftp.cwd(old_dir)
                        self.ftp_client.current_directory = old_dir
                        self.update_ftp_path_display()
                        self.ftp_client.list_directory()
                    except:
                        # If that doesn't work either, try to navigate to root
                        try:
                            self.ftp_client.ftp.cwd("/")
                            self.ftp_client.current_directory = "/"
                            self.update_ftp_path_display()
                            self.ftp_client.list_directory()
                        except:
                            pass
        except Exception as e:
            # Capture all errors to prevent application crash
            self.status_label.setText(f"Error navigating back: {str(e)}")
            
            # Reset protection in case of error
            self.double_click_protection = False
            
            # Try to refresh the list to stay in the current directory
            try:
                self.ftp_client.list_directory()
            except:
                pass

    def update_ftp_path_display(self):
        """Update the FTP path display in Windows format"""
        path = self.ftp_client.current_directory

        # Convert the path from FTP format (/C/...) to Windows format (C:/...)
        if path.startswith('/') and len(path) > 1:
            # Check if the second character is a drive letter
            if path[1].isalpha() and (len(path) == 2 or path[2] == '/'):
                # Extract the drive letter
                drive_letter = path[1]
                # Convert the format
                if len(path) > 2:
                    windows_path = f"{drive_letter}:{path[2:]}"
                else:
                    windows_path = f"{drive_letter}:/"

                self.ftp_path_input.setText(windows_path)
                return

        # If it is not a special path, display the original path
        self.ftp_path_input.setText(path)

    def upload_file(self):
        """Handler for uploading a file"""
        if not self.ftp_client or not self.ftp_client.is_connected:
            self.show_message("You are not connected to an FTP server", "warning")
            return

        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select file to upload", "", "All files (*)"
            )

            if file_path:
                file_name = os.path.basename(file_path)
                self.status_label.setText(f"Uploading {file_name}...")
                self.show_message(f"Uploading file {file_name}...", "info")

                # Check connection type
                if hasattr(self, 'connection_type') and self.connection_type == 'sftp':
                    # For SFTP, construct the full path
                    remote_path = self.ftp_client.current_directory
                    if not remote_path.endswith('/'):
                        remote_path += '/'
                    remote_path += file_name
                    
                    # Try uploading with correct SFTP parameters
                    try:
                        self.ftp_client.upload_file(file_path, remote_path)
                        # Wait for the upload to finish (handled by the file_uploaded signal)
                    except Exception as e:
                        self.status_label.setText(f"File upload error: {str(e)}")
                        self.show_message(f"Could not upload file: {str(e)}", "error")
                else:
                    # For FTP, use the existing method
                    success = self.ftp_client.upload_file(file_path)
                    if not success:
                        self.status_label.setText(f"File upload error")
                        self.show_message("Could not upload file", "error")

        except Exception as e:
            self.show_message(f"Could not start upload: {str(e)}", "error")

    def download_file(self):
        """Handler for downloading a file"""
        if not self.ftp_client or not self.ftp_client.is_connected:
            self.show_message("You are not connected to an FTP server", "warning")
            return

        current_item = self.file_list.currentItem()
        if not current_item:
            self.show_message("Select a file to download", "warning")
            return

        item_data = current_item.data(Qt.UserRole)
        if hasattr(self, 'connection_type') and self.connection_type == 'sftp':
            # For SFTP
            if item_data["type"] == "dir":
                self.show_message("You can only download files, not directories", "warning")
                return

            try:
                # Construct the full path on the server
                remote_path = self.ftp_client.current_directory
                if not remote_path.endswith('/'):
                    remote_path += '/'
                remote_path += item_data["name"]

                # File save dialog
                save_path, _ = QFileDialog.getSaveFileName(
                    self, "Save file", item_data["name"], "All files (*)"
                )

                if save_path:
                    self.status_label.setText(f"Downloading {item_data['name']}...")
                    self.show_message(f"Downloading file {item_data['name']}...", "info")
                    self.ftp_client.download_file(remote_path, save_path)
            except Exception as e:
                self.show_message(f"Could not start download: {str(e)}", "error")
        else:
            # For FTP
            if not item_data["type"] == "file":
                self.show_message("You can only download files, not directories", "warning")
                return

            try:
                save_path, _ = QFileDialog.getSaveFileName(
                    self, "Save file", os.path.expanduser(
                        f"~/{item_data['name']}")
                )

                if save_path:
                    self.status_label.setText(f"Downloading {item_data['name']}...")
                    self.show_message(f"Downloading file {item_data['name']}...", "info")
                    self.ftp_client.download_file(item_data["name"], save_path)
            except Exception as e:
                self.show_message(f"Could not start download: {str(e)}", "error")

    def create_directory(self):
        if not self.ftp_client.is_connected:
            self.show_message("You are not connected to an FTP server", "warning")
            return

        dir_name, ok = QInputDialog.getText(
            self, "Create Directory", "Directory name:"
        )

        if ok and dir_name:
            success = self.ftp_client.create_directory(dir_name)
            if success:
                self.ftp_client.list_directory()  # Update the list
                self.show_message(f"Directory '{dir_name}' was created successfully", "success")
            else:
                self.show_message(f"Could not create directory '{dir_name}'", "error")

    def delete_item(self):
        if not self.ftp_client.is_connected:
            return

        current_item = self.file_list.currentItem()
        if not current_item:
            return

        item_data = current_item.data(Qt.UserRole)
        if item_data["name"] == "..":
            return

        confirm = QMessageBox.question(
            self, "Delete confirmation",
            f"Are you sure you want to delete '{item_data['name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            success = False
            if item_data["type"] == "file":
                success = self.ftp_client.delete_file(item_data["name"])
            else:
                success = self.ftp_client.delete_directory(item_data["name"])

            if success:
                self.ftp_client.list_directory()  # Update the list

    def show_context_menu(self, position):
        current_item = self.file_list.currentItem()
        if not current_item:
            return

        item_data = current_item.data(Qt.UserRole)

        menu = QMenu()

        if item_data["type"] == "directory" and item_data["name"] != "..":
            open_dir_action = QAction("Open", self)
            open_dir_action.triggered.connect(
                lambda: self.item_double_clicked(current_item))
            menu.addAction(open_dir_action)

        if item_data["type"] == "file":
            download_action = QAction("Download", self)
            download_action.triggered.connect(self.download_file)
            menu.addAction(download_action)

            # Add action for copying to local system
            copy_to_local_action = QAction("Copy to Local", self)
            # Connect the action to the appropriate method
            if self.file_manager:
                copy_to_local_action.triggered.connect(
                    lambda: self.file_manager.copy_from_ftp_to_local()
                )
            else:
                # Alternatively, try through parent()
                copy_to_local_action.triggered.connect(
                    lambda: self.parent().copy_from_ftp_to_local() if hasattr(
                        self.parent(), 'copy_from_ftp_to_local') else None
                )
            menu.addAction(copy_to_local_action)

        if item_data["name"] != "..":
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(self.delete_item)
            menu.addAction(delete_action)

        menu.exec_(self.file_list.mapToGlobal(position))

    def on_file_downloaded(self, local_path):
        """Callback for when a file has been successfully downloaded"""
        try:
            # Get file information
            filename = os.path.basename(local_path)
            filesize = os.path.getsize(local_path) if os.path.exists(local_path) else 0
            
            # Format size
            if filesize < 1024:
                size_text = f"{filesize} bytes"
            elif filesize < 1024 * 1024:
                size_text = f"{filesize // 1024} KB"
            else:
                size_text = f"{filesize // (1024 * 1024)} MB"
                
            # Display successful download message
            self.show_message(
                f"File {filename} ({size_text}) was successfully downloaded to: {local_path}", 
                "success"
            )
        except Exception as e:
            # In case of error, use the simple message
            self.show_message(f"File was successfully downloaded to: {local_path}", "success")

    def on_file_uploaded(self, local_file):
        """Callback for when a file has been successfully uploaded"""
        try:
            # Get file information
            filename = os.path.basename(local_file)
            filesize = os.path.getsize(local_file) if os.path.exists(local_file) else 0
            
            # Format size
            if filesize < 1024:
                size_text = f"{filesize} bytes"
            elif filesize < 1024 * 1024:
                size_text = f"{filesize // 1024} KB"
            else:
                size_text = f"{filesize // (1024 * 1024)} MB"
                
            # Construct the full remote path
            remote_path = ""
            if hasattr(self, 'ftp_client') and hasattr(self.ftp_client, 'current_directory'):
                remote_path = self.ftp_client.current_directory
                if not remote_path.endswith('/'):
                    remote_path += '/'
                remote_path += filename
                
            # Display successful upload message
            self.show_message(
                f"File {filename} ({size_text}) was successfully uploaded to {remote_path}", 
                "success"
            )
        except Exception as e:
            # In case of error, use the simple message
            self.show_message(f"File {os.path.basename(local_file)} was successfully uploaded", "success")

    # Helper methods for access by the parent class
    def get_selected_item_data(self):
        """Return the data of the selected item or None if no selection exists"""
        current_item = self.file_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None

    def get_current_directory(self):
        """Return the current directory in FTP"""
        if hasattr(self, 'ftp_client') and self.ftp_client and self.ftp_client.is_connected:
            # Return the local value, which should be synchronized with ftp_client.current_directory
            return self.current_directory
        return None

    def is_connected(self):
        """Check if the FTP client is connected"""
        return self.ftp_client.is_connected

    def navigate_to_ftp_path(self):
        """Navigate to the path entered in the FTP path field"""
        # Check if protection is active
        if self.double_click_protection:
            self.show_message("Navigation ignored: operation in progress", "warning")
            return
        
        # Activate protection
        self.double_click_protection = True
        
        # Start timer for unlocking after 500 ms
        self.click_timer.start(300)
        
        if not self.ftp_client or not self.ftp_client.is_connected:
            self.show_message("You are not connected to a server", "warning")
            self.double_click_protection = False  # Reset protection in case of error
            return

        path = self.ftp_path_input.text().strip()
        if not path:
            self.show_message("Enter a path for navigation", "warning")
            self.double_click_protection = False  # Reset protection in case of error
            return
        
        self.show_message(f"Navigating to {path}...", "info")

        # Check connection type
        if hasattr(self, 'connection_type') and self.connection_type == 'sftp':
            # For SFTP, use the method from the SFTPClient class
            try:
                self.status_label.setText(f"Attempting to navigate to {path}...")
                
                # For SFTP, navigate directly with the entered path
                success = self.ftp_client.change_directory(path)

                if success:
                    # Update the current path in the interface
                    self.ftp_path_input.setText(self.ftp_client.current_directory)
                    self.status_label.setText(f"Successfully navigated to: {self.ftp_client.current_directory}")
                    self.show_message(f"Successfully navigated to {self.ftp_client.current_directory}", "success")

                    # Check if the listing was successful but do not continue to display errors
                    # if we managed to navigate
                    self.ftp_client.list_directory()
                else:
                    # Restore the previous path in the interface
                    if self.ftp_client.current_directory:
                        self.ftp_path_input.setText(self.ftp_client.current_directory)
                        
                    # Try to see if the path is relative
                    if not path.startswith('/') and self.ftp_client.current_directory:
                        alt_path = self.ftp_client.current_directory
                        if not alt_path.endswith('/'):
                            alt_path += '/'
                        alt_path += path
                        
                        success = self.ftp_client.change_directory(alt_path)
                        
                        if success:
                            self.ftp_path_input.setText(self.ftp_client.current_directory)
                            self.status_label.setText(f"Successfully navigated to: {self.ftp_client.current_directory}")
                            self.show_message(f"Successfully navigated to {self.ftp_client.current_directory}", "success")
                            return
                    
                    self.status_label.setText(f"Navigation error: Could not access {path}")
                    self.show_message(f"Could not navigate to path: {path}", "error")
            except Exception as e:
                # Display the error and restore the previous path
                if self.ftp_client.current_directory:
                    self.ftp_path_input.setText(self.ftp_client.current_directory)

                self.status_label.setText(f"Navigation error: {str(e)}")
                self.show_message(f"Navigation error: {str(e)}", "error")
        else:
            # For FTP, use the existing method
            # Use the navigate_to_ftp_path method from ftp_client
            if self.ftp_client.navigate_to_ftp_path(path):
                # If navigation was successful, update the current directory and contents
                self.current_directory = self.ftp_client.current_directory
                self.ftp_path_input.setText(self.current_directory)
                self.refresh_ftp_files()
                self.show_message(f"Successfully navigated to {self.ftp_client.current_directory}", "success")
            else:
                # If navigation failed, display an error message
                self.show_message(f"Could not navigate to path: {path}", "error")
                # Reset the field to the current directory
                self.ftp_path_input.setText(self.current_directory)

    def change_directory(self, dir_name):
        """Change the current directory using the FTP client"""
        try:
            # Check connection type
            if hasattr(self, 'connection_type') and self.connection_type == 'sftp':
                # For SFTP, use the specific method
                result = self.ftp_client.change_directory(dir_name)
            else:
                # For standard FTP, use the navigate_to_ftp_path method
                result = self.ftp_client.navigate_to_ftp_path(dir_name)

            if result:
                # Update the interface and file list
                self.current_directory = self.ftp_client.current_directory
                self.ftp_path_input.setText(self.current_directory)
                self.refresh_ftp_files()
                return True
            return False
        except Exception as e:
            self.show_message(f"Could not navigate to path: {dir_name}", "error")
            return False

    def refresh_ftp_files(self):
        """Update the FTP file list for the current directory"""
        if not self.ftp_client or not self.ftp_client.is_connected:
            self.status_label.setText("You are not connected to an FTP server")
            self.show_message("You are not connected to an FTP server", "warning")
            return False

        try:
            # Save the current directory to be able to restore it in case of error
            try:
                current_dir = self.ftp_client.ftp.pwd()
            except:
                current_dir = "/"

            # Handle the possible error message "250 ... is the current directory"
            # which is not actually an error, but a success message
            try:
                result = self.ftp_client.list_directory()

                # Check if the list is empty, which may indicate an error
                if not result and self.ftp_client.current_directory != "/":
                    # Try again by explicitly navigating
                    self.ftp_client.ftp.cwd(current_dir)
                    result = self.ftp_client.list_directory()

                self.status_label.setText(
                    f"Directory has been updated: {self.ftp_client.current_directory}")
                return True
            except Exception as e:
                error_str = str(e)

                # Check if the error is actually a success message
                if "250" in error_str and "current directory" in error_str:
                    # Try again without generating an error
                    try:
                        result = self.ftp_client.list_directory()
                        self.status_label.setText(
                            f"Directory has been updated: {self.ftp_client.current_directory}")
                        return True
                    except Exception as inner_e:
                        error_str = str(inner_e)

                self.status_label.setText(
                    f"Error updating list: {error_str}")

                # Try to restore the current directory and list again
                try:
                    self.ftp_client.ftp.cwd(current_dir)
                    self.ftp_client.current_directory = current_dir
                    result = self.ftp_client.list_directory()
                    return True
                except:
                    self.show_message(f"Could not update file list: {error_str}", "error")
                    return False
        except Exception as e:
            self.status_label.setText(
                f"Error updating list: {str(e)}")
            self.show_message(f"Could not update file list: {str(e)}", "error")
            return False

    # Methods for integration with FileManager
    def upload_from_path(self, local_path):
        """Allow the main panel to upload a file directly"""
        if not self.ftp_client.is_connected:
            self.show_message("Please connect to an FTP server first", "warning")
            return False

        if not os.path.exists(local_path):
            self.show_message(f"File {local_path} does not exist", "error")
            return False

        if not os.path.isfile(local_path):
            self.show_message(f"{local_path} is a directory, not a file. You can only copy files.", "warning")
            return False

        # Check if the file can be accessed
        try:
            with open(local_path, 'rb') as test_file:
                # Just test if the file can be opened
                pass
        except PermissionError:
            self.show_message(f"You do not have permission to read the file {local_path}", "error")
            return False
        except Exception as e:
            self.show_message(f"Could not access file: {str(e)}", "error")
            return False

        # Get the file name for upload
        remote_filename = os.path.basename(local_path)
        
        # Construct the full path for destination in the case of SFTP
        # For standard FTP it is not necessary
        current_dir = ""
        if hasattr(self.ftp_client, 'current_directory') and self.ftp_client.current_directory:
            current_dir = self.ftp_client.current_directory
            # Ensure there is a separator at the end
            if not current_dir.endswith('/'):
                current_dir += '/'
        
        # Check if the file already exists on the server
        try:
            file_exists = False
            
            # For SFTP
            if hasattr(self, 'connection_type') and self.connection_type == 'sftp':
                self.status_label.setText(f"Checking existence of file {remote_filename}...")
                # Get the current file list
                file_list = self.ftp_client.list_directory(show_output=False)
                file_exists = any(item['name'] == remote_filename and item['type'] == 'file' for item in file_list)
                self.status_label.setText(f"Check complete: {'File exists' if file_exists else 'File does not exist'}")
            else:
                # For standard FTP, check if the file exists
                self.status_label.setText(f"Checking existence of file {remote_filename}...")
                try:
                    # Try to get file details to check existence
                    self.ftp_client.ftp.size(remote_filename)
                    file_exists = True
                    self.status_label.setText(f"Check complete: File exists")
                except:
                    file_exists = False
                    self.status_label.setText(f"Check complete: File does not exist")
                    
            if file_exists:
                # Ask the user if they want to replace the file
                confirm = QMessageBox.question(
                    self, "Replace confirmation",
                    f"File {remote_filename} already exists in {current_dir}. Do you want to replace it?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if confirm == QMessageBox.No:
                    self.show_message(f"Copy operation was canceled", "info")
                    return False
        except Exception as e:
            # Display the error, but continue with the upload
            self.status_label.setText(f"Warning: Could not check file existence: {str(e)}")
            self.show_message(f"Warning: Could not check file existence: {str(e)}", "warning")
        
        # Display progress message
        self.status_label.setText(f"Copying {os.path.basename(local_path)} to directory {current_dir}...")
        self.show_message(f"Copying {os.path.basename(local_path)} to directory {current_dir}...", "info")

        # Register a handler for the error signal to capture the specific message
        # Use a list to be able to modify the value in the callback
        last_error_message = [""]

        def on_error(message):
            last_error_message[0] = message

        # Temporarily connect to the error signal
        error_connection = self.ftp_client.error.connect(on_error)

        # Check the client type and call the appropriate method
        try:
            success = False
            
            # Check if it is an SFTP or standard FTP client
            if hasattr(self, 'connection_type') and self.connection_type == 'sftp':
                # For SFTP, we need to specify the full path on the server
                remote_path = current_dir + remote_filename
                self.ftp_client.upload_file(local_path, remote_path)
                success = True
            else:
                # For standard FTP, use the existing method that only requires the local path
                # FTPClient.upload_file manages the destination using the current directory
                success = self.ftp_client.upload_file(local_path)
        except Exception as e:
            success = False
            last_error_message[0] = str(e)

        # Disconnect the temporary handler
        self.ftp_client.error.disconnect(error_connection)

        if success:
            # Update the list to display the newly uploaded file
            QTimer.singleShot(500, lambda: self.ftp_client.list_directory())
            
            self.show_message(f"File {os.path.basename(local_path)} was successfully copied", "success")
            return True
        else:
            # Use the specific error message if it exists
            error_msg = last_error_message[0] if last_error_message[0] else "Could not copy file to FTP"
            
            self.show_message(error_msg, "error")
            return False

    def download_to_directory(self, local_dir):
        """Allow the main panel to download a file directly to a local directory"""
        if not self.ftp_client.is_connected:
            self.show_message("Please connect to an FTP server first", "warning")
            return False

        item_data = self.get_selected_item_data()
        if not item_data:
            self.show_message("Select a file from FTP to copy", "warning")
            return False

        if (item_data["type"] != "file" and 
            item_data.get("type") != "file" and 
            not (hasattr(self, 'connection_type') and self.connection_type == 'sftp' and item_data.get("type") == "file")):
            self.show_message("You can only copy files (not directories)", "warning")
            return False

        # Check and prepare the destination directory
        if not local_dir or not os.path.exists(local_dir) or not os.path.isdir(local_dir):
            # Use Home if we do not have a valid directory
            local_dir = os.path.expanduser("~")

        # Construct the full path for the local file
        local_path = os.path.join(local_dir, item_data["name"])
        
        # Check if the file already exists
        if os.path.exists(local_path):
            confirm = QMessageBox.question(
                self, "Replace confirmation",
                f"File {item_data['name']} already exists in {local_dir}. Do you want to replace it?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm == QMessageBox.No:
                self.show_message(f"Copy operation was canceled", "info")
                return False

        # Display a progress message
        self.show_message(f"Downloading file {item_data['name']} to {local_dir}...", "info")
        
        # Check connection type and handle SFTP specially
        if hasattr(self, 'connection_type') and self.connection_type == 'sftp':
            try:
                # For SFTP, construct the full path
                remote_path = self.ftp_client.current_directory
                if not remote_path.endswith('/'):
                    remote_path += '/'
                remote_path += item_data["name"]
                
                # Try downloading
                success = self.ftp_client.download_file(remote_path, local_path)
                
                # Check if the file exists on disk to confirm success
                if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                    self.show_message(f"File was successfully copied to {local_path}", "success")
                    return True
                elif not success:
                    self.show_message(f"Could not download file from SFTP", "error")
                    return False
                else:
                    # Wait a bit and check the file again
                    from time import sleep
                    sleep(0.5)
                    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                        self.show_message(f"File was successfully copied to {local_path}", "success")
                        return True
                    else:
                        self.show_message(f"Download result is unclear, check the file: {local_path}", "warning")
                        return True
            except Exception as e:
                self.show_message(f"Download error: {str(e)}", "error")
                return False
        else:
            # For standard FTP
            success = self.ftp_client.download_file(item_data["name"], local_path)
            
            if success:
                self.show_message(f"File was successfully copied to {local_path}", "success")
                return True
            else:
                self.show_message(f"Could not copy file from FTP", "error")
                return False

    def hide_connection_buttons(self):
        """Hide the connect and disconnect buttons from the panel"""
        if hasattr(self, 'connect_btn'):
            self.connect_btn.setVisible(False)
        if hasattr(self, 'disconnect_btn'):
            self.disconnect_btn.setVisible(False)
        # We can also hide the status label, as it will be displayed in the toolbar
        if hasattr(self, 'status_label'):
            self.status_label.setVisible(False)

    def show_directory_input_dialog(self):
        """Display a dialog to ask the user to enter a specific directory."""
        from PyQt5.QtWidgets import QInputDialog
        directory, ok = QInputDialog.getText(
            self, 
            "Enter a directory", 
            "Could not list the current directory. Enter a directory to try accessing:",
            text="/home/ftpuser/ftp"
        )
        if ok and directory:
            try:
                success = self.ftp_client.change_directory(directory)
                if success:
                    # The directory was updated in the change_directory method
                    self.ftp_path_input.setText(self.ftp_client.current_directory)
                    self.status_label.setText(f"Successfully navigated to: {self.ftp_client.current_directory}")
                else:
                    self.status_label.setText(f"Navigation error: Could not access {directory}")
            except Exception as e:
                self.status_label.setText(f"Navigation error: {str(e)}")

    def navigate_back_directly(self):
        """Method for navigating back using the dedicated button, which ignores double-click protection"""
        # This method does not use protection against multiple clicks
        # because it is called from a dedicated button
        
        try:
            self.status_label.setText("Navigating back...")
            
            if hasattr(self, 'connection_type') and self.connection_type == 'sftp':
                # For SFTP, use our method
                success = self.ftp_client.change_directory("..")
                
                if success:
                    # Update path field
                    if self.ftp_client.current_directory:
                        self.ftp_path_input.setText(self.ftp_client.current_directory)
                        self.status_label.setText(f"Successfully navigated to: {self.ftp_client.current_directory}")
                else:
                    self.status_label.setText("Error navigating back")
            else:
                # For standard FTP
                # Save the current directory to be able to return in case of error
                old_dir = self.ftp_client.current_directory if self.ftp_client.current_directory else "/"
                
                try:
                    # Try to navigate back
                    self.ftp_client.ftp.cwd("..")
                    
                    # Update the current path
                    try:
                        self.ftp_client.current_directory = self.ftp_client.ftp.pwd()
                    except:
                        # If we cannot get the path, assume we are at root
                        self.ftp_client.current_directory = "/"
                    
                    # List contents
                    try:
                        self.ftp_client.list_directory()
                        self.status_label.setText(f"Parent directory: {self.ftp_client.current_directory}")
                    except:
                        self.status_label.setText("Error listing parent directory")
                    
                    # Update path field
                    self.update_ftp_path_display()
                    
                except Exception as e:
                    self.status_label.setText(f"Error navigating back: {str(e)}")
                    
                    # Try to return to the previous directory
                    try:
                        self.ftp_client.ftp.cwd(old_dir)
                        self.ftp_client.current_directory = old_dir
                        self.update_ftp_path_display()
                        self.ftp_client.list_directory()
                    except:
                        # If that doesn't work either, try to navigate to root
                        try:
                            self.ftp_client.ftp.cwd("/")
                            self.ftp_client.current_directory = "/"
                            self.update_ftp_path_display()
                            self.ftp_client.list_directory()
                        except:
                            pass
        except Exception as e:
            # Capture all errors to prevent application crash
            self.status_label.setText(f"Error navigating back: {str(e)}")
            
            # Try to refresh the list to stay in the current directory
            try:
                self.ftp_client.list_directory()
            except:
                pass

    def show_message(self, message, message_type="info", auto_clear=True, timeout=5000):
        """Afișează un mesaj în zona de log și actualizează tabelele de transfer
        
        Args:
            message (str): Mesajul de afișat
            message_type (str): Tipul mesajului (info, success, error, warning)
            auto_clear (bool): Dacă mesajul trebuie șters automat după un anumit timp
            timeout (int): Timpul în milisecunde după care mesajul va fi șters automat
        """
        # Înregistrează mesajul în fișierele de log FTP
        if hasattr(self, 'ftp_client') and self.ftp_client:
            if hasattr(self.ftp_client, 'logger') and self.ftp_client.logger:
                prefix = ""
                if message_type == "error":
                    prefix = "ERROR: "
                elif message_type == "warning":
                    prefix = "WARNING: "
                elif message_type == "success":
                    prefix = "SUCCESS: "
                self.ftp_client.logger.log(f"{prefix}{message}")
                
        # Transmite mesajul către FileManager pentru actualizarea tabelelor de transfer
        if hasattr(self, 'file_manager') and self.file_manager and hasattr(self.file_manager, 'show_message'):
            self.file_manager.show_message(message, message_type, auto_clear, timeout)
        
        # Afișează mesajul și în eticheta de stare
        self.status_label.setText(message)

    def clear_message(self):
        """Clear the message from the main window's message area"""
        if hasattr(self, 'file_manager') and self.file_manager and hasattr(self.file_manager, 'clear_message'):
            self.file_manager.clear_message()
