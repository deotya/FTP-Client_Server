"""
Module for the file system model
"""

from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant
from PyQt5.QtGui import QIcon, QColor
import os
import datetime

class FileSystemModel(QAbstractTableModel):
    """
    Custom model for displaying and managing files and directories.
    Can be used for both local and FTP systems.
    """
    
    COLUMNS = ["Name", "Size", "Type", "Modified"]
    
    def __init__(self, parent=None):
        super(FileSystemModel, self).__init__(parent)
        self.files_data = []
        self.show_hidden = False
        
    def clear(self):
        """Clears all data from the model"""
        self.beginResetModel()
        self.files_data = []
        self.endResetModel()
        
    def update_data(self, files_data):
        """Updates the model data with the new list of files"""
        self.beginResetModel()
        self.files_data = files_data
        self.endResetModel()
        
    def rowCount(self, parent=None):
        return len(self.files_data)
        
    def columnCount(self, parent=None):
        return len(self.COLUMNS)
        
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.files_data):
            return QVariant()
            
        file_item = self.files_data[index.row()]
        column = index.column()
        
        if role == Qt.DisplayRole:
            if column == 0:  # Name
                return file_item.get('name', '')
            elif column == 1:  # Size
                if file_item.get('type') == 'directory':
                    return '<Directory>'
                size = file_item.get('size', 0)
                try:
                    size = int(size)
                    # Format file size (B, KB, MB, GB)
                    if size < 1024:
                        return f"{size} B"
                    elif size < 1024 * 1024:
                        return f"{size/1024:.1f} KB"
                    elif size < 1024 * 1024 * 1024:
                        return f"{size/(1024*1024):.1f} MB"
                    else:
                        return f"{size/(1024*1024*1024):.1f} GB"
                except:
                    return str(size)
            elif column == 2:  # Type
                return 'Directory' if file_item.get('type') == 'directory' else 'File'
            elif column == 3:  # Modified
                return file_item.get('modified', '')
        
        elif role == Qt.ForegroundRole:
            if file_item.get('type') == 'directory':
                return QColor(Qt.blue)
                
        elif role == Qt.TextAlignmentRole:
            if column == 1:  # Size - right alignment
                return Qt.AlignRight | Qt.AlignVCenter
                
        return QVariant()
        
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.COLUMNS[section]
        return QVariant()
        
    def sort(self, column, order=Qt.AscendingOrder):
        """Sorts the model by the specified column"""
        self.beginResetModel()
        reverse = (order == Qt.DescendingOrder)
        
        # Separate directories to always display them first
        directories = [f for f in self.files_data if f.get('type') == 'directory']
        files = [f for f in self.files_data if f.get('type') != 'directory']
        
        # Sorting function based on column
        if column == 0:  # Name
            directories.sort(key=lambda x: x.get('name', '').lower(), reverse=reverse)
            files.sort(key=lambda x: x.get('name', '').lower(), reverse=reverse)
        elif column == 1:  # Size
            directories.sort(key=lambda x: x.get('name', '').lower(), reverse=reverse)
            files.sort(key=lambda x: int(x.get('size', 0)) if str(x.get('size', 0)).isdigit() else 0, reverse=reverse)
        elif column == 2:  # Type
            directories.sort(key=lambda x: x.get('name', '').lower(), reverse=reverse)
            files.sort(key=lambda x: x.get('name', '').lower(), reverse=reverse)
        elif column == 3:  # Modified
            directories.sort(key=lambda x: x.get('modified', ''), reverse=reverse)
            files.sort(key=lambda x: x.get('modified', ''), reverse=reverse)
            
        # Combine the two lists (directories always first)
        self.files_data = directories + files
        self.endResetModel()
        
    def get_file_at_index(self, index):
        """Returns the file data at the specified index"""
        if index.isValid() and index.row() < len(self.files_data):
            return self.files_data[index.row()]
        return None 