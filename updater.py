# updater.py
import os
import sys
import json
import urllib.request
import subprocess
import tempfile
import shutil
import logging
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTextBrowser, QMessageBox, QApplication)
from PySide6.QtGui import QFont

from version import APP_VERSION
from settings import DB_PATH

log = logging.getLogger('updater')

def get_update_url():
    """Возвращает путь к version.json в той же папке, где лежит база данных."""
    try:
        net_dir = os.path.dirname(DB_PATH)
        return os.path.join(net_dir, "version.json")
    except Exception:
        return ""

def _parse_version(v_str):
    """Превращает '1.2.9' в [1, 2, 9] для сравнения"""
    try:
        return [int(x) for x in v_str.strip().split('.')]
    except Exception:
        return [0, 0, 0]

class UpdateCheckThread(QThread):
    update_available = Signal(str, str, str) # latest_ver, download_url, notes

    def __init__(self, update_url):
        super().__init__()
        self.update_url = update_url

    def run(self):
        try:
            if self.update_url.startswith("http"):
                req = urllib.request.Request(self.update_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
            else:
                with open(self.update_url, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            latest_ver = data.get("latest_version")
            download_url = data.get("download_url")
            notes = data.get("release_notes", "Нет описания.")

            if not latest_ver or not download_url:
                return

            # Защита от ошибки, если download_url указывает на json
            if str(download_url).endswith('.json') or not str(download_url).strip():
                download_url = f"ManagerContacts_Setup_v{latest_ver}.exe"

            current_ver = _parse_version(APP_VERSION)
            new_ver = _parse_version(latest_ver)

            if new_ver > current_ver:
                self.update_available.emit(latest_ver, download_url, notes)
                
        except Exception as e:
            log.error(f"Ошибка проверки обновлений: {e}")

class UpdateDownloadThread(QThread):
    finished = Signal(str) # setup_path
    error = Signal(str)

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            actual_url = self.download_url
            
            # Если путь относительный, ищем его рядом с базой
            if not actual_url.startswith("http") and not os.path.isabs(actual_url):
                base_dir = os.path.dirname(DB_PATH)
                actual_url = os.path.join(base_dir, actual_url)

            # Скачиваем во временную папку
            temp_dir = tempfile.gettempdir()
            local_setup_path = os.path.join(temp_dir, "ManagerContacts_Setup_Update.exe")

            if actual_url.startswith("http"):
                urllib.request.urlretrieve(actual_url, local_setup_path)
            else:
                if not os.path.exists(actual_url):
                    raise FileNotFoundError(f"Файл обновления не найден: {actual_url}")
                shutil.copy2(actual_url, local_setup_path)

            self.finished.emit(local_setup_path)
        except Exception as e:
            self.error.emit(str(e))

def check_for_updates(parent_window):
    """Вызывается при старте приложения"""
    update_url = get_update_url()
    
    if not update_url or not os.path.exists(update_url):
        # Файл не найден, выходим молча (нет сети или локальный режим)
        return

    # Сохраняем ссылку на поток, чтобы он не удалился сборщиком мусора
    parent_window._update_thread = UpdateCheckThread(update_url)
    
    def on_update_available(latest_ver, download_url, notes):
        dlg = UpdateDialog(parent_window, latest_ver, download_url, notes)
        dlg.exec()

    parent_window._update_thread.update_available.connect(on_update_available)
    parent_window._update_thread.start()


class UpdateDialog(QDialog):
    def __init__(self, parent, new_version, download_url, notes):
        super().__init__(parent)
        self.setWindowTitle("Доступно обновление")
        self.resize(500, 400)
        self.download_url = download_url
        
        layout = QVBoxLayout(self)

        # Заголовок
        lbl_title = QLabel(f"Доступна новая версия программы: {new_version}\nТекущая версия: {APP_VERSION}")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        lbl_title.setFont(font)
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        # Подзаголовок
        lbl_notes = QLabel("Что нового в этой версии:")
        lbl_notes.setStyleSheet("color: #ffaa55; font-weight: bold;")
        layout.addWidget(lbl_notes)

        # Текст изменений
        text_notes = QTextBrowser()
        text_notes.setText(notes if notes and notes.strip() else "Описание изменений не предоставлено.")
        layout.addWidget(text_notes)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_update = QPushButton("Обновить сейчас")
        self.btn_update.clicked.connect(self.do_update)
        
        btn_later = QPushButton("Напомнить позже")
        btn_later.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_update)
        btn_layout.addWidget(btn_later)
        layout.addLayout(btn_layout)

    def do_update(self):
        self.btn_update.setEnabled(False)
        self.btn_update.setText("Загрузка...")
        
        self.download_thread = UpdateDownloadThread(self.download_url)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.error.connect(self.on_download_error)
        self.download_thread.start()

    def on_download_finished(self, setup_path):
        try:
            # Запускаем установщик с ключом /SILENT (без участия пользователя)
            subprocess.Popen([setup_path, '/SILENT', '/CLOSEAPPLICATIONS', '/RESTARTAPPLICATIONS'])
            QApplication.quit() # Закрываем текущее приложение, чтобы установщик мог перезаписать файлы
        except Exception as e:
            self.on_download_error(f"Не удалось запустить установщик: {e}")

    def on_download_error(self, err_msg):
        QMessageBox.critical(self, "Ошибка обновления", f"Произошла ошибка:\n{err_msg}")
        self.btn_update.setEnabled(True)
        self.btn_update.setText("Обновить сейчас")