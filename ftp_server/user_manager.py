import sys
import os
import sqlite3
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget, 
                             QTableWidgetItem, QMessageBox, QCheckBox, 
                             QComboBox, QFileDialog, QGroupBox, QFormLayout, QWidget)
from PyQt5.QtCore import Qt, pyqtSignal


# Import UserDatabase to work with the database
from ftp_server import UserDatabase

class PermissionSelector(QDialog):
    """Dialog for selecting FTP permissions"""
    
    def __init__(self, parent=None, current_permissions="elradfmwMT"):
        super().__init__(parent)
        self.setWindowTitle("Set Permissions")
        self.setMinimumWidth(400)
        self.current_permissions = current_permissions
        self.permissions = ""
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Permissions explanation
        info_label = QLabel(
            "Select permissions for the user:\n"
            "e - Change directory\n"
            "l - List files\n"
            "r - Download files\n"
            "a - Add files\n"
            "d - Delete files\n"
            "f - Rename files\n"
            "m - Create directories\n"
            "w - Write to existing files\n"
            "M - Delete directories\n"
            "T - Transfer files"
        )
        info_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Checkboxes for permissions
        permissions_layout = QHBoxLayout()
        
        # Basic permissions
        basic_group = QGroupBox("Basic Permissions")
        basic_layout = QVBoxLayout()
        
        self.chk_e = QCheckBox("e - Change directory")
        self.chk_l = QCheckBox("l - List files")
        self.chk_r = QCheckBox("r - Download files")
        
        self.chk_e.setChecked("e" in self.current_permissions)
        self.chk_l.setChecked("l" in self.current_permissions)
        self.chk_r.setChecked("r" in self.current_permissions)
        
        basic_layout.addWidget(self.chk_e)
        basic_layout.addWidget(self.chk_l)
        basic_layout.addWidget(self.chk_r)
        basic_group.setLayout(basic_layout)
        permissions_layout.addWidget(basic_group)
        
        # Write permissions
        write_group = QGroupBox("Write Permissions")
        write_layout = QVBoxLayout()
        
        self.chk_a = QCheckBox("a - Add files")
        self.chk_d = QCheckBox("d - Delete files")
        self.chk_f = QCheckBox("f - Rename files")
        self.chk_m = QCheckBox("m - Create directories")
        self.chk_w = QCheckBox("w - Write to files")
        self.chk_M = QCheckBox("M - Delete directories")
        self.chk_T = QCheckBox("T - Transfer files")
        
        self.chk_a.setChecked("a" in self.current_permissions)
        self.chk_d.setChecked("d" in self.current_permissions)
        self.chk_f.setChecked("f" in self.current_permissions)
        self.chk_m.setChecked("m" in self.current_permissions)
        self.chk_w.setChecked("w" in self.current_permissions)
        self.chk_M.setChecked("M" in self.current_permissions)
        self.chk_T.setChecked("T" in self.current_permissions)
        
        write_layout.addWidget(self.chk_a)
        write_layout.addWidget(self.chk_d)
        write_layout.addWidget(self.chk_f)
        write_layout.addWidget(self.chk_m)
        write_layout.addWidget(self.chk_w)
        write_layout.addWidget(self.chk_M)
        write_layout.addWidget(self.chk_T)
        
        write_group.setLayout(write_layout)
        permissions_layout.addWidget(write_group)
        
        layout.addLayout(permissions_layout)
        
        # Button for presets
        preset_layout = QHBoxLayout()
        
        presets_label = QLabel("Presets:")
        self.presets_combo = QComboBox()
        self.presets_combo.addItems([
            "Read only (elr)", 
            "Read and write (elradfmw)", 
            "Full control (elradfmwMT)",
            "Custom"
        ])
        self.presets_combo.currentIndexChanged.connect(self.apply_preset)
        
        preset_layout.addWidget(presets_label)
        preset_layout.addWidget(self.presets_combo)
        
        layout.addLayout(preset_layout)
        
        # Initialize the correct preset value
        if self.current_permissions == "elr":
            self.presets_combo.setCurrentIndex(0)
        elif self.current_permissions == "elradfmw":
            self.presets_combo.setCurrentIndex(1)
        elif self.current_permissions == "elradfmwMT":
            self.presets_combo.setCurrentIndex(2)
        else:
            self.presets_combo.setCurrentIndex(3)
        
        # OK/Cancel buttons
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
    
    def apply_preset(self, index):
        """Apply a predefined set of permissions"""
        if index == 0:  # Read only
            self.chk_e.setChecked(True)
            self.chk_l.setChecked(True)
            self.chk_r.setChecked(True)
            self.chk_a.setChecked(False)
            self.chk_d.setChecked(False)
            self.chk_f.setChecked(False)
            self.chk_m.setChecked(False)
            self.chk_w.setChecked(False)
            self.chk_M.setChecked(False)
            self.chk_T.setChecked(False)
        elif index == 1:  # Read and write
            self.chk_e.setChecked(True)
            self.chk_l.setChecked(True)
            self.chk_r.setChecked(True)
            self.chk_a.setChecked(True)
            self.chk_d.setChecked(True)
            self.chk_f.setChecked(True)
            self.chk_m.setChecked(True)
            self.chk_w.setChecked(True)
            self.chk_M.setChecked(False)
            self.chk_T.setChecked(False)
        elif index == 2:  # Full control
            self.chk_e.setChecked(True)
            self.chk_l.setChecked(True)
            self.chk_r.setChecked(True)
            self.chk_a.setChecked(True)
            self.chk_d.setChecked(True)
            self.chk_f.setChecked(True)
            self.chk_m.setChecked(True)
            self.chk_w.setChecked(True)
            self.chk_M.setChecked(True)
            self.chk_T.setChecked(True)
    
    def get_permissions(self):
        """Return the selected permissions as a string"""
        permissions = ""
        if self.chk_e.isChecked(): permissions += "e"
        if self.chk_l.isChecked(): permissions += "l"
        if self.chk_r.isChecked(): permissions += "r"
        if self.chk_a.isChecked(): permissions += "a"
        if self.chk_d.isChecked(): permissions += "d"
        if self.chk_f.isChecked(): permissions += "f"
        if self.chk_m.isChecked(): permissions += "m"
        if self.chk_w.isChecked(): permissions += "w"
        if self.chk_M.isChecked(): permissions += "M"
        if self.chk_T.isChecked(): permissions += "T"
        
        return permissions
        
    def accept(self):
        """Override accept to save permissions before closing"""
        self.permissions = self.get_permissions()
        super().accept()

