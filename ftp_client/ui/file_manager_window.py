"""
Main window of the File Manager application
"""

import os
from datetime import datetime
import re
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QLabel, QMessageBox, QToolBar, QMenu, QTabWidget, QTableWidget, 
                            QTableWidgetItem, QHeaderView, QTextEdit, QSplitter)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

from ftp_client.ui.local_panel import LocalPanel
from ftp_client.ui.ftp_panel import FTPPanel
from ftp_client.ui.common.styles import TRANSFER_BUTTON_STYLE

class FileManager(QMainWindow):
    """Main window of the File Manager application"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
        # Force button state update after all components are initialized
        QTimer.singleShot(100, self.check_ftp_status)

    def init_ui(self):
        """Initialize user interface"""
        # Configure window
        self.setWindowTitle('FTP Client')
        self.setGeometry(100, 100, 1200, 800)
        
        # Create the top toolbar for FTP connection buttons
        self.create_toolbar()
        
        # Main widget with vertical layout to arrange panels and message area
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)  # Margins for a nicer appearance
        self.setCentralWidget(main_widget)
        
        # Container for file panels
        panels_widget = QWidget()
        panels_layout = QHBoxLayout(panels_widget)
        panels_layout.setContentsMargins(0, 0, 0, 0)  # Remove internal margins
        
        # Panel for local file system (left)
        self.local_panel = LocalPanel(self)
        
        # Panel for central transfer buttons
        central_panel = self.create_central_panel()
        
        # Panel for FTP (right) - pass reference directly to the main window
        self.ftp_panel = FTPPanel(parent=self, file_manager=self)
        
        # Update ftp_panel to hide connection buttons
        self.ftp_panel.hide_connection_buttons()
        
        # Add the three panels to the panels layout
        panels_layout.addWidget(self.local_panel)
        panels_layout.addWidget(central_panel, 0)  # 0 = minimum size for the central panel
        panels_layout.addWidget(self.ftp_panel)
        
        # Set the ratio between side panels to 10:10 (or 1:1)
        panels_layout.setStretch(0, 10)
        panels_layout.setStretch(2, 10)
        
        # Add the panels container to the main layout
        main_layout.addWidget(panels_widget)
        
        # Add the message area at the bottom
        self.create_message_area()
        main_layout.addWidget(self.message_container)

    def create_toolbar(self):
        """Create the top toolbar with FTP connection buttons"""
        toolbar = QToolBar("FTP Connection Bar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        
        # Create dropdown button for saved connections
        self.connections_btn = QPushButton("FTP Connect")
        self.connections_btn.setMenu(QMenu())
        self.connections_btn.clicked.connect(self.handle_connect_clicked)
        
        # Retrieve buttons from ftp_panel and add them to the toolbar
        disconnect_btn = QPushButton("Disconnect")
        status_label = QLabel("Disconnected")
        
        # Save references to buttons and label to update them from ftp_panel
        self.connect_btn = self.connections_btn
        self.disconnect_btn = disconnect_btn
        self.status_label = status_label
        
        # Connect the disconnect button
        disconnect_btn.clicked.connect(self.handle_disconnect_clicked)
        
        # Initially disable the disconnect button
        disconnect_btn.setEnabled(False)
        
        # Add buttons and label to the toolbar
        toolbar.addWidget(self.connections_btn)
        toolbar.addWidget(disconnect_btn)
        toolbar.addWidget(status_label)
        
        # Add the toolbar to the top of the window
        self.addToolBar(toolbar)
        
        # Load saved connections
        self.load_saved_connections()
        
    def load_saved_connections(self):
        """Load saved connections into the dropdown menu"""
        from ftp_client.utils.database import ConnectionDatabase
        db = ConnectionDatabase()
        connections = db.get_all_connections()
        
        menu = self.connections_btn.menu()
        menu.clear()
        
        for connection in connections:
            action = menu.addAction(f"{connection['name']} ({connection['host']}:{connection['port']})")
            action.setData(connection)
            action.triggered.connect(lambda checked, conn=connection: self.connect_to_saved(conn))
            
        menu.addSeparator()
        new_connection = menu.addAction("New Connection...")
        new_connection.triggered.connect(self.handle_connect_clicked)
        
    def connect_to_saved(self, connection):
        """Connect to a saved connection"""
        if hasattr(self, 'ftp_panel') and self.ftp_panel:
            # Retrieve password and other details from the database
            from ftp_client.utils.database import ConnectionDatabase
            db = ConnectionDatabase()
            full_connection = db.get_connection(connection['id'])
            
            if full_connection:
                # Set connection type in FTPPanel
                self.ftp_panel.connection_type = full_connection.get('connection_type', 'ftp')
                
                # Update ftp_panel interface to handle the appropriate type
                if self.ftp_panel.connection_type == 'sftp':
                    from ftp_client.sftp_client import SFTPClient
                    self.ftp_panel.ftp_client = SFTPClient()
                else:
                    from ftp_client import FTPClient
                    self.ftp_panel.ftp_client = FTPClient()
                    
                # Reconnect signals for the new client
                self.ftp_panel.connect_signals()
                
                # Connect to the server
                self.ftp_panel.connect_to_ftp(
                    full_connection['host'],
                    full_connection['port'],
                    full_connection['username'],
                    full_connection['password'],
                    full_connection.get('key_file'),
                    full_connection.get('key_passphrase')
                )
                
                # Update last used in the database
                db.update_last_used(connection['id'])

    def handle_connect_clicked(self):
        """Handler for connect button click"""
        if hasattr(self, 'ftp_panel') and self.ftp_panel:
            self.ftp_panel.show_connection_dialog()
            self.load_saved_connections()
            
    def handle_disconnect_clicked(self):
        """Handler for disconnect button click"""
        # Asigură-te că cursorul este normal
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        QApplication.restoreOverrideCursor()
        
        if hasattr(self, 'ftp_panel') and self.ftp_panel:
            # Verificăm dacă există un thread de conectare în desfășurare și îl oprim
            if hasattr(self.ftp_panel, 'connection_thread') and self.ftp_panel.connection_thread and self.ftp_panel.connection_thread.isRunning():
                try:
                    # Anulăm thread-ul de conectare
                    self.ftp_panel.connection_thread.terminate()
                    self.ftp_panel.connection_thread.wait(1000)  # Așteptăm maxim 1 secundă
                    self.show_message("Încercare de conectare anulată", "warning")
                except Exception as e:
                    self.show_message(f"Nu s-a putut anula conexiunea: {str(e)}", "error")
            
            # Deconectăm clientul FTP
            self.ftp_panel.disconnect()
            
            # Actualizăm starea butoanelor
            self.update_connection_status(False, "Deconectat")

    def create_central_panel(self):
        """Create the central panel with transfer buttons"""
        central_panel = QWidget()
        central_layout = QHBoxLayout(central_panel)
        
        # Remove margins for a more compact look
        central_layout.setContentsMargins(0, 0, 0, 0)
        
        # Vertical container for buttons
        button_container = QWidget()
        # Use VBoxLayout to arrange buttons vertically (one above the other)
        button_layout = QVBoxLayout(button_container)
        
        # Add empty space at the top for alignment
        button_layout.addStretch()
        
        # Button for copying from Local to FTP
        self.copy_to_ftp_btn = QPushButton('➡')  # Thick Unicode arrow to the right
        self.copy_to_ftp_btn.setMinimumHeight(40)
        self.copy_to_ftp_btn.setMinimumWidth(40)
        self.copy_to_ftp_btn.setMaximumWidth(40)
        self.copy_to_ftp_btn.setFont(QFont('DejaVu Sans', 18, QFont.Bold))
        self.copy_to_ftp_btn.setToolTip('Copy to FTP')
        self.copy_to_ftp_btn.setStyleSheet(TRANSFER_BUTTON_STYLE)
        
        self.copy_to_ftp_btn.clicked.connect(self.copy_from_local_to_ftp)
        button_layout.addWidget(self.copy_to_ftp_btn)
        
        # Space between buttons
        button_layout.addSpacing(10)
        
        # Button for copying from FTP to Local
        self.copy_to_local_btn = QPushButton('⬅')  # Thick Unicode arrow to the left
        self.copy_to_local_btn.setMinimumHeight(40)
        self.copy_to_local_btn.setMinimumWidth(40)
        self.copy_to_local_btn.setMaximumWidth(40)
        self.copy_to_local_btn.setFont(QFont('DejaVu Sans', 18, QFont.Bold))
        self.copy_to_local_btn.setToolTip('Copy to Local')
        self.copy_to_local_btn.setStyleSheet(TRANSFER_BUTTON_STYLE)
        
        self.copy_to_local_btn.clicked.connect(self.copy_from_ftp_to_local)
        button_layout.addWidget(self.copy_to_local_btn)
        
        # Add empty space at the bottom for alignment
        button_layout.addStretch()
        
        # Center the button container in the central panel
        central_layout.addStretch()
        central_layout.addWidget(button_container)
        central_layout.addStretch()
        
        return central_panel
        
    def copy_from_local_to_ftp(self):
        """Copy the selected file from the local system to FTP"""
        # Get the selected local file path
        local_path = self.local_panel.get_selected_path()
        if not local_path:
            QMessageBox.warning(self, "Warning", "Select a file to copy")
            return
            
        # Delegate the operation to the FTP panel
        self.ftp_panel.upload_from_path(local_path)
            
    def copy_from_ftp_to_local(self):
        """Copy the selected file from FTP to the local system"""
        # Get the current directory from the local panel
        local_dir = self.local_panel.get_current_directory()
        
        # If we have a selected item and it's a directory, use it
        selected_path = self.local_panel.get_selected_path()
        if selected_path and os.path.isdir(selected_path):
            local_dir = selected_path
            
        # Check if the directory exists and we have write permissions
        if not local_dir or not os.path.exists(local_dir):
            # Use the home directory as a fallback
            local_dir = os.path.expanduser("~")
            
        # Delegate the operation to the FTP panel
        self.ftp_panel.download_to_directory(local_dir)

    def update_connection_status(self, connected, message=""):
        """Update the connection buttons and status label"""
        # Directly update the buttons in the toolbar
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        
        # Update the status label
        if message:
            self.status_label.setText(message)
        else:
            self.status_label.setText("Connected" if connected else "Disconnected")

    def check_ftp_status(self):
        """Check the FTP connection status and update the corresponding buttons"""
        if hasattr(self, 'ftp_panel') and self.ftp_panel:
            connected = self.ftp_panel.ftp_client.is_connected
            message = "Connected" if connected else "Disconnected"
            self.update_connection_status(connected, message)

    def closeEvent(self, event):
        """Ensure all connections are properly closed when the application is closed"""
        try:
            # Oprește timer-ul de actualizare a logurilor
            if hasattr(self, 'log_timer') and self.log_timer.isActive():
                self.log_timer.stop()
                
            # Disconnect FTP to avoid abandoned threads
            if hasattr(self, 'ftp_panel') and self.ftp_panel and hasattr(self.ftp_panel, 'ftp_client'):
                if self.ftp_panel.ftp_client and self.ftp_panel.ftp_client.is_connected:
                    self.ftp_panel.ftp_client.disconnect()
                    
            # Close the application log
            from ftp_client.utils.logger import FTPLogger
            FTPLogger.close_app_log()
        except Exception as e:
            print(f"Error closing application: {str(e)}")
        
        # Allow the application to close
        event.accept()

    def create_message_area(self):
        """Create the message area at the bottom of the window as a transfer table"""
        # Create a message container with a white background
        self.message_container = QWidget()
        self.message_container.setStyleSheet("background-color: white; border: 1px solid #cccccc;")
        message_layout = QVBoxLayout(self.message_container)
        message_layout.setContentsMargins(4, 4, 4, 4)  # Smaller margins to save space
        
        # Add a table for transfers
        from PyQt5.QtWidgets import QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
        
        # Create a tab widget
        self.transfer_tabs = QTabWidget()
        self.transfer_tabs.setStyleSheet("QTabBar { font-size: 9pt; }")  # Smaller font for tabs
        
        # Create tables for different types of transfers
        self.queued_transfers = QTableWidget(0, 6)  # 6 columns
        self.successful_transfers = QTableWidget(0, 6)  # 6 columns
        self.failed_transfers = QTableWidget(0, 6)  # 6 columns
        
        # Set headers for tables
        headers = ["Server/Local file", "Direction", "Remote file", "Size", "Priority", "Time"]
        
        for table in [self.queued_transfers, self.successful_transfers, self.failed_transfers]:
            # Style the table to save space
            table.setStyleSheet("QTableWidget { font-size: 9pt; } QHeaderView { font-size: 9pt; }")
            table.verticalHeader().setDefaultSectionSize(20)  # Smaller row height
            table.setHorizontalHeaderLabels(headers)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
            # Disable cell editing
            table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Add tables to tabs
        self.transfer_tabs.addTab(self.queued_transfers, "Queued Transfers")
        self.transfer_tabs.addTab(self.successful_transfers, "Successful Transfers")
        self.transfer_tabs.addTab(self.failed_transfers, "Failed Transfers")
        
        # Create the widget for displaying logs
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet("QTextEdit { font-family: 'Courier New'; font-size: 9pt; background-color: #f5f5f5; }")
        
        # Add tab for logs (without control menu)
        self.transfer_tabs.addTab(self.log_viewer, "Messages log")
        
        # Timer for automatically updating logs (every 2 seconds)
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.refresh_logs)
        self.log_timer.start(2000)  # 2 seconds
        
        # Add tabs to layout
        message_layout.addWidget(self.transfer_tabs)
        
        # Calculate height as 70% of the initial value of 150 pixels
        new_height = 250  # Slightly increase the container height
        
        # Set the message container height
        self.message_container.setMinimumHeight(new_height)
        self.message_container.setMaximumHeight(new_height)
        
        # Timer for automatically clearing messages after a certain time
        self.message_timer = QTimer()
        self.message_timer.setSingleShot(True)
        self.message_timer.timeout.connect(self.clear_message)
        
        # Create a dictionary to keep track of transfers
        self.transfers = {
            "queued": [],
            "successful": [],
            "failed": []
        }
        
        # Initialize log display
        self.refresh_logs()

    def refresh_logs(self):
        """Load and display log messages only from the most recent log file"""
        try:
            # Get the path to the ftp_log directory
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ftp_log")
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                self.log_viewer.setText("No logs available. Connect to an FTP server to view logs.")
                return
                
            # Get the list of files and sort them by modification date (most recent first)
            log_files = [(f, os.path.getmtime(os.path.join(log_dir, f))) 
                        for f in os.listdir(log_dir) 
                        if f.endswith('.txt') and f.startswith('ftp_client_log_')]
            
            if not log_files:
                self.log_viewer.setText("No logs available. Connect to an FTP server to view logs.")
                return
            
            # Check if the application has just started (first run of refresh_logs)
            if not hasattr(self, '_logs_initialized'):
                self._logs_initialized = True
                self.log_viewer.setText("The application is ready. Connect to an FTP server to view connection logs.")
                return
                
            # Sort files by modification date (most recent first)
            log_files.sort(key=lambda x: x[1], reverse=True)
            
            # Select only the most recent log file
            latest_log_file = log_files[0][0]
            latest_log_path = os.path.join(log_dir, latest_log_file)
            
            # Preserve the current scroll position
            scrollbar = self.log_viewer.verticalScrollBar()
            scroll_position = scrollbar.value()
            was_at_bottom = scroll_position == scrollbar.maximum() or scrollbar.value() == 0
            
            # Read the content of the most recent log file
            try:
                with open(latest_log_path, 'r', encoding='utf-8') as f:
                    log_lines = f.readlines()
                    # Limit to the last 1000 lines for performance
                    if len(log_lines) > 1000:
                        log_lines = log_lines[-1000:]
            except Exception:
                log_lines = []
                
            # If the number of lines hasn't changed, don't update (to avoid flickering)
            if hasattr(self, '_log_lines_count') and self._log_lines_count == len(log_lines):
                # Restore the scroll position
                if not was_at_bottom:
                    scrollbar.setValue(scroll_position)
                return
                
            # Store the number of lines
            self._log_lines_count = len(log_lines)
            
            # Clear the viewer
            self.log_viewer.clear()
            
            # Display the lines with colored formatting
            for line in log_lines:
                line = line.strip()
                color = QColor(0, 0, 0)  # default color: black
                
                if "Error" in line or "error" in line or "failed" in line or "Failed" in line:
                    color = QColor(200, 0, 0)  # roșu
                elif "Warning" in line or "WARNING" in line:
                    color = QColor(255, 140, 0)  # portocaliu
                elif "Success" in line or "success" in line or "downloaded" in line or "uploaded" in line:
                    color = QColor(0, 128, 0)  # verde
                elif "Attempting" in line or "connecting" in line or "Connecting" in line:
                    color = QColor(128, 128, 0)  # galben închis
                
                self.log_viewer.setTextColor(color)
                self.log_viewer.append(line)
            
            # Restore the scroll position or scroll to the end if it was already at the end
            if was_at_bottom:
                scrollbar.setValue(scrollbar.maximum())
            else:
                scrollbar.setValue(scroll_position)
                
        except Exception as e:
            # Capture all errors to prevent application crash
            print(f"Error loading logs: {str(e)}")

    def show_message(self, message, message_type="info", auto_clear=True, timeout=5000):
        """Display a message and update the transfer tables
        
        Args:
            message (str): The message to display
            message_type (str): The type of message (info, success, error, warning)
            auto_clear (bool): Whether the message should be automatically cleared after a time
            timeout (int): The time in milliseconds after which the message will be automatically cleared
        """
        # Doar actualizăm tabelele de transfer fără alte funcționalități
        if "download" in message.lower() or "upload" in message.lower() or "copy" in message.lower():
            if "success" in message_type or "successfully" in message.lower():
                self.add_transfer_to_table("successful", message)
            elif "error" in message_type or "failed" in message.lower() or "error" in message.lower():
                self.add_transfer_to_table("failed", message)
            elif "info" in message_type:
                self.add_transfer_to_table("queued", message)
                
        # Optionally, automatically clear the message after a specified time
        if auto_clear:
            self.message_timer.start(timeout)
            
    def add_transfer_to_table(self, table_type, message):
        """Add a transfer to the appropriate table
        
        Args:
            table_type (str): The type of table ("queued", "successful", "failed")
            message (str): The message containing transfer information
        """
        # Select the appropriate table
        if table_type == "queued":
            table = self.queued_transfers
        elif table_type == "successful":
            table = self.successful_transfers
        elif table_type == "failed":
            table = self.failed_transfers
        else:
            return
        
        # Extract information from the message
        file_regex = r"file ([^ ]+)"
        path_regex = r"to ([^\"]+)"
        
        file_match = re.search(file_regex, message)
        path_match = re.search(path_regex, message)
        
        local_file = ""
        remote_file = ""
        direction = ""
        server = ""
        
        # Determine the server hostname if available
        if hasattr(self, 'ftp_panel') and self.ftp_panel and hasattr(self.ftp_panel, 'ftp_client'):
            try:
                # Try to get the hostname
                host = ""
                if hasattr(self.ftp_panel.ftp_client, 'host'):
                    host = self.ftp_panel.ftp_client.host
                elif hasattr(self.ftp_panel.ftp_client, 'hostname'):
                    host = self.ftp_panel.ftp_client.hostname
                
                # Determine the protocol
                protocol = "sftp" if hasattr(self.ftp_panel, 'connection_type') and self.ftp_panel.connection_type == 'sftp' else "ftp"
                
                if host:
                    server = f"{protocol}://{host}"
            except:
                server = f"{'sftp' if hasattr(self.ftp_panel, 'connection_type') and self.ftp_panel.connection_type == 'sftp' else 'ftp'}://server"
        
        # Determine direction and files
        if "download" in message.lower() or "downloaded" in message.lower():
            direction = "<---"
            if file_match:
                remote_file = file_match.group(1)
            if path_match:
                local_file = path_match.group(1)
        else:  # upload
            direction = "--->"
            if file_match:
                local_file = file_match.group(1)
            if hasattr(self, 'ftp_panel') and self.ftp_panel and hasattr(self.ftp_panel.ftp_client, 'current_directory'):
                try:
                    remote_file = self.ftp_panel.ftp_client.current_directory
                    if not remote_file.endswith('/'):
                        remote_file += '/'
                    if file_match:
                        remote_file += file_match.group(1)
                except:
                    remote_file = file_match.group(1) if file_match else ""
        
        # Determine file size (if available)
        size = "N/A"
        try:
            if local_file and os.path.exists(local_file):
                size_bytes = os.path.getsize(local_file)
                if size_bytes < 1024:
                    size = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size = f"{size_bytes // 1024} KB"
                else:
                    size = f"{size_bytes // (1024 * 1024)} MB"
        except:
            pass
        
        # Current date and time
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Add the row to the table
        row_position = table.rowCount()
        table.insertRow(row_position)
        
        # Populate the cells
        table.setItem(row_position, 0, QTableWidgetItem(server if server else local_file))
        table.setItem(row_position, 1, QTableWidgetItem(direction))
        table.setItem(row_position, 2, QTableWidgetItem(remote_file))
        table.setItem(row_position, 3, QTableWidgetItem(size))
        table.setItem(row_position, 4, QTableWidgetItem("Normal"))
        table.setItem(row_position, 5, QTableWidgetItem(current_time))
        
        # Limit the number of rows to 100 for each table
        if table.rowCount() > 100:
            table.removeRow(0)
            
        # Make the appropriate table visible
        if table_type == "queued":
            self.transfer_tabs.setCurrentIndex(0)
        elif table_type == "successful":
            self.transfer_tabs.setCurrentIndex(1)
        elif table_type == "failed":
            self.transfer_tabs.setCurrentIndex(2)

    def clear_message(self):
        """Clear the message from the waiting area"""
        # Do nothing, keep the transfer history
        pass 

    def open_log_folder(self):
        """Deschide folderul cu fișiere de log în exploratorul de fișiere"""
        try:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ftp_log")
            
            if os.path.exists(log_dir):
                # Deschide folderul în exploratorul de fișiere
                import subprocess, platform
                
                if platform.system() == "Windows":
                    os.startfile(log_dir)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.Popen(["open", log_dir])
                else:  # Linux
                    subprocess.Popen(["xdg-open", log_dir])
        except Exception as e:
            self.log_viewer.append(f"Eroare la deschiderea folderului: {str(e)}") 

    def refresh_log_file_list(self):
        """Metodă păstrată pentru compatibilitate cu codul existent"""
        self.refresh_logs()
            
    def load_selected_log(self):
        """Metodă păstrată pentru compatibilitate cu codul existent"""
        pass 