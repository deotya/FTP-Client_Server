"""
Local and FTP File Management Application
"""

import sys
import os
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileSystemModel, 
                            QTreeView, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLineEdit, QLabel, QMessageBox,
                            QInputDialog, QMenu, QAction, QFileDialog, QComboBox,
                            QTabWidget, QListWidget, QListWidgetItem, QDialog,
                            QFormLayout, QSpinBox, QCheckBox, QGroupBox)
from PyQt5.QtCore import Qt, QDir, QModelIndex, QCoreApplication
from PyQt5.QtGui import QIcon, QFont

from ftp_client import FTPClient
from ui.file_manager_window import FileManager

# Then before creating the application
QCoreApplication.setAttribute(Qt.AA_DisableHighDpiScaling)
QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

def main():
    """The main function that starts the file management application"""
    app = QApplication(sys.argv)
    window = FileManager()
    window.show()
    sys.exit(app.exec_()) 

if __name__ == '__main__':
    main() 