class UserDialog(QDialog):
    """Dialog for adding or editing a user"""
    
    def __init__(self, parent=None, username="", password="", permissions="elradfmwMT", home_dir="/"):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit User")
        self.setMinimumWidth(400)
        
        self.edit_mode = bool(username)  # If username is not empty, we are in edit mode
        
        # Initial values
        self.username = username
        self.password = password
        self.permissions = permissions
        self.home_dir = home_dir
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Username
        self.username_input = QLineEdit(self.username)
        self.username_input.setEnabled(not self.edit_mode)  # Disabled in edit mode
        form_layout.addRow("Username:", self.username_input)
        
        # Password
        self.password_input = QLineEdit(self.password)
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.password_input)
        
        # Permissions
        self.permissions_input = QLineEdit(self.permissions)
        self.permissions_input.setReadOnly(True)
        
        permissions_layout = QHBoxLayout()
        permissions_layout.addWidget(self.permissions_input)
        
        self.permissions_btn = QPushButton("...")
        self.permissions_btn.setMaximumWidth(30)
        self.permissions_btn.clicked.connect(self.select_permissions)
        permissions_layout.addWidget(self.permissions_btn)
        
        form_layout.addRow("Permissions:", permissions_layout)
        
        # Home directory
        self.home_dir_input = QLineEdit(self.home_dir)
        
        home_dir_layout = QHBoxLayout()
        home_dir_layout.addWidget(self.home_dir_input)
        
        # Add disk selector
        self.disk_combo = QComboBox()
        self.disk_combo.setMaximumWidth(70)
        self.refresh_available_disks()
        self.disk_combo.currentIndexChanged.connect(self.on_disk_selected)
        
        home_dir_layout.addWidget(self.disk_combo)
        
        self.browse_btn = QPushButton("...")
        self.browse_btn.setMaximumWidth(30)
        self.browse_btn.clicked.connect(self.browse_dir)
        home_dir_layout.addWidget(self.browse_btn)
        
        form_layout.addRow("Home Directory:", home_dir_layout)
        
        # Add a help label for the home directory
        help_label = QLabel("Note: Specify '/' for access to all disks, a specific disk (e.g., C:\\) or a specific directory (e.g., C:\\Users)")
        help_label.setStyleSheet("color: #666; font-style: italic;")
        help_label.setWordWrap(True)
        form_layout.addRow("", help_label)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
    
    def select_permissions(self):
        """Open the dialog for selecting permissions"""
        dialog = PermissionSelector(self, self.permissions_input.text())
        if dialog.exec_() == QDialog.Accepted:
            self.permissions_input.setText(dialog.permissions)
    
    def browse_dir(self):
        """Open a dialog for selecting the home directory"""
        dir_path = QFileDialog.getExistingDirectory(self, "Select the home directory")
        if dir_path:
            # Convert to Windows format with double slashes
            dir_path = dir_path.replace('/', '\\')
            self.home_dir_input.setText(dir_path)
    
    def get_user_data(self):
        """Return the user data entered in the dialog"""
        return {
            'username': self.username_input.text(),
            'password': self.password_input.text(),
            'permissions': self.permissions_input.text(),
            'home_dir': self.home_dir_input.text()
        }
    
    def validate(self):
        """Validate the user data"""
        if not self.username_input.text():
            QMessageBox.warning(self, "Validation", "Username cannot be empty!")
            return False
            
        if not self.password_input.text() and not self.edit_mode:
            QMessageBox.warning(self, "Validation", "Password cannot be empty!")
            return False
            
        if not self.permissions_input.text():
            QMessageBox.warning(self, "Validation", "You must select at least one permission!")
            return False
            
        return True
    
    def accept(self):
        """Check validation before accepting the dialog"""
        if self.validate():
            super().accept()
    
    def refresh_available_disks(self):
        """Identify and add available disks in the system"""
        self.disk_combo.clear()
        self.disk_combo.addItem("Full access (/)", "/")
        
        # In Windows, we can get available disks
        if os.name == 'nt':
            try:
                import win32api
                drives = win32api.GetLogicalDriveStrings().split('\000')
                for drive in drives:
                    if drive:  # Exclude empty strings
                        self.disk_combo.addItem(f"Only {drive[0]}:", f"{drive[0]}:\\")
            except:
                # Fallback - add standard disks
                for letter in ['C', 'D', 'E', 'F']:
                    if os.path.exists(f"{letter}:\\"):
                        self.disk_combo.addItem(f"Only {letter}:", f"{letter}:\\")
                        
        # Select the option corresponding to the current home directory
        if self.home_dir == "/":
            self.disk_combo.setCurrentIndex(0)
        elif len(self.home_dir) == 3 and self.home_dir[1:] == ":\\":
            # It's a disk (e.g., C:\)
            for i in range(self.disk_combo.count()):
                if self.disk_combo.itemData(i) == self.home_dir:
                    self.disk_combo.setCurrentIndex(i)
                    break
                    
    def on_disk_selected(self, index):
        """Update the home directory based on the selected disk"""
        selected_path = self.disk_combo.itemData(index)
        if selected_path:
            self.home_dir_input.setText(selected_path)

class UserManagerDialog(QDialog):
    """Main dialog for managing users"""
    
    # Signal emitted when users are modified
    users_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FTP User Management")
        self.setMinimumSize(700, 500)
        
        # Initialize the database manager
        self.db_manager = UserDatabase()
        
        self.setup_ui()
        self.load_users()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels(["User", "Permissions", "Home Directory", "Actions"])
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.users_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.users_table)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        self.add_user_btn = QPushButton("Add User")
        self.add_user_btn.clicked.connect(self.add_user)
        self.add_user_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        buttons_layout.addWidget(self.add_user_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
    
    def load_users(self):
        """Load users from the database and display them in the table"""
        users = self.db_manager.get_all_users()
        
        self.users_table.setRowCount(len(users))
        
        for row, user in enumerate(users):
            # User column
            self.users_table.setItem(row, 0, QTableWidgetItem(user['username']))
            
            # Permissions column
            self.users_table.setItem(row, 1, QTableWidgetItem(user['permissions']))
            
            # Home Directory column
            self.users_table.setItem(row, 2, QTableWidgetItem(user['home_dir']))
            
            # Actions column
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(4, 4, 4, 4)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setProperty("username", user['username'])
            edit_btn.clicked.connect(lambda _, u=user['username']: self.edit_user(u))
            
            delete_btn = QPushButton("Delete")
            delete_btn.setProperty("username", user['username'])
            delete_btn.clicked.connect(lambda _, u=user['username']: self.delete_user(u))
            
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            
            actions_widget = QWidget()
            actions_widget.setLayout(actions_layout)
            
            self.users_table.setCellWidget(row, 3, actions_widget)
        
        self.users_table.resizeColumnsToContents()
    
    def add_user(self):
        """Add a new user"""
        dialog = UserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            user_data = dialog.get_user_data()
            
            success = self.db_manager.add_user(
                user_data['username'],
                user_data['password'], 
                user_data['permissions'],
                user_data['home_dir']
            )
            
            if success:
                self.load_users()
                self.users_changed.emit()
                QMessageBox.information(self, "Success", "User was added successfully.")
            else:
                QMessageBox.warning(self, "Error", "Could not add user. The name may already exist.")
    
    def edit_user(self, username):
        """Edit an existing user"""
        # Get user data
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT username, permissions, home_dir FROM users WHERE username = ?", 
            (username,)
        )
        
        user_data = cursor.fetchone()
        conn.close()
        
        if not user_data:
            QMessageBox.warning(self, "Error", "User not found.")
            return
        
        # Open the edit dialog
        dialog = UserDialog(
            self,
            username=user_data[0],
            password="",  # Do not load the password
            permissions=user_data[1],
            home_dir=user_data[2]
        )
        
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_user_data()
            
            # Update the user (password is updated only if entered)
            success = self.db_manager.update_user(
                username,
                new_data['password'] if new_data['password'] else None,
                new_data['permissions'],
                new_data['home_dir']
            )
            
            if success:
                self.load_users()
                self.users_changed.emit()
                QMessageBox.information(self, "Success", "User was updated successfully.")
            else:
                QMessageBox.warning(self, "Error", "Could not update user.")
    
    def delete_user(self, username):
        """Delete a user"""
        confirm = QMessageBox.question(
            self,
            "Delete Confirmation",
            f"Are you sure you want to delete the user '{username}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            success = self.db_manager.delete_user(username)
            
            if success:
                self.load_users()
                self.users_changed.emit()
                QMessageBox.information(self, "Success", "User was deleted successfully.")
            else:
                QMessageBox.warning(self, "Error", "Could not delete user.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = UserManagerDialog()
    dialog.exec_()
    sys.exit(app.exec_()) 