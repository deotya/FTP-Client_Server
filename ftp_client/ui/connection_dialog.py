"""
Dialog for connecting to an FTP server
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                            QSpinBox, QComboBox, QLabel, QCheckBox, QPushButton,
                            QHBoxLayout, QListWidget, QListWidgetItem, QSplitter,
                            QWidget, QMessageBox, QFileDialog, QInputDialog)
from PyQt5.QtCore import Qt, pyqtSlot

from ftp_client.utils.database import ConnectionDatabase

class FTPConnectionDialog(QDialog):
    """Dialog for connecting to an FTP server"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to FTP Server")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Initialize the connection database
        self.db = ConnectionDatabase()
        
        # Initialize the flag for SFTP mode
        self.is_sftp_mode = False
        
        self.setup_ui()
        self.load_saved_connections()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Use a splitter to separate the connection list from the connection form
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - List of saved connections
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        list_label = QLabel("Saved Connections:")
        left_layout.addWidget(list_label)
        
        self.connections_list = QListWidget()
        self.connections_list.itemDoubleClicked.connect(self.on_connection_selected)
        left_layout.addWidget(self.connections_list)
        
        # Button to delete the connection
        self.delete_btn = QPushButton("Delete Connection")
        self.delete_btn.clicked.connect(self.delete_selected_connection)
        left_layout.addWidget(self.delete_btn)
        
        splitter.addWidget(left_widget)
        
        # Right panel - Connection form
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        form_layout = QFormLayout()
        
        # Connection name (optional)
        self.name_input = QLineEdit()
        form_layout.addRow("Connection Name:", self.name_input)
        
        # Connection type selector
        self.connection_type = QComboBox()
        self.connection_type.addItem("FTP", "ftp")
        self.connection_type.addItem("SFTP", "sftp")
        self.connection_type.currentIndexChanged.connect(self.on_connection_type_changed)
        form_layout.addRow("Connection Type:", self.connection_type)
        
        # Host
        self.host_input = QLineEdit()
        self.host_input.setText("localhost")
        form_layout.addRow("Server:", self.host_input)
        
        # Port
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(21)  # Default FTP port
        form_layout.addRow("Port:", self.port_input)
        
        # Update port when connection type changes
        self.connection_type.currentIndexChanged.connect(self.update_port)
        
        # Username
        self.username_input = QLineEdit()
        self.username_input.setText("anonymous")
        form_layout.addRow("Username:", self.username_input)
        
        # Password
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.password_input)
        
        # Private key for SFTP
        self.key_file_layout = QHBoxLayout()
        self.key_file_input = QLineEdit()
        self.key_file_input.setReadOnly(True)
        self.key_file_input.setPlaceholderText("Optional: Select private key file")
        self.key_file_btn = QPushButton("Select...")
        self.key_file_btn.clicked.connect(self.select_key_file)
        self.key_file_layout.addWidget(self.key_file_input)
        self.key_file_layout.addWidget(self.key_file_btn)
        
        # Add a field for the private key passphrase
        self.key_passphrase_input = QLineEdit()
        self.key_passphrase_input.setPlaceholderText("Leave empty if the key has no passphrase")
        self.key_passphrase_input.setEchoMode(QLineEdit.Password)
        
        # Add fields for the private key
        self.key_file_row = form_layout.addRow("Private Key:", self.key_file_layout)
        self.key_passphrase_row = form_layout.addRow("Key Passphrase:", self.key_passphrase_input)
        
        # Initially hide the private key rows
        self.key_file_input.hide()
        self.key_file_btn.hide()
        self.key_passphrase_input.hide()
        
        # Setting the stretch to zero, the rows will occupy minimal space
        form_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        
        # Informative note
        info_label = QLabel("For the local server, users are: 'user/password' and 'admin/admin'.")
        info_label.setStyleSheet("color: #0066cc; font-style: italic;")
        form_layout.addRow("", info_label)
        
        # Checkbox to save credentials
        self.save_credentials = QCheckBox("Save this connection")
        form_layout.addRow("", self.save_credentials)
        
        right_layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.on_connect_clicked)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.cancel_button)
        
        right_layout.addLayout(button_layout)
        
        splitter.addWidget(right_widget)
        
        # Set initial sizes for the splitter
        splitter.setSizes([200, 300])
        
    def on_connection_type_changed(self, index):
        """Handler for changing the connection type"""
        connection_type = self.connection_type.currentData()
        
        # Update the port
        self.update_port(index)
        
        # Update the SFTP flag
        self.is_sftp_mode = (connection_type == "sftp")
        
        # Show or hide fields for the private key
        if connection_type == "sftp":
            self.key_file_input.show()
            self.key_file_btn.show()
            self.key_passphrase_input.show()
        else:
            self.key_file_input.hide()
            self.key_file_btn.hide()
            self.key_passphrase_input.hide()
            # Clear key fields when type changes
            self.key_file_input.clear()
            self.key_passphrase_input.clear()
            
    def select_key_file(self):
        """Open a dialog to select the private key file"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select private key file", "",
            "Private key files (*.pem *.key *.openssh id_rsa id_ed25519 id_ed25519ftp);;All files (*)", 
            options=options
        )
        if file_path:
            self.key_file_input.setText(file_path)
            
    def update_port(self, index):
        """Update the port based on the selected connection type"""
        connection_type = self.connection_type.currentData()
        if connection_type == "ftp":
            self.port_input.setValue(21)  # Default FTP port
        elif connection_type == "sftp":
            self.port_input.setValue(22)  # Default SFTP port

    def load_saved_connections(self):
        """Load the list of saved connections from the database"""
        self.connections_list.clear()
        self.connections = self.db.get_all_connections()
        
        for connection in self.connections:
            item_text = f"{connection['name']} ({connection['host']}:{connection['port']} - {connection['username']})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, connection['id'])
            self.connections_list.addItem(item)
    
    def on_connection_selected(self, item):
        """Populate the form fields with the details of the selected connection"""
        connection_id = item.data(Qt.UserRole)
        connection = self.db.get_connection(connection_id)
        
        if connection:
            self.name_input.setText(connection['name'])
            
            # Set the connection type
            connection_type = connection.get('connection_type', 'ftp')
            index = self.connection_type.findData(connection_type)
            if index >= 0:
                self.connection_type.setCurrentIndex(index)
                
            self.host_input.setText(connection['host'])
            self.port_input.setValue(connection['port'])
            self.username_input.setText(connection['username'])
            self.password_input.setText(connection['password'])
            self.save_credentials.setChecked(True)
            
            # Update the SFTP flag
            self.is_sftp_mode = (connection_type == "sftp")
            
            # Set the private key and its passphrase if they exist
            if self.is_sftp_mode and 'key_file' in connection and connection['key_file']:
                self.key_file_input.setText(connection['key_file'])
                if 'key_passphrase' in connection and connection['key_passphrase']:
                    self.key_passphrase_input.setText(connection['key_passphrase'])
                else:
                    self.key_passphrase_input.clear()
            
            # Store the ID of the selected connection
            self.selected_connection_id = connection_id
    
    def delete_selected_connection(self):
        """Delete the selected connection from the database"""
        selected_items = self.connections_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Select a connection to delete.")
            return
            
        item = selected_items[0]
        connection_id = item.data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self, 
            "Delete Confirmation", 
            "Are you sure you want to delete this connection?",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db.delete_connection(connection_id):
                self.load_saved_connections()
                QMessageBox.information(self, "Success", "Connection was successfully deleted.")
            else:
                QMessageBox.warning(self, "Error", "Connection could not be deleted.")
    
    def on_connect_clicked(self):
        """Handle the connect action and save the connection"""
        connection_info = self.get_connection_info()
        
        # Check if we have a name for the connection if we want to save it
        if connection_info["save"] and not connection_info["name"]:
            # Generate an automatic name if not specified
            connection_info["name"] = f"{connection_info['host']}:{connection_info['port']}"
        
        # Save the connection if necessary
        if connection_info["save"]:
            connection_id = self.db.save_connection(
                connection_info["name"],
                connection_info["host"],
                connection_info["port"],
                connection_info["username"],
                connection_info["password"],
                connection_info["connection_type"],
                connection_info["key_file"],
                connection_info.get("key_passphrase", "")
            )
            # Store the connection ID to update it with the last used date
            connection_info["id"] = connection_id
        
        # Accept the dialog to proceed with the connection
        self.accept()
        
    def get_connection_info(self):
        """Return a dictionary with the connection information"""
        connection_type = self.connection_type.currentData()
        
        # Prepare the private key information
        key_file = ""
        key_passphrase = ""
        if connection_type == "sftp" and self.key_file_input.text().strip():
            key_file = self.key_file_input.text().strip()
            key_passphrase = self.key_passphrase_input.text()
        
        return {
            "name": self.name_input.text(),
            "connection_type": connection_type,
            "host": self.host_input.text(),
            "port": self.port_input.value(),
            "username": self.username_input.text(),
            "password": self.password_input.text(),
            "key_file": key_file,
            "key_passphrase": key_passphrase,
            "save": self.save_credentials.isChecked()
        }