import sys
import os
import logging
import datetime
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, 
                             QPushButton, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QFormLayout, QLineEdit,
                             QSpinBox, QCheckBox, QGroupBox, QFileDialog,
                             QMessageBox, QStatusBar, QDialog)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QDateTime, QEvent
from PyQt5.QtGui import QIcon, QTextCursor, QFont, QColor, QTextCharFormat

# Import the FTP server and other necessary dependencies
import ftp_server
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.filesystems import FilesystemError

# Import the module for user management
from user_manager import UserManagerDialog

# Event class for server errors
class ServerErrorEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self):
        super().__init__(ServerErrorEvent.EVENT_TYPE)

# Class to redirect output to TextEdit and file
class OutputRedirector(QObject):
    output_written = pyqtSignal(str, str)  # signal for text and type (info, error, etc)
    
    def __init__(self, log_file_path):
        super().__init__()
        self.log_file = open(log_file_path, 'a', encoding='utf-8')
        self.log_file.write(f"\n\n--- NEW SESSION: {datetime.datetime.now()} ---\n\n")
        
    def write(self, text):
        # Determine the message type based on content
        if "Eroare" in text or "Error" in text or "eroare" in text:
            msg_type = "error"
        elif "Info" in text or "info" in text:
            msg_type = "info"
        elif "Server FTP" in text or "pornit" in text or "rulează" in text:
            msg_type = "success"
        elif "Warning" in text or "Avertisment" in text:
            msg_type = "warning"
        else:
            msg_type = "normal"
            
        # Send the text to the widget and write it to the log file
        self.output_written.emit(text, msg_type)
        
        # Write to the log file
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_file.write(f"[{timestamp}] {text}")
            self.log_file.flush()  # Ensure it is written to the file immediately
        except:
            # Ignore file writing errors
            pass
    
    def flush(self):
        try:
            self.log_file.flush()
        except:
            pass
        
    def close(self):
        try:
            if self.log_file:
                self.log_file.close()
        except:
            pass

class FTPServerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initial configuration
        self.setWindowTitle("FTP Server UI")
        self.setGeometry(100, 100, 800, 600)
        self.server_thread = None
        self.server_running = False
        self.ftpserver = None
        
        # Prepare the directory for logs
        self.logs_dir = os.path.join(os.getcwd(), "logs")
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
            
        # Create the log file name with timestamp
        self.log_file_path = os.path.join(
            self.logs_dir, 
            f"ftp_server_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        # Initialize the output redirector
        self.redirector = OutputRedirector(self.log_file_path)
        
        # Set up the interface
        self.setup_ui()
        
    def setup_ui(self):
        # Central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Application title
        title_label = QLabel("FTP Server with SQLite")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # Server configuration section
        config_group = QGroupBox("Server Configuration")
        config_layout = QFormLayout()
        
        # IP and port
        self.host_input = QLineEdit("0.0.0.0")
        self.host_input.setEnabled(False)  # Disabled to force listening on all interfaces
        config_layout.addRow("IP Address:", self.host_input)
        
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(2121)
        config_layout.addRow("Port:", self.port_input)
        
        # Remove the field for choosing the database
        # The database will always be ftp_users.db from the current directory
        
        # Additional options
        self.allow_anon_check = QCheckBox("Allow Anonymous Connection")
        self.allow_anon_check.setChecked(True)
        config_layout.addRow("", self.allow_anon_check)
        
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Server")
        self.start_button.clicked.connect(self.start_server)
        self.start_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        self.stop_button = QPushButton("Stop Server")
        self.stop_button.clicked.connect(self.stop_server)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        
        self.users_button = QPushButton("Manage Users")
        self.users_button.clicked.connect(self.manage_users)
        self.users_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        
        self.view_logs_button = QPushButton("Open Log File")
        self.view_logs_button.clicked.connect(lambda: os.startfile(self.log_file_path) if sys.platform == 'win32' else None)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.users_button)
        control_layout.addWidget(self.view_logs_button)
        
        main_layout.addLayout(control_layout)
        
        # Output console
        output_group = QGroupBox("Server Messages")
        output_layout = QVBoxLayout()
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier New", 10))
        self.output_text.document().setMaximumBlockCount(5000)  # Limit the number of lines for performance
        output_layout.addWidget(self.output_text)
        
        # Connect the signal from the redirector to the display function
        self.redirector.output_written.connect(self.append_output)
        
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Server stopped")
        
        self.setCentralWidget(central_widget)
        
    @pyqtSlot(str, str)
    def append_output(self, text, msg_type):
        # Set the text format based on the message type
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output_text.setTextCursor(cursor)
        
        # Format for different message types
        format_map = {
            "normal": QColor(0, 0, 0),        # black
            "info": QColor(0, 0, 255),        # blue
            "error": QColor(255, 0, 0),       # red
            "warning": QColor(255, 165, 0),   # orange
            "success": QColor(0, 128, 0)      # green
        }
        
        # Apply the format
        format = QTextCharFormat()
        format.setForeground(format_map.get(msg_type, QColor(0, 0, 0)))
        
        # Add the formatted text
        self.output_text.textCursor().insertText(text)
        
        # Scroll to the end
        self.output_text.ensureCursorVisible()
        
    def start_server(self):
        if not self.server_running:
            # Disable configuration buttons
            self.host_input.setEnabled(False)
            self.port_input.setEnabled(False)
            self.allow_anon_check.setEnabled(False)
            
            # Update buttons
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            
            # Set status
            self.status_bar.showMessage("Server started")
            
            # Redirect stdout and stderr to our redirector
            sys.stdout = self.redirector
            sys.stderr = self.redirector
            
            # Start the server in a separate thread
            self.server_thread = threading.Thread(target=self.run_server)
            self.server_thread.daemon = True  # Ensure the thread closes with the application
            self.server_thread.start()
            
            self.server_running = True
    
    def run_server(self):
        try:
            # Display an initialization message
            print(f"Initializing FTP server...")
            print(f"Port: {self.port_input.value()}")
            print(f"Allow anonymous connection: {'Yes' if self.allow_anon_check.isChecked() else 'No'}")
            
            # Initialize the database manager
            db_manager = ftp_server.UserDatabase("ftp_users.db")
            
            # Create an authorizer that uses the database
            authorizer = ftp_server.SQLiteAuthorizer(db_manager)
            
            # Add an anonymous user with read permissions if enabled
            if self.allow_anon_check.isChecked():
                authorizer.add_anonymous("/", perm="elr")
            
            # Use the handler defined in ftp_server.py
            handler = ftp_server.CustomFTPHandler
            handler.authorizer = authorizer
            handler.abstracted_fs = ftp_server.WindowsRootFS
            
            # Disable checking if the directory is at the root (not relevant for our virtual system)
            handler.permit_foreign_addresses = True
            handler.permit_privileged_ports = True
            
            # Set the format for logging
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
            address = (self.host_input.text(), self.port_input.value())
            self.ftpserver = FTPServer(address, handler)
            
            # Set the connection limit
            self.ftpserver.max_cons = 256
            self.ftpserver.max_cons_per_ip = 5
            
            print(f"FTP server running at {address[0]}:{address[1]}")
            if self.allow_anon_check.isChecked():
                print(f"Or anonymous connection enabled")
            print("Press the 'Stop Server' button to stop the server")
            
            # Start the server
            self.ftpserver.serve_forever()
            
        except Exception as e:
            print(f"Server error: {str(e)}")
            # Reset the UI state in case of an error
            QApplication.postEvent(self, ServerErrorEvent())
    
    def stop_server(self):
        if self.server_running:
            try:
                # Stop the FTP server
                if self.ftpserver:
                    print("Stopping FTP server...")
                    self.ftpserver.close_all()
                    
                # Reset the thread state
                self.server_thread = None
                self.ftpserver = None
                
                # Restore stdout and stderr
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                
                # Reset the interface
                self.reset_server_ui()
                
                print("FTP server stopped successfully")
            except Exception as e:
                print(f"Error stopping the server: {str(e)}")
                self.reset_server_ui()
            
            # Set status
            self.status_bar.showMessage("Server stopped")
            self.server_running = False

    def closeEvent(self, event):
        # Ensure the server is stopped and the log file is closed before exiting
        try:
            if self.server_running:
                self.stop_server()
                
            # Restore stdout and stderr and close the redirector
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            self.redirector.close()
        except:
            pass
            
        event.accept()
    
    def customEvent(self, event):
        """Handle custom events"""
        if event.type() == ServerErrorEvent.EVENT_TYPE:
            # A server error occurred, reset the interface
            self.reset_server_ui()
        else:
            super().customEvent(event)
    
    def reset_server_ui(self):
        """Reset the interface after a server error"""
        # Execute on the UI thread
        self.server_running = False
        self.host_input.setEnabled(True)
        self.port_input.setEnabled(True)
        self.allow_anon_check.setEnabled(True)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_bar.showMessage("Server stopped due to an error")
        
    def manage_users(self):
        """Open the user management dialog"""
        # Create an instance of the user management dialog
        user_dialog = UserManagerDialog(parent=self)
        
        # If the server is running, stop it temporarily
        was_running = self.server_running
        if was_running:
            # Do not stop the server, just notify the user
            QMessageBox.information(
                self,
                "Notification",
                "Added/modified users will be available after restarting the server."
            )
            
        # Show the dialog
        dialog_result = user_dialog.exec_()
        
        # Inform the user to restart the server to apply changes
        if dialog_result == QDialog.Accepted and was_running:
            QMessageBox.information(
                self,
                "User Changes",
                "Changes have been saved. Restart the server to apply the changes."
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FTPServerUI()
    window.show()
    sys.exit(app.exec_())