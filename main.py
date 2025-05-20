"""
Fisierul principal care pornește aplicația de gestiune a fișierelor
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QCoreApplication

from ftp_client.ui.file_manager_window import FileManager

def main():
    """The main function that starts the file management application"""
    # Settings for high DPI
    QCoreApplication.setAttribute(Qt.AA_DisableHighDpiScaling)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # Set the maximum number of threads to avoid problems
    QApplication.setAttribute(Qt.AA_DisableWindowContextHelpButton)
    
    app = QApplication(sys.argv)
    
    # Configure the application to ensure all threads are stopped when closing
    app.setQuitOnLastWindowClosed(True)
    
    window = FileManager()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 