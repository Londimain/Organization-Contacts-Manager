# popups.py
import os
import webbrowser
from datetime import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QMessageBox, QListWidget,
                               QListWidgetItem, QTextBrowser, QWidget, QProgressDialog, QFileDialog)
from PySide6.QtCore import Qt
from about import ABOUT_TEXT

def _validate_phone(phone):
    if not phone: return True, ''
    if not any(ch.isdigit() for ch in phone):
        return False, 'Телефон должен содержать хотя бы одну цифру'
    return True, ''

def _validate_date(date):
    if not date: return True, ''
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
        try:
            datetime.strptime(date, fmt)
            return True, ''
        except ValueError:
            continue
    return False, 'Формат: ДД.ММ.ГГГГ или ГГГГ-ММ-ДД'

class FormDialog(QDialog):
    def __init__(self, title, fields, validators=None, initial=None):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(400, 100 + len(fields) * 60)
        self.validators = validators or {}
        self.inputs = {}
        
        layout = QVBoxLayout(self)
        self.error_labels = {}

        for key, label_text in fields:
            layout.addWidget(QLabel(label_text))
            inp = QLineEdit()
            if initial:
                try:
                    val = initial[key]
                    if val is not None: inp.setText(str(val))
                except (KeyError, IndexError): pass
            self.inputs[key] = inp
            layout.addWidget(inp)

            err_lbl = QLabel("")
            err_lbl.setStyleSheet("color: #ff9a47;")
            self.error_labels[key] = err_lbl
            layout.addWidget(err_lbl)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.validate_and_accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def validate_and_accept(self):
        data = {k: v.text().strip() for k, v in self.inputs.items()}
        ok = True
        for key, validator in self.validators.items():
            res = validator(data.get(key, ''))
            if isinstance(res, tuple):
                valid, msg = res
            else:
                valid, msg = res, ''
            self.error_labels[key].setText(msg)
            if not valid:
                ok = False
        
        if ok:
            self.accept()

    def get_data(self):
        return {k: v.text().strip() for k, v in self.inputs.items()}

class ConfirmDialog(QDialog):
    def __init__(self, text, yes_text="Удалить"):
        super().__init__()
        self.setWindowTitle("Подтверждение")
        self.resize(350, 120)
        layout = QVBoxLayout(self)
        
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        btn_layout = QHBoxLayout()
        btn_yes = QPushButton(yes_text)
        btn_yes.clicked.connect(self.accept)
        btn_no = QPushButton("Отмена")
        btn_no.clicked.connect(self.reject)
        btn_layout.addWidget(btn_yes)
        btn_layout.addWidget(btn_no)
        layout.addLayout(btn_layout)

class ContactTypeDialog(QDialog):
    def __init__(self, current_type=None):
        super().__init__()
        self.setWindowTitle("Тип контакта")
        self.resize(300, 100)
        self.choice = None
        
        layout = QHBoxLayout(self)
        if current_type != 'decision_maker':
            btn_lpr = QPushButton("ЛПР")
            btn_lpr.clicked.connect(lambda: self.set_choice('decision_maker'))
            layout.addWidget(btn_lpr)
        
        if current_type != 'payment':
            btn_pay = QPushButton("Оплата")
            btn_pay.clicked.connect(lambda: self.set_choice('payment'))
            layout.addWidget(btn_pay)
            
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel)

    def set_choice(self, t):
        self.choice = t
        self.accept()

    def get_choice(self):
        return self.choice

class AboutDialog(QDialog):
    def __init__(self, repo_url):
        super().__init__()
        self.setWindowTitle("О программе")
        # ИСПРАВЛЕНИЕ: Увеличили ширину с 600 до 850 и высоту с 500 до 650
        self.resize(850, 650) 
        self.repo_url = repo_url
        
        layout = QVBoxLayout(self)
        text = QTextBrowser()
        text.setText(ABOUT_TEXT)
        layout.addWidget(text)

        btn_layout = QHBoxLayout()
        btn_repo = QPushButton("Перейти в репозиторий")
        btn_repo.clicked.connect(lambda: webbrowser.open(self.repo_url))
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_repo)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

