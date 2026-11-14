# main.py
import sys
import socket
import logging
import os
import ctypes
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtGui import QIcon, QPalette, QColor
from PySide6.QtCore import Qt
from popups import LoginDialog
from updater import check_for_updates

from logger import setup_logging
setup_logging()

log = logging.getLogger('main')
_single_instance_socket = None

def resource_path(relative_path):
    try:
        base = sys._MEIPASS
    except Exception:
        base = os.path.abspath(".")
    return os.path.join(base, relative_path)

def acquire_single_instance_lock():
    global _single_instance_socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 47521))
        sock.listen(1)
        _single_instance_socket = sock
        return True
    except OSError:
        return False

def set_dark_theme(app):
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(18, 18, 18))
    palette.setColor(QPalette.WindowText, QColor(240, 240, 240))
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(35, 35, 35))
    palette.setColor(QPalette.Text, QColor(240, 240, 240))
    palette.setColor(QPalette.Button, QColor(30, 77, 84)) 
    palette.setColor(QPalette.ButtonText, QColor(240, 240, 240))
    palette.setColor(QPalette.Highlight, QColor(56, 77, 107))
    # Меняем чисто белый на приятный светло-серый
    palette.setColor(QPalette.HighlightedText, QColor(240, 240, 240))
    app.setPalette(palette)

if __name__ == '__main__':
    # Установка ID для корректного отображения иконки в панели задач Windows
    try:
        myappid = 'MogNat.ManagerContacts.1.4' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    if not acquire_single_instance_lock():
        log.warning("Another instance is already running")
        sys.exit(0)

    from app import MainWindow
    
    app = QApplication(sys.argv)
    set_dark_theme(app)
    
    app.setStyleSheet("""
        QPushButton {
            background-color: #1e4d54;
            color: #000000; /* <--- ИЗМЕНЕНО НА ЧЕРНЫЙ */
            border: 1px solid #d93f3f;
            padding: 5px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #377f87;
            border: 1px solid #ff6b6b;
        }
        QPushButton:pressed {
            background-color: #123336;
        }
        QPushButton:disabled {
            background-color: #1e1e1e;
            color: #ffffff; /* <--- ИЗМЕНЕНО НА БЕЛЫЙ */
            border: 1px solid #444;
        }
        
        QTreeView {
            outline: none;
            font-size: 14px;
        }
        
        /* ЗАГОЛОВКИ ТАБЛИЦЫ */
        QHeaderView::section {
            background-color: #1e4d54;
            color: #000000; /* <--- ИЗМЕНЕНО НА ЧЕРНЫЙ */
            font-size: 14px;
            font-weight: bold;
            padding: 4px;
            border: 1px solid #d93f3f;
        }
        
        QTreeView::item:hover {
            background-color: transparent;
        }
        
        QTreeView::item:selected {
            background-color: #253445; 
        }

        /* СТИЛИЗАЦИЯ ПОЛОСЫ ПРОКРУТКИ */
        QScrollBar:vertical {
            border: none;
            background: transparent;
            width: 12px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #1e4d54;
            min-height: 20px;
            border: 1px solid #d93f3f;
            border-radius: 2px;
        }
        QScrollBar::handle:vertical:hover {
            background: #377f87;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
            height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
    """)

    icon_path = resource_path('ico/manager.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        
    # --- НОВОЕ: Запрос пароля перед запуском ---
    login_dlg = LoginDialog("soft")
    if login_dlg.exec() != QDialog.Accepted:
        sys.exit(0)  # Если нажали "Отмена" или закрыли окно - выходим
    # -----------------------------------------

    from app import MainWindow
    window = MainWindow()
    window.showMaximized()
    
    check_for_updates(window)
    
    sys.exit(app.exec())