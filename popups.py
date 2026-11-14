# popups.py
import os
import webbrowser
from datetime import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QMessageBox, QListWidget,
                               QListWidgetItem, QTextBrowser, QWidget, QProgressDialog, QFileDialog)
from PySide6.QtCore import Qt, QTimer
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
        self.resize(850, 650) 
        self.repo_url = repo_url
        
        layout = QVBoxLayout(self)
        text = QTextBrowser()
        
        # --- ДОБАВИТЬ ЭТУ СТРОКУ ---
        text.setOpenExternalLinks(True) 
        # ----------------------------
        
        text.setText(ABOUT_TEXT)
        # Убираем рамку у текстового поля, чтобы оно сливалось с фоном
        text.setStyleSheet("QTextBrowser { background-color: #121212; border: none; }") 
        layout.addWidget(text)

        btn_layout = QHBoxLayout()
        btn_repo = QPushButton("Перейти в репозиторий")
        btn_repo.clicked.connect(lambda: webbrowser.open(self.repo_url))
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_repo)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

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

class ErrorDialog(QDialog):
    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(350)
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("ОК")
        btn_ok.setFixedWidth(120)
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
# --- ВОЗВРАЩАЕМ КЛАСС ЗАГРУЗКИ ---
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
        self.list_widget.itemSelectionChanged.connect(self.update_buttons)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        
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

    def update_buttons(self):
        has_items = self.list_widget.count() > 0
        has_selection = len(self.list_widget.selectedItems()) > 0
        self.btn_purge.setEnabled(has_items)
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
        
        # --- НОВОЕ: Отступ между полем ввода и кнопками ---
        layout.addSpacing(15) 
        # --------------------------------------------------
        
        from settings import app_dir
        local_db = os.path.join(app_dir(), 'contacts.db')
        
        if os.path.abspath(self.current_path) == os.path.abspath(local_db):
            self.path_input.setText("")
            self.path_input.setPlaceholderText("Локальная база (по умолчанию)")
        else:
            self.path_input.setText(self.current_path)

        layout.addWidget(self.path_input)
        
        # --- НОВОЕ: Отступ между полем ввода и кнопками ---
        layout.addSpacing(15) 
        # --------------------------------------------------

        path_btns = QHBoxLayout()
        btn_browse = QPushButton("Обзор...")
        btn_browse.clicked.connect(self.browse_db)
        btn_local = QPushButton("Использовать локальную")
        btn_local.clicked.connect(self.use_local)
        path_btns.addWidget(btn_browse)
        path_btns.addWidget(btn_local)
        layout.addLayout(path_btns)

        # --- НОВОЕ: Небольшой отступ между рядами кнопок для красоты ---
        layout.addSpacing(10) 
        # --------------------------------------------------------------

        action_btns = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        
        # Делаем кнопки одинаковой ширины
        action_btns.addStretch(1)               # Небольшой отступ слева
        action_btns.addWidget(btn_save, 1)      # Ширина 1
        action_btns.addSpacing(5)              # Отступ между кнопками
        action_btns.addWidget(btn_cancel, 1)    # Ширина 1 (теперь такая же)
        action_btns.addStretch(1)               # Небольшой отступ справа
        
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
    
class LoginDialog(QDialog):
    def __init__(self, correct_password):
        super().__init__()
        self.correct_password = correct_password
        self.setWindowTitle("Вход в программу")
        self.setFixedSize(300, 170)  # <--- Увеличили высоту с 150 до 170
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15) # Немного сузим поля по краям
        
        lbl = QLabel("Введите пароль для доступа:")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.Password)
        self.pwd_input.returnPressed.connect(self.check_password)
        layout.addWidget(self.pwd_input)
        
        # --- НОВОЕ: Отступ между полем ввода и кнопками ---
        layout.addSpacing(20) 
        # -------------------------------------------------
        
        btn_layout = QHBoxLayout()
        
        self.btn_ok = QPushButton("Войти")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self.check_password)
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setAutoDefault(False)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        self.pwd_input.setFocus()

    def check_password(self):
        if not self.pwd_input.isEnabled():
            return

        if self.pwd_input.text() == self.correct_password:
            self.accept()
        else:
            self.pwd_input.setEnabled(False)
            self.btn_ok.setEnabled(False)
            self.btn_cancel.setEnabled(False)

            ErrorDialog("Ошибка", "Неверный пароль! Попробуйте снова.", self).exec()

            QTimer.singleShot(150, self._reset_ui)
            
    def _reset_ui(self):
        self.pwd_input.setEnabled(True)
        self.btn_ok.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.pwd_input.clear()
        self.pwd_input.setFocus()