# ИСПРАВЛЕНИЕ: Переписали InfoDialog с QMessageBox на QDialog для центрирования кнопки и смены текста
class InfoDialog(QDialog):
    def __init__(self, title, text):
        super().__init__()
        self.setWindowTitle(title)
        self.setMinimumWidth(350)
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Понятно")
        btn_ok.setFixedWidth(120)
        btn_ok.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

class LoadingDialog(QDialog):
    def __init__(self, text="Пожалуйста, подождите..."):
        super().__init__()
        self.setWindowTitle("Загрузка")
        self.setFixedSize(300, 100)
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        layout = QVBoxLayout(self)
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

class TrashDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Корзина")
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        # Привязываем событие изменения выделения для управления кнопкой "Восстановить"
        self.list_widget.itemSelectionChanged.connect(self.update_buttons)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        
        # ИСПРАВЛЕНИЕ: Сохраняем кнопки как атрибуты класса (self.), чтобы иметь к ним доступ
        self.btn_restore = QPushButton("Восстановить выбранные")
        self.btn_restore.clicked.connect(self.restore)
        
        self.btn_purge = QPushButton("Очистить корзину")
        self.btn_purge.clicked.connect(self.purge_all)
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_restore)
        btn_layout.addWidget(self.btn_purge)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        self.populate()

    def populate(self):
        self.list_widget.clear()
        items = self.db.get_deleted_items()
        type_names = {'rp': 'Ответственный', 'org': 'Организация', 'store': 'Магазин', 'contact': 'Контакт'}
        for ntype, db_id, name, deleted_at in items:
            text = f"[{type_names[ntype]}] {name}  ({deleted_at})"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, (ntype, db_id))
            self.list_widget.addItem(item)
            
        self.update_buttons()

    # ИСПРАВЛЕНИЕ: Новый метод для управления активностью кнопок
    def update_buttons(self):
        has_items = self.list_widget.count() > 0
        has_selection = len(self.list_widget.selectedItems()) > 0
        
        # "Очистить" активна, только если есть хоть один элемент
        self.btn_purge.setEnabled(has_items)
        
        # "Восстановить" активна, только если выбран хотя бы один элемент
        self.btn_restore.setEnabled(has_selection)

    def restore(self):
        for item in self.list_widget.selectedItems():
            ntype, db_id = item.data(Qt.UserRole)
            self.db.restore_item(ntype, db_id)
        self.populate()

    def purge_all(self):
        self.db.purge_all_deleted()
        self.populate()

class SettingsDialog(QDialog):
    def __init__(self, parent, current_path):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.resize(500, 150)
        self.current_path = current_path
        
        layout = QVBoxLayout(self)

        lbl_info = QLabel("Путь к файлу базы данных (contacts.db):")
        lbl_info.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(lbl_info)

        self.path_input = QLineEdit()
        
        # Импортируем функцию для проверки локального пути
        from settings import app_dir
        local_db = os.path.join(app_dir(), 'contacts.db')
        
        # Если текущий путь совпадает с локальным, показываем пустое поле
        if os.path.abspath(self.current_path) == os.path.abspath(local_db):
            self.path_input.setText("")
            self.path_input.setPlaceholderText("Локальная база (по умолчанию)")
        else:
            self.path_input.setText(self.current_path)
            
        layout.addWidget(self.path_input)

        path_btns = QHBoxLayout()
        btn_browse = QPushButton("Обзор...")
        btn_browse.clicked.connect(self.browse_db)
        btn_local = QPushButton("Использовать локальную")
        btn_local.clicked.connect(self.use_local)
        path_btns.addWidget(btn_browse)
        path_btns.addWidget(btn_local)
        layout.addLayout(path_btns)

        action_btns = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        action_btns.addStretch()
        action_btns.addWidget(btn_save)
        action_btns.addWidget(btn_cancel)
        layout.addLayout(action_btns)

    def browse_db(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, 
            "Выберите файл базы данных (contacts.db) или укажите путь для создания", 
            "",
            "SQLite DB (*.db)",
            options=QFileDialog.DontConfirmOverwrite
        )
        if filepath:
            if not filepath.lower().endswith('.db'):
                filepath += '.db'
            self.path_input.setText(filepath)

    def use_local(self):
        self.path_input.setText("")

    def get_path(self):
        return self.path_input.text().strip()