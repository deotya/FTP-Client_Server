"""
Panel for navigating and managing files on the local system
"""

import os
import shutil
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QTreeView, QMessageBox, QInputDialog,
                            QAction, QMenu, QFileDialog, QFileSystemModel)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices

from ftp_client.ui.common.styles import TITLE_LABEL_STYLE

class LocalPanel(QWidget):
    """Panel for navigating the local file system"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.copy_source = None
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Add field for navigation path
        path_layout = QHBoxLayout()
        path_label = QLabel('Local site:')
        self.local_path_input = QLineEdit()
        self.local_path_input.setPlaceholderText('Enter path...')
        self.local_path_input.returnPressed.connect(self.navigate_to_local_path)
        
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.local_path_input)
        main_layout.addLayout(path_layout)
        
        # Tree view for navigation
        self.model = QFileSystemModel()
        # Set root at the file system level (equivalent to "\")
        self.model.setRootPath("")
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        # Set index at the root of the file system
        self.tree_view.setRootIndex(self.model.index(""))
        self.tree_view.setColumnWidth(0, 250)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        
        # Set initial path in the input field
        self.local_path_input.setText("\\")
        
        # Connect double-click signal to update path
        self.tree_view.doubleClicked.connect(self.on_tree_view_double_clicked)
        
        main_layout.addWidget(self.tree_view)
        
    def get_selected_path(self):
        """Returns the path of the selected item in the tree view"""
        indexes = self.tree_view.selectedIndexes()
        if indexes:

            return self.model.filePath(indexes[0])
            
        return None
        
    def create_folder(self):
        """Creates a new folder in the selected location"""
        current_path = self.get_selected_path()
        if not current_path:
            # If nothing is selected, use My Computer / Computer / This PC
            current_path = os.path.expanduser("~")  # Use Home directory as an alternative
        
        if os.path.isfile(current_path):
            current_path = os.path.dirname(current_path)
        
        folder_name, ok = QInputDialog.getText(self, 'Create Folder', 
                                            'Enter folder name:')
        if ok and folder_name:
            try:
                new_folder_path = os.path.join(current_path, folder_name)
                os.makedirs(new_folder_path, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Could not create folder: {str(e)}')
                
    def delete_item(self):
        """Deletes the selected item (file or folder)"""
        path = self.get_selected_path()
        if not path:
            return
            
        confirm = QMessageBox.question(self, 'Delete Confirmation', 
                                    f'Are you sure you want to delete "{os.path.basename(path)}"?',
                                    QMessageBox.Yes | QMessageBox.No)
                                    
        if confirm == QMessageBox.Yes:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Could not delete: {str(e)}')
                
    def rename_item(self):
        """Renames the selected item"""
        path = self.get_selected_path()
        if not path:
            return
            
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, 'Rename', 
                                        'Enter new name:',
                                        text=old_name)
                                        
        if ok and new_name and new_name != old_name:
            try:
                new_path = os.path.join(os.path.dirname(path), new_name)
                os.rename(path, new_path)
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Could not rename: {str(e)}')
                
    def copy_item(self):
        """Copies the selected item to clipboard"""
        path = self.get_selected_path()
        if path:
            self.copy_source = path
            
    def paste_item(self):
        """Pastes the item from clipboard to the selected location"""
        if not self.copy_source:
            QMessageBox.information(self, 'Information', 'Nothing to paste. Copy an item first.')
            return
            
        dest_path = self.get_selected_path()
        if not dest_path:
            # If nothing is selected, use the Home directory
            dest_path = os.path.expanduser("~")
            
        if os.path.isfile(dest_path):
            dest_path = os.path.dirname(dest_path)
            
        source_name = os.path.basename(self.copy_source)
        dest_file = os.path.join(dest_path, source_name)
        
        # Check if the file/folder already exists at the destination
        if os.path.exists(dest_file):
            confirm = QMessageBox.question(self, 'Replace Confirmation', 
                                        f'"{source_name}" already exists. Do you want to replace it?',
                                        QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.No:
                return
        
        try:
            if os.path.isfile(self.copy_source):
                shutil.copy2(self.copy_source, dest_file)
            else:
                shutil.copytree(self.copy_source, dest_file, dirs_exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Could not paste: {str(e)}')
    
    def show_context_menu(self, position):
        """Displays the context menu for the selected item"""
        menu = QMenu()
        
        open_action = QAction('Open', self)
        open_action.triggered.connect(self.open_item)
        
        create_folder_action = QAction('Create Folder', self)
        create_folder_action.triggered.connect(self.create_folder)
        
        delete_action = QAction('Delete', self)
        delete_action.triggered.connect(self.delete_item)
        
        rename_action = QAction('Rename', self)
        rename_action.triggered.connect(self.rename_item)
        
        copy_action = QAction('Copy', self)
        copy_action.triggered.connect(self.copy_item)
        
        paste_action = QAction('Paste', self)
        paste_action.triggered.connect(self.paste_item)
        
        # Add action for copying to FTP
        copy_to_ftp_action = QAction('Copy to FTP', self)
        # Connect to the method in the parent class that will be implemented by FileManager
        copy_to_ftp_action.triggered.connect(
            lambda: self.parent().copy_from_local_to_ftp() if hasattr(self.parent(), 'copy_from_local_to_ftp') else None
        )
        
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(create_folder_action)
        menu.addAction(delete_action)
        menu.addAction(rename_action)
        menu.addSeparator()
        menu.addAction(copy_action)
        menu.addAction(paste_action)
        menu.addSeparator()
        menu.addAction(copy_to_ftp_action)
        
        menu.exec_(self.tree_view.mapToGlobal(position))
        
    def open_item(self):
        """Opens the selected item with the default application"""
        path = self.get_selected_path()
        if not path:
            return
            
        if os.path.isfile(path):
            # Open with the default application
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            
    def on_tree_view_double_clicked(self, index):
        """Updates the path field when an item is double-clicked"""
        # Get the path of the item that was double-clicked
        path = self.model.filePath(index)
        
        # Update the path in the input
        if path:
            self.local_path_input.setText(path)

    def navigate_to_local_path(self):
        """Navigate to the path specified in the input field"""
        path = self.local_path_input.text()
        
        # For the special root path "\"
        if path == "\\" or path == "/":
            self.tree_view.setRootIndex(self.model.index(""))
            self.local_path_input.setText("\\")
            return
            
        # For any other path
        if os.path.exists(path) and os.path.isdir(path):
            # Use setCurrent to select and highlight the path in the tree view
            index = self.model.index(path)
            self.tree_view.setCurrentIndex(index)
            # Expand the parent to see the selection
            parent_index = index.parent()
            if parent_index.isValid():
                self.tree_view.expand(parent_index)
            # Scroll to the selected location
            self.tree_view.scrollTo(index)
        else:
            QMessageBox.warning(self, 'Warning', f'The specified path does not exist or is not a directory: {path}')
            # Reset the field to the current path or "\"
            current_index = self.tree_view.currentIndex()
            if current_index.isValid():
                current_path = self.model.filePath(current_index)
                self.local_path_input.setText(current_path)
            else:
                self.local_path_input.setText("\\") 

    def get_current_directory(self):
        """Returns the current directory displayed in the tree view"""
        # Check if there is a selection
        selected_path = self.get_selected_path()
        
        if selected_path:
            # If there is a selection, check if it is a directory
            if os.path.isdir(selected_path):
                return selected_path
            else:
                # If it is a file, return the parent directory
                return os.path.dirname(selected_path)
        else:
            # If there is no selection, try to get the current directory from the path field
            current_path = self.local_path_input.text().strip()
            
            # Check if the input path is valid
            if current_path and os.path.exists(current_path) and os.path.isdir(current_path):
                return current_path
            
            # Check the current index in the tree view
            current_index = self.tree_view.rootIndex()
            if current_index.isValid():
                path = self.model.filePath(current_index)
                if path and os.path.exists(path) and os.path.isdir(path):
                    return path
            
            # If all other methods fail, return the home directory
            return os.path.expanduser("~") 