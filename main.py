"""
Fisierul principal care pornește aplicația de gestiune a fișierelor
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QCoreApplication

from ftp_client.ui.file_manager_window import FileManager

def main():
    """Funcția principală care pornește aplicația de gestionare a fișierelor"""
    # Setări pentru high DPI
    QCoreApplication.setAttribute(Qt.AA_DisableHighDpiScaling)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # Setăm numărul maxim de thread-uri pentru a evita probleme
    QApplication.setAttribute(Qt.AA_DisableWindowContextHelpButton)
    
    app = QApplication(sys.argv)
    
    # Configurăm aplicația pentru a se asigura că toate thread-urile sunt oprite la închidere
    app.setQuitOnLastWindowClosed(True)
    
    window = FileManager()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 