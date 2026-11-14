# app.py
import os
import sys
import re
import logging
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLineEdit, QLabel, QPushButton, QTreeView, QHeaderView,
                               QMessageBox, QFileDialog, QApplication, QAbstractItemView,
                               QStyledItemDelegate, QStyle, QStyleOptionViewItem, QSizePolicy)
from PySide6.QtGui import (QStandardItemModel, QStandardItem, QAction, QShortcut, 
                           QKeySequence, QIcon, QColor, QBrush, QFont, QPalette)
from PySide6.QtCore import (Qt, QSortFilterProxyModel, QModelIndex, QEvent, 
                            QTimer, QThread, Signal, QItemSelectionModel)

from version import WINDOW_TITLE, REPO_URL
from settings import DB_PATH, load_settings, save_settings, app_dir
from database import Database
from popups import (FormDialog, ConfirmDialog, ContactTypeDialog, AboutDialog,
                    InfoDialog, TrashDialog, LoadingDialog, SettingsDialog)
from export import export_to_excel, import_from_excel, get_desktop_path

log = logging.getLogger('app')

# ==============================================================================
# ЦВЕТОВАЯ СХЕМА ИНТЕРФЕЙСА
# ==============================================================================
C_RP_TEXT      = "#6D015F"
C_ORG_TEXT     = "#ffaa55"
C_STORE_TEXT   = "#458a00"
C_CONTACT_TEXT = "#aaaaaa"
C_HEADER_TEXT  = "#55aaff"

class KeepColorDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        
        fg_brush = index.data(Qt.ForegroundRole)
        if (opt.state & QStyle.State_Selected) and fg_brush:
            if hasattr(fg_brush, 'color'):
                opt.palette.setColor(QPalette.HighlightedText, fg_brush.color())
            else:
                opt.palette.setColor(QPalette.HighlightedText, fg_brush)
        
        super().paint(painter, opt, index)

def resource_path(relative_path):
    try:
        base = sys._MEIPASS
    except Exception:
        base = os.path.abspath(".")
    return os.path.join(base, relative_path)

def _phone_validator(phone):
    if not phone: return True, ''
    if not any(ch.isdigit() for ch in phone):
        return False, 'Должна быть хотя бы одна цифра'
    return True, ''

def _date_validator(date):
    if not date: return True, ''
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
        try:
            datetime.strptime(date, fmt)
            return True, ''
        except ValueError:
            continue
    return False, 'Формат: ДД.ММ.ГГГГ'

class SwitchDbThread(QThread):
    finished_signal = Signal(object)
    error_signal = Signal(str)

    def __init__(self, new_path):
        super().__init__()
        self.new_path = new_path

    def run(self):
        try:
            new_db = Database(self.new_path)
            new_db.connect() 
            self.finished_signal.emit(new_db)
        except Exception as e:
            self.error_signal.emit(str(e))

class LoadDataThread(QThread):
    finished_signal = Signal(object) # object для безопасной передачи списка
    error_signal = Signal(str)

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        try:
            tree_data = []
            for rp in self.db.get_responsible_persons():
                rp_node = {'rp': rp, 'orgs': []}
                for org in self.db.get_organizations(rp['id']):
                    org_node = {'org': org, 'stores': []}
                    for st in self.db.get_stores(org['id']):
                        st_node = {
                            'store': st,
                            'dm': self.db.get_contacts(st['id'], 'decision_maker'),
                            'pay': self.db.get_contacts(st['id'], 'payment')
                        }
                        org_node['stores'].append(st_node)
                    rp_node['orgs'].append(org_node)
                tree_data.append(rp_node)
            self.finished_signal.emit(tree_data)
        except Exception as e:
            self.error_signal.emit(str(e))

class ExportThread(QThread):
    finished_signal = Signal(str) # Возвращает путь к сохраненному файлу
    error_signal = Signal(str)

    def __init__(self, db, filepath):
        super().__init__()
        self.db = db
        self.filepath = filepath

    def run(self):
        try:
            path = export_to_excel(self.db, filepath=self.filepath)
            self.finished_signal.emit(path)
        except Exception as e:
            self.error_signal.emit(str(e))
                             
class ImportThread(QThread):
    finished_signal = Signal(int, int, int)
    error_signal = Signal(str)

    def __init__(self, db, filepath):
        super().__init__()
        self.db = db
        self.filepath = filepath

    def run(self):
        try:
            added, updated, skipped = import_from_excel(self.db, self.filepath)
            self.finished_signal.emit(added, updated, skipped)
        except Exception as e:
            self.error_signal.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1400, 900)
        
        self.is_searching = False
        self.saved_expanded_nodes = set()
        
        icon_path = resource_path('ico/manager.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.db = Database(DB_PATH)
        self.db.connect()

        self.setup_ui()
        self.refresh_view()
        self.setup_shortcuts()
        
        # --- НОВОЕ: Таймер для проверки обновлений с других ПК ---
        self.last_db_mtime = self._get_db_mtime()
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.check_for_external_changes)
        self.auto_refresh_timer.start(10000) # Проверка каждые 10 секунд (10 000 мс)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # --- Верхняя панель ---
        top_layout = QHBoxLayout()
        
        lbl_search = QLabel("Поиск:")
        lbl_search.setStyleSheet("font-size: 16px;")
        top_layout.addWidget(lbl_search)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по всей базе... (Ctrl+F)")
        self.search_input.setStyleSheet("font-size: 16px; padding: 4px;")
        self.search_input.textChanged.connect(self.on_search)
        top_layout.addWidget(self.search_input)

        btn_settings = QPushButton("Настройки")
        btn_settings.clicked.connect(self.show_settings)

        btn_trash = QPushButton("Корзина")
        btn_trash.clicked.connect(self.show_trash)
        btn_about = QPushButton("О программе")
        btn_about.clicked.connect(self.show_about)
        btn_exit = QPushButton("Выход")
        btn_exit.clicked.connect(self.close)

        for b in (btn_settings, btn_trash, btn_about, btn_exit): 
            b.setFixedWidth(120)
            top_layout.addWidget(b)

        layout.addLayout(top_layout)

        # --- Таблица (Дерево) ---
        self.tree = QTreeView()
        self.model = QStandardItemModel()
        
        self.tree.setItemDelegate(KeepColorDelegate(self.tree))
        
        self.model.setHorizontalHeaderLabels([
            "Тип", "Наименование / ФИО", "Город / Договор", "Дата договора", "Адрес / Должность", "№ телефона"
        ])
        
        for i in range(self.model.columnCount()):
            self.model.setHeaderData(i, Qt.Horizontal, Qt.AlignCenter, Qt.TextAlignmentRole)
        
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setRecursiveFilteringEnabled(True)
        self.proxy_model.setFilterKeyColumn(-1)

        self.tree.setModel(self.proxy_model)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setSortingEnabled(True)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree.setMouseTracking(True)
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.setTextElideMode(Qt.ElideNone)
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        self.tree.clicked.connect(self.on_tree_clicked)
        self.tree.doubleClicked.connect(self.copy_cell_text)
        self.tree.viewport().installEventFilter(self)

        header = self.tree.header()
        header.setStretchLastSection(False)
        
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.tree.selectionModel().selectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.tree)

        # --- Панель с кнопками действий ---
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Добавить")
        self.btn_edit = QPushButton("Редактировать")
        self.btn_delete = QPushButton("Удалить")
        self.btn_change_type = QPushButton("Сменить тип")
        self.btn_export = QPushButton("Экспорт в Excel")
        self.btn_import = QPushButton("Импорт из Excel")

        self.btn_add.clicked.connect(self.on_add)
        self.btn_edit.clicked.connect(self.on_edit)
        self.btn_delete.clicked.connect(self.on_delete)
        self.btn_change_type.clicked.connect(self.on_change_type)
        self.btn_export.clicked.connect(self.export_data)
        self.btn_import.clicked.connect(self.import_data)

        for b in (self.btn_add, self.btn_edit, self.btn_delete,
                  self.btn_change_type, self.btn_export, self.btn_import):
            btn_layout.addWidget(b)
        layout.addLayout(btn_layout)

        # --- Нижняя панель ---
        bottom_layout = QHBoxLayout()
        
        btn_collapse = QPushButton("Свернуть всё")
        btn_collapse.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_collapse.clicked.connect(self.collapse_all)
        # Коэффициент 5 делает кнопку очень широкой
        bottom_layout.addWidget(btn_collapse, 5)

        self.status_label = QLabel("")
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom_layout.addWidget(self.status_label, 3)

        self.db_status_label = QLabel("")
        self.db_status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.db_status_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        bottom_layout.addWidget(self.db_status_label)
        
        layout.addLayout(bottom_layout)

    def eventFilter(self, source, event):
        if source is self.tree.viewport():
            if event.type() in (QEvent.MouseButtonPress, QEvent.ContextMenu):
                if event.type() == QEvent.ContextMenu or event.button() == Qt.RightButton:
                    self.tree.clearSelection()
                    self.tree.setCurrentIndex(QModelIndex())
                    return True
                
                elif event.button() == Qt.LeftButton:
                    index = self.tree.indexAt(event.pos())
                    if not index.isValid():
                        self.tree.clearSelection()
                        self.tree.setCurrentIndex(QModelIndex())
                        return True
                        
        return super().eventFilter(source, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(10, self.force_stretch_columns)

    def force_stretch_columns(self):
        if self.model.columnCount() == 0: return
        
        header = self.tree.header()
        for i in range(self.model.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
            
        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(2)
        self.tree.resizeColumnToContents(3)
        self.tree.resizeColumnToContents(5)
        
        fm = self.tree.fontMetrics()
        max_text_w = max(fm.horizontalAdvance("Ответственный"), fm.horizontalAdvance("Организация"))
        min_w0 = max_text_w + (self.tree.indentation() * 3) + 20
        
        w0 = self.tree.columnWidth(0)
        if w0 < min_w0:
            w0 = min_w0
            self.tree.setColumnWidth(0, w0)
            
        w2 = self.tree.columnWidth(2)
        w3 = self.tree.columnWidth(3)
        w5 = self.tree.columnWidth(5)
        
        viewport_width = self.tree.viewport().width() - 20
        remaining = viewport_width - w0 - w2 - w3 - w5
        
        if remaining > 200:
            w1 = int(remaining * 0.55)
            w4 = remaining - w1 
            self.tree.setColumnWidth(1, w1)
            self.tree.setColumnWidth(4, w4)
        else:
            self.tree.setColumnWidth(1, 250)
            self.tree.setColumnWidth(4, 150)

    def on_tree_clicked(self, proxy_index):
        if not proxy_index.isValid(): return
            
        modifiers = QApplication.keyboardModifiers()
        if modifiers in (Qt.ControlModifier, Qt.ShiftModifier): 
            return
            
        idx0 = self.proxy_model.index(proxy_index.row(), 0, proxy_index.parent())
        
        if self.proxy_model.rowCount(idx0) > 0:
            self.tree.setExpanded(idx0, not self.tree.isExpanded(idx0))

    def flash_item(self, item):
        if not item: return
        orig_fg = item.data(Qt.ForegroundRole)
        item.setForeground(QBrush(QColor("#00FF00"))) 
        
        def restore():
            if item:
                item.setData(orig_fg, Qt.ForegroundRole)
                
        QTimer.singleShot(200, restore)

    def copy_cell_text(self, proxy_index):
        if not proxy_index.isValid(): return
        text = self.proxy_model.data(proxy_index)
        if text and text.strip() not in ('-', ''):
            QApplication.clipboard().setText(text)
            self.status_label.setText(f"Скопировано: {text[:30]}...")
            QTimer.singleShot(3000, self.update_status)
            
            src_idx = self.proxy_model.mapToSource(proxy_index)
            item = self.model.itemFromIndex(src_idx)
            self.flash_item(item)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.search_input.setFocus)
        QShortcut(QKeySequence("Insert"), self).activated.connect(self.on_add)
        QShortcut(QKeySequence("Delete"), self).activated.connect(self.on_delete)
        QShortcut(QKeySequence("Enter"), self).activated.connect(self.on_edit)
        QShortcut(QKeySequence("Ctrl+C"), self).activated.connect(self.copy_selected)

    def get_expanded_nodes(self):
        expanded = set()
        def traverse(parent_index):
            for row in range(self.proxy_model.rowCount(parent_index)):
                index = self.proxy_model.index(row, 0, parent_index)
                if self.tree.isExpanded(index):
                    src_index = self.proxy_model.mapToSource(index)
                    item = self.model.itemFromIndex(src_index)
                    data = item.data(Qt.UserRole)
                    if data and data[0] != 'header':
                        expanded.add(data)
                traverse(index)
        traverse(QModelIndex())
        return expanded

    def restore_expanded_nodes(self):
        def traverse(parent_index):
            for row in range(self.proxy_model.rowCount(parent_index)):
                index = self.proxy_model.index(row, 0, parent_index)
                src_index = self.proxy_model.mapToSource(index)
                item = self.model.itemFromIndex(src_index)
                data = item.data(Qt.UserRole)
                if data in self.saved_expanded_nodes:
                    self.tree.expand(index)
                traverse(index)
        traverse(QModelIndex())

    def find_index_by_data(self, data_key):
        def traverse(parent_index):
            for row in range(self.proxy_model.rowCount(parent_index)):
                index = self.proxy_model.index(row, 0, parent_index)
                src_index = self.proxy_model.mapToSource(index)
                item = self.model.itemFromIndex(src_index)
                data = item.data(Qt.UserRole)
                if data == data_key:
                    return index
                res = traverse(index)
                if res: return res
            return None
        return traverse(QModelIndex())

    def _get_item_by_key(self, data_key):
        proxy_idx = self.find_index_by_data(data_key)
        if proxy_idx and proxy_idx.isValid():
            src_idx = self.proxy_model.mapToSource(proxy_idx)
            return self.model.itemFromIndex(src_idx)
        return None

    def _select_item(self, data_key):
        proxy_idx = self.find_index_by_data(data_key)
        if proxy_idx and proxy_idx.isValid():
            parent = proxy_idx.parent()
            while parent.isValid():
                self.tree.expand(parent)
                parent = parent.parent()
            self.tree.setCurrentIndex(proxy_idx)
            self.tree.selectionModel().select(proxy_idx, QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows)
            self.tree.scrollTo(proxy_idx)
            
            src_idx = self.proxy_model.mapToSource(proxy_idx)
            item = self.model.itemFromIndex(src_idx)
            self.flash_item(item)

    def _get_db_mtime(self):
        """Возвращает время последнего изменения файла базы данных."""
        try:
            return os.path.getmtime(self.db.db_name)
        except Exception:
            return 0

    def check_for_external_changes(self):
        """Проверяет, не изменил ли кто-то базу данных на сервере."""
        # Не обновляем, если открыто какое-то диалоговое окно (пользователь что-то вводит)
        if QApplication.activeModalWidget():
            return

        current_mtime = self._get_db_mtime()
        if current_mtime > self.last_db_mtime:
            # База изменилась! Обновляем тихо, без окна загрузки
            self.last_db_mtime = current_mtime
            self.refresh_view(silent=True)
                   
    def refresh_view(self, select_data=None, show_cursor=True, silent=False):
        self._pending_select_data = select_data
        
        # Показываем окно загрузки ТОЛЬКО если это не тихое автообновление
        if not silent:
            if not hasattr(self, 'loading_dlg') or not self.loading_dlg:
                self.loading_dlg = LoadingDialog("Загрузка данных из базы...\nПожалуйста, подождите.")
                self.loading_dlg.setWindowModality(Qt.ApplicationModal) 
                self.loading_dlg.show()

        # Сохраняем текущее состояние (открытые узлы, выделение)
        self.saved_expanded_nodes = self.get_expanded_nodes()
        self._pending_old_sel = self.get_selected_data()

        # Запускаем фоновый поток
        self.load_thread = LoadDataThread(self.db)
        self.load_thread.finished_signal.connect(self.on_data_loaded)
        self.load_thread.error_signal.connect(self.on_data_load_error)
        self.load_thread.start()

    def on_data_loaded(self, tree_data):
        self.tree.setUpdatesEnabled(False)
        try:
            self.model.clear()
            self.model.setHorizontalHeaderLabels([
                "Тип", "Наименование / ФИО", "Город / Договор", "Дата договора", "Адрес / Должность", "№ телефона"
            ])
            for i in range(self.model.columnCount()):
                self.model.setHeaderData(i, Qt.Horizontal, Qt.AlignCenter, Qt.TextAlignmentRole)

            font_hdr = QFont()
            font_hdr.setBold(True)

            for rp_node in tree_data:
                rp = rp_node['rp']
                rp_row = self.make_row(
                    "Ответственный", rp['full_name'], rp['city'] or '-', '', 
                    rp['position'] or '-', rp['phone'] or '-', ('rp', rp['id'])
                )
                self.model.invisibleRootItem().appendRow(rp_row)
                
                for org_node in rp_node['orgs']:
                    org = org_node['org']
                    org_row = self.make_row(
                        "Организация", org['name'], org['contract_number'] or '-',
                        org['contract_date'] or '-', org['address'] or '-', org['phone'] or '-',
                        ('org', org['id'])
                    )
                    rp_row[0].appendRow(org_row)
                    
                    for st_node in org_node['stores']:
                        st = st_node['store']
                        st_row = self.make_row(
                            "Магазин", st['name'], '', '', st['unloading_address'] or '-', st['phone'] or '-',
                            ('store', st['id'])
                        )
                        org_row[0].appendRow(st_row)
                        
                        hdr_dm_type = QStandardItem("")
                        hdr_dm_type.setData(('header', 'decision_maker', st['id']), Qt.UserRole)
                        hdr_dm_name = QStandardItem("Контакты ЛПР")
                        hdr_dm_name.setFont(font_hdr)
                        hdr_dm_name.setForeground(QBrush(QColor(C_HEADER_TEXT)))
                        row_dm = [hdr_dm_type, hdr_dm_name, QStandardItem(""), QStandardItem(""), QStandardItem(""), QStandardItem("")]
                        st_row[0].appendRow(row_dm)
                        
                        for c in st_node['dm']:
                            dm_row = self.make_row("", c['full_name'] or '-', '', '', c['position'] or '-', c['phone'] or '-', ('contact_dm', c['id']))
                            hdr_dm_type.appendRow(dm_row) 
                            
                        hdr_pay_type = QStandardItem("")
                        hdr_pay_type.setData(('header', 'payment', st['id']), Qt.UserRole)
                        hdr_pay_name = QStandardItem("Контакты оплаты")
                        hdr_pay_name.setFont(font_hdr)
                        hdr_pay_name.setForeground(QBrush(QColor(C_HEADER_TEXT)))
                        row_pay = [hdr_pay_type, hdr_pay_name, QStandardItem(""), QStandardItem(""), QStandardItem(""), QStandardItem("")]
                        st_row[0].appendRow(row_pay)
                        
                        for c in st_node['pay']:
                            pay_row = self.make_row("", c['full_name'] or '-', '', '', c['position'] or '-', c['phone'] or '-', ('contact_pay', c['id']))
                            hdr_pay_type.appendRow(pay_row)

            self.force_stretch_columns()
            self.restore_expanded_nodes()
            self.saved_expanded_nodes.clear()
            
            target = self._pending_select_data if self._pending_select_data else self._pending_old_sel
            if target:
                new_idx = self.find_index_by_data(target)
                if new_idx and new_idx.isValid():
                    parent = new_idx.parent()
                    while parent.isValid():
                        self.tree.expand(parent)
                        parent = parent.parent()
                    self.tree.setCurrentIndex(new_idx)
                    self.tree.selectionModel().select(new_idx, QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows)
                    self.tree.scrollTo(new_idx)
                    
        finally:
            self.tree.setUpdatesEnabled(True)
            QTimer.singleShot(50, self.force_stretch_columns) 
            self.update_status()
            
            # Обновляем время последнего изменения, чтобы таймер не срабатывал зря
            self.last_db_mtime = self._get_db_mtime()
            
            if hasattr(self, 'loading_dlg') and self.loading_dlg:
                self.loading_dlg.accept()
                self.loading_dlg = None

    def on_data_load_error(self, error_msg):
        if hasattr(self, 'loading_dlg') and self.loading_dlg:
            self.loading_dlg.accept()
            self.loading_dlg = None
        InfoDialog("Ошибка", f"Не удалось загрузить данные из базы:\n{error_msg}").exec()

    def make_row(self, type_name, name, c2, c3, c4, c5, data_key):
        item_type = QStandardItem(type_name)
        item_name = QStandardItem(name)
        
        brush = QBrush()
        font = QFont()
        
        if data_key[0] == 'rp':
            brush.setColor(QColor(C_RP_TEXT))
            font.setBold(True)
            item_type.setFont(font)
        elif data_key[0] == 'org':
            brush.setColor(QColor(C_ORG_TEXT))
            font.setBold(True)
            item_type.setFont(font)
        elif data_key[0] == 'store':
            brush.setColor(QColor(C_STORE_TEXT))
        elif data_key[0] in ('contact_dm', 'contact_pay'):
            brush.setColor(QColor(C_CONTACT_TEXT))
            
        if brush.color().isValid():
            item_type.setForeground(brush)
        
        items = [
            item_type,
            item_name,
            QStandardItem(c2),
            QStandardItem(c3),
            QStandardItem(c4),
            QStandardItem(c5)
        ]
        items[0].setData(data_key, Qt.UserRole)
        
        return items

    def collapse_all(self):
        self.tree.collapseAll()

    def on_search(self, text):
        if not text:
            if self.is_searching:
                self.is_searching = False
                self.proxy_model.setFilterFixedString("")
                self.tree.collapseAll()
                self.restore_expanded_nodes()
                self.saved_expanded_nodes.clear()
        else:
            if not self.is_searching:
                self.is_searching = True
                self.saved_expanded_nodes = self.get_expanded_nodes()
            
            self.proxy_model.setFilterFixedString(text)
            self.tree.expandAll()

    def update_status(self):
        c = self.db.get_counts()
        self.status_label.setText(
            f"Ответственных: {c['rp']}  |  Организаций: {c['org']}  |  "
            f"Магазинов: {c['store']}  |  Контактов: {c['contact']}"
        )

        local_db_path = os.path.abspath(os.path.join(app_dir(), 'contacts.db'))
        current_db_path = os.path.abspath(self.db.db_name)

        if current_db_path == local_db_path:
            self.db_status_label.setText("💾 База: Локальная")
            self.db_status_label.setStyleSheet("color: #55aaff; font-size: 14px; font-weight: bold;")
            self.db_status_label.setToolTip(current_db_path)
        else:
            self.db_status_label.setText("🌐 База: Сетевая")
            self.db_status_label.setStyleSheet("color: #458a00; font-size: 14px; font-weight: bold;")
            self.db_status_label.setToolTip(current_db_path) 

    def get_selected_data(self):
        indexes = self.tree.selectionModel().selectedRows()
        if not indexes: return None
        source_idx = self.proxy_model.mapToSource(indexes[0])
        item = self.model.itemFromIndex(source_idx)
        return item.data(Qt.UserRole)

    def on_selection_changed(self, selected, deselected):
        data = self.get_selected_data()
        has_sel = len(self.tree.selectionModel().selectedRows()) > 0
        
        if not data:
            self.btn_add.setEnabled(True)
            self.btn_add.setText("Добавить ответственного")
            self.btn_edit.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.btn_change_type.setEnabled(False)
            return

        ntype = data[0]
        is_contact = ntype in ('contact_dm', 'contact_pay')
        is_header = ntype == 'header'
        
        self.btn_delete.setEnabled(has_sel and not is_header)
        self.btn_edit.setEnabled(len(self.tree.selectionModel().selectedRows()) == 1 and not is_header)
        self.btn_change_type.setEnabled(is_contact)
        
        if is_contact:
            self.btn_add.setEnabled(False)
            self.btn_add.setText("Добавить")
        elif is_header:
            self.btn_add.setEnabled(True)
            self.btn_add.setText("Добавить контакт")
        elif ntype == 'store':
            self.btn_add.setEnabled(True)
            self.btn_add.setText("Добавить контакт")
        else:
            self.btn_add.setEnabled(True)
            if ntype == 'rp': self.btn_add.setText("Добавить организацию")
            elif ntype == 'org': self.btn_add.setText("Добавить магазин")

    def copy_selected(self):
        indexes = self.tree.selectionModel().selectedRows()
        if not indexes: return
        lines = []
        for idx in indexes:
            row_data = []
            for col in range(6):
                col_idx = self.proxy_model.index(idx.row(), col, idx.parent())
                row_data.append(col_idx.data(Qt.DisplayRole))
                
                src_idx = self.proxy_model.mapToSource(col_idx)
                item = self.model.itemFromIndex(src_idx)
                self.flash_item(item)
                
            lines.append("\t".join(row_data))
        
        QApplication.clipboard().setText("\r\n".join(lines))
        self.status_label.setText(f"Скопировано строк: {len(indexes)}")
        QTimer.singleShot(3000, self.update_status)

    def on_add(self):
        data = self.get_selected_data()
        if not data: 
            self._add_rp()
        elif data[0] == 'rp': 
            self._add_org(data[1])
        elif data[0] == 'org': 
            self._add_store(data[1])
        elif data[0] == 'store': 
            self._add_contact(data[1])
        elif data[0] == 'header':
            self._add_contact(data[2], data[1])

    def _add_rp(self):
        dlg = FormDialog("Новое ответственное лицо", [('full_name', 'ФИО'), ('city', 'Город'), ('position', 'Должность'), ('phone', 'Телефон')], {'phone': _phone_validator})
        if dlg.exec():
            d = dlg.get_data()
            if d['full_name']:
                new_id = self.db.add_responsible_person(d['full_name'], d['city'], d['position'], d['phone'])
                new_row = self.make_row("Ответственный", d['full_name'], d['city'] or '-', '', d['position'] or '-', d['phone'] or '-', ('rp', new_id))
                self.model.invisibleRootItem().appendRow(new_row)
                self._select_item(('rp', new_id))
                self.update_status()

    def _add_org(self, rp_id):
        dlg = FormDialog("Новая организация", [('name', 'Название'), ('contract_number', '№ договора'), ('contract_date', 'Дата договора'), ('address', 'Адрес'), ('phone', 'Телефон')], {'phone': _phone_validator, 'contract_date': _date_validator})
        if dlg.exec():
            d = dlg.get_data()
            if d['name']:
                new_id = self.db.add_organization(rp_id, d['name'], d['address'], d['phone'], d['contract_number'], d['contract_date'])
                new_row = self.make_row("Организация", d['name'], d['contract_number'] or '-', d['contract_date'] or '-', d['address'] or '-', d['phone'] or '-', ('org', new_id))
                rp_item = self._get_item_by_key(('rp', rp_id))
                if rp_item:
                    rp_item.appendRow(new_row)
                    self._select_item(('org', new_id))
                    self.update_status()

    def _add_store(self, org_id):
        dlg = FormDialog("Новый магазин", [('name', 'Название'), ('address', 'Адрес разгрузки'), ('phone', 'Телефон')], {'phone': _phone_validator})
        if dlg.exec():
            d = dlg.get_data()
            if d['name']:
                new_id = self.db.add_store(org_id, d['name'], d['address'], d['phone'])
                new_row = self.make_row("Магазин", d['name'], '', '', d['address'] or '-', d['phone'] or '-', ('store', new_id))
                org_item = self._get_item_by_key(('org', org_id))
                if org_item:
                    org_item.appendRow(new_row)
                    
                    # Сразу создаем заголовки для контактов нового магазина
                    font_hdr = QFont()
                    font_hdr.setBold(True)
                    
                    hdr_dm_type = QStandardItem("")
                    hdr_dm_type.setData(('header', 'decision_maker', new_id), Qt.UserRole)
                    hdr_dm_name = QStandardItem("Контакты ЛПР")
                    hdr_dm_name.setFont(font_hdr)
                    hdr_dm_name.setForeground(QBrush(QColor(C_HEADER_TEXT)))
                    row_dm = [hdr_dm_type, hdr_dm_name, QStandardItem(""), QStandardItem(""), QStandardItem(""), QStandardItem("")]
                    new_row[0].appendRow(row_dm)
                    
                    hdr_pay_type = QStandardItem("")
                    hdr_pay_type.setData(('header', 'payment', new_id), Qt.UserRole)
                    hdr_pay_name = QStandardItem("Контакты оплаты")
                    hdr_pay_name.setFont(font_hdr)
                    hdr_pay_name.setForeground(QBrush(QColor(C_HEADER_TEXT)))
                    row_pay = [hdr_pay_type, hdr_pay_name, QStandardItem(""), QStandardItem(""), QStandardItem(""), QStandardItem("")]
                    new_row[0].appendRow(row_pay)
                    
                    self._select_item(('store', new_id))
                    self.update_status()

    def _add_contact(self, store_id, preset_type=None):
        if preset_type:
            ctype = preset_type
        else:
            dlg = ContactTypeDialog()
            if dlg.exec() and dlg.get_choice():
                ctype = dlg.get_choice()
            else:
                return

        title = 'ЛПР' if ctype == 'decision_maker' else 'Оплата'
        f_dlg = FormDialog(f"Новый контакт ({title})", [('full_name', 'ФИО'), ('position', 'Должность'), ('phone', 'Телефон')], {'phone': _phone_validator})
        
        if f_dlg.exec():
            d = f_dlg.get_data()
            if d['full_name']:
                new_id = self.db.add_contact(store_id, ctype, d['full_name'], d['position'], d['phone'])
                prefix = 'contact_dm' if ctype == 'decision_maker' else 'contact_pay'
                new_row = self.make_row("", d['full_name'], '', '', d['position'] or '-', d['phone'] or '-', (prefix, new_id))
                hdr_item = self._get_item_by_key(('header', ctype, store_id))
                if hdr_item:
                    hdr_item.appendRow(new_row)
                    self._select_item((prefix, new_id))
                    self.update_status()

    def on_edit(self):
        data = self.get_selected_data()
        if not data or data[0] == 'header': return
        ntype, db_id = data
        if ntype == 'rp': self._edit_rp(db_id)
        elif ntype == 'org': self._edit_org(db_id)
        elif ntype == 'store': self._edit_store(db_id)
        elif ntype in ('contact_dm', 'contact_pay'): self._edit_contact(db_id)

    def _edit_rp(self, rp_id):
        cur = self.db.get_rp(rp_id)
        if not cur: return
        dlg = FormDialog("Редактирование отв. лица", [('full_name', 'ФИО'), ('city', 'Город'), ('position', 'Должность'), ('phone', 'Телефон')], {'phone': _phone_validator}, initial=cur)
        if dlg.exec():
            d = dlg.get_data()
            self.db.update_responsible_person(rp_id, d['full_name'], d['city'], d['position'], d['phone'])
            item = self._get_item_by_key(('rp', rp_id))
            if item:
                parent = item.parent() if item.parent() else self.model.invisibleRootItem()
                row = item.row()
                parent.child(row, 1).setText(d['full_name'])
                parent.child(row, 2).setText(d['city'] or '-')
                parent.child(row, 4).setText(d['position'] or '-')
                parent.child(row, 5).setText(d['phone'] or '-')
                self._select_item(('rp', rp_id))

    def _edit_org(self, org_id):
        cur = self.db.get_org(org_id)
        if not cur: return
        dlg = FormDialog("Редактирование организации", [('name', 'Название'), ('contract_number', '№ договора'), ('contract_date', 'Дата договора'), ('address', 'Адрес'), ('phone', 'Телефон')], {'phone': _phone_validator, 'contract_date': _date_validator}, initial=cur)
        if dlg.exec():
            d = dlg.get_data()
            self.db.update_organization(org_id, d['name'], d['address'], d['phone'], d['contract_number'], d['contract_date'])
            item = self._get_item_by_key(('org', org_id))
            if item:
                parent = item.parent() if item.parent() else self.model.invisibleRootItem()
                row = item.row()
                parent.child(row, 1).setText(d['name'])
                parent.child(row, 2).setText(d['contract_number'] or '-')
                parent.child(row, 3).setText(d['contract_date'] or '-')
                parent.child(row, 4).setText(d['address'] or '-')
                parent.child(row, 5).setText(d['phone'] or '-')
                self._select_item(('org', org_id))

    def _edit_store(self, store_id):
        cur = self.db.get_store(store_id)
        if not cur: return
        dlg = FormDialog("Редактирование магазина", [('name', 'Название'), ('address', 'Адрес разгрузки'), ('phone', 'Телефон')], {'phone': _phone_validator}, initial=cur)
        if dlg.exec():
            d = dlg.get_data()
            self.db.update_store(store_id, d['name'], d['address'], d['phone'])
            item = self._get_item_by_key(('store', store_id))
            if item:
                parent = item.parent() if item.parent() else self.model.invisibleRootItem()
                row = item.row()
                parent.child(row, 1).setText(d['name'])
                parent.child(row, 4).setText(d['address'] or '-')
                parent.child(row, 5).setText(d['phone'] or '-')
                self._select_item(('store', store_id))

    def _edit_contact(self, contact_id):
        cur = self.db.get_contact(contact_id)
        if not cur: return
        dlg = FormDialog("Редактирование контакта", [('full_name', 'ФИО'), ('position', 'Должность'), ('phone', 'Телефон')], {'phone': _phone_validator}, initial=cur)
        if dlg.exec():
            d = dlg.get_data()
            self.db.update_contact(contact_id, d['full_name'], d['position'], d['phone'])
            prefix = 'contact_dm' if cur['contact_type'] == 'decision_maker' else 'contact_pay'
            item = self._get_item_by_key((prefix, contact_id))
            if item:
                parent = item.parent() if item.parent() else self.model.invisibleRootItem()
                row = item.row()
                parent.child(row, 1).setText(d['full_name'])
                parent.child(row, 4).setText(d['position'] or '-')
                parent.child(row, 5).setText(d['phone'] or '-')
                self._select_item((prefix, contact_id))

    def on_delete(self):
        indexes = self.tree.selectionModel().selectedRows()
        if not indexes: return
        
        def do_delete():
            data_list = []
            for idx in indexes:
                src_idx = self.proxy_model.mapToSource(idx)
                item = self.model.itemFromIndex(src_idx)
                data = item.data(Qt.UserRole)
                if data and data[0] != 'header':
                    data_list.append(data)
            
            order = {'contact_dm': 4, 'contact_pay': 4, 'store': 3, 'org': 2, 'rp': 1}
            data_list.sort(key=lambda x: order.get(x[0], 0), reverse=True)
            
            for ntype, db_id in data_list:
                if ntype in ('contact_dm', 'contact_pay'): self.db.delete_contact(db_id)
                elif ntype == 'store': self.db.delete_store(db_id)
                elif ntype == 'org': self.db.delete_organization(db_id)
                elif ntype == 'rp': self.db.delete_responsible_person(db_id)
                
                item = self._get_item_by_key((ntype, db_id))
                if item:
                    parent = item.parent()
                    if parent:
                        parent.removeRow(item.row())
                    else:
                        self.model.invisibleRootItem().removeRow(item.row())
            
            self.update_status()

        msg = f"Удалить выбранные элементы ({len(indexes)} шт.)?" if len(indexes) > 1 else "Удалить выбранный элемент?"
        dlg = ConfirmDialog(msg, "Удалить")
        if dlg.exec():
            do_delete()

    def on_change_type(self):
        data = self.get_selected_data()
        if not data or data[0] not in ('contact_dm', 'contact_pay'): return
        cur = self.db.get_contact(data[1])
        dlg = ContactTypeDialog(current_type=cur['contact_type'])
        
        if dlg.exec() and dlg.get_choice():
            new_type = dlg.get_choice()
            self.db.change_contact_type(data[1], new_type)
            
            item = self._get_item_by_key(data)
            if item:
                parent = item.parent()
                row_idx = item.row()
                row_data = [parent.child(row_idx, col).text() for col in range(6)]
                db_id = data[1]
                
                parent.removeRow(row_idx)
                
                prefix = 'contact_dm' if new_type == 'decision_maker' else 'contact_pay'
                new_row = self.make_row("", row_data[1], '', '', row_data[4], row_data[5], (prefix, db_id))
                
                store_id = cur['store_id']
                hdr_item = self._get_item_by_key(('header', new_type, store_id))
                if hdr_item:
                    hdr_item.appendRow(new_row)
                    self._select_item((prefix, db_id))
                    self.update_status()

    def export_data(self):
        # Сначала показываем окно подтверждения
        dlg = ConfirmDialog("Вы уверены, что хотите экспортировать базу данных в Excel?", "Экспортировать")
        
        if dlg.exec():
            export_dir = os.path.join(get_desktop_path(), 'Экспорт контактов')
            filepath = os.path.join(export_dir, 'contacts_export.xlsx')
            
            try:
                os.makedirs(export_dir, exist_ok=True)
                
                # Показываем окно загрузки
                self.loading_dlg = LoadingDialog("Экспорт данных в Excel...\nПожалуйста, подождите.")
                self.loading_dlg.setWindowModality(Qt.ApplicationModal) 
                self.loading_dlg.show()
                
                # Запускаем фоновый поток
                self.export_thread = ExportThread(self.db, filepath)
                self.export_thread.finished_signal.connect(self.on_export_finished)
                self.export_thread.error_signal.connect(self.on_export_error)
                self.export_thread.start()
                
            except Exception as e:
                InfoDialog("Ошибка", f"Не удалось начать экспорт.\n\n{e}").exec()

    def on_export_finished(self, filepath):
        if hasattr(self, 'loading_dlg') and self.loading_dlg:
            self.loading_dlg.accept()
            self.loading_dlg = None
            
        InfoDialog("Успех", f"Данные успешно сохранены:\n{filepath}").exec()

    def on_export_error(self, error_msg):
        if hasattr(self, 'loading_dlg') and self.loading_dlg:
            self.loading_dlg.accept()
            self.loading_dlg = None
            
        InfoDialog("Ошибка экспорта", f"Не удалось сохранить файл:\n\n{error_msg}").exec()

    def import_data(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Импорт из Excel", "", "Excel Files (*.xlsx)")
        if not filepath: return
        
        self.loading_dlg = LoadingDialog("Импорт данных...\nПожалуйста, подождите.")
        self.loading_dlg.setWindowModality(Qt.ApplicationModal) 
        self.loading_dlg.show()
        
        self.import_thread = ImportThread(self.db, filepath)
        self.import_thread.finished_signal.connect(self.on_import_finished)
        self.import_thread.error_signal.connect(self.on_import_error)
        self.import_thread.start()

    def on_import_finished(self, added, updated, skipped):
        try:
            self.refresh_view(show_cursor=False)
        except Exception as e:
            log.error(f"Error refreshing view after import: {e}")
            
        if hasattr(self, 'loading_dlg') and self.loading_dlg:
            self.loading_dlg.accept()
            self.loading_dlg = None
            
        InfoDialog("Импорт завершён", f"Добавлено: {added}\nОбновлено: {updated}\nПропущено: {skipped}").exec()

    def on_import_error(self, error_msg):
        if hasattr(self, 'loading_dlg') and self.loading_dlg:
            self.loading_dlg.accept()
            self.loading_dlg = None
            
        InfoDialog("Ошибка импорта", f"Не удалось импортировать данные:\n\n{error_msg}").exec()

    def show_settings(self):
        dlg = SettingsDialog(self, self.db.db_name)
        if dlg.exec():
            new_path = dlg.get_path()
            settings_data = load_settings()
            
            if not new_path:
                settings_data['db_path'] = ""
                actual_path = os.path.join(app_dir(), 'contacts.db')
            else:
                settings_data['db_path'] = new_path
                actual_path = new_path
                
            save_settings(settings_data)
            
            if os.path.abspath(self.db.db_name) != os.path.abspath(actual_path):
                
                self.loading_dlg = LoadingDialog("Подключение к новой базе данных...\nПожалуйста, подождите.")
                self.loading_dlg.setWindowModality(Qt.ApplicationModal) 
                self.loading_dlg.show()
                
                self.switch_thread = SwitchDbThread(actual_path)
                self.switch_thread.finished_signal.connect(self.on_db_switched)
                self.switch_thread.error_signal.connect(self.on_db_switch_error)
                self.switch_thread.start()

    def on_db_switched(self, new_db):
        self.db = new_db
        
        self.search_input.clear()
        self.refresh_view(show_cursor=False)
        
        if hasattr(self, 'loading_dlg') and self.loading_dlg:
            self.loading_dlg.accept()
            self.loading_dlg = None
            
        InfoDialog("Успех", f"База данных успешно изменена.\nТекущий путь:\n{self.db.db_name}").exec()

    def on_db_switch_error(self, error_msg):
        if hasattr(self, 'loading_dlg') and self.loading_dlg:
            self.loading_dlg.accept()
            self.loading_dlg = None
            
        InfoDialog("Ошибка", f"Не удалось подключиться к базе:\n{error_msg}").exec()
                    
    def show_trash(self):
        dlg = TrashDialog(self.db)
        if dlg.exec():
            self.refresh_view()

    def show_about(self):
        AboutDialog(REPO_URL).exec()

    def closeEvent(self, event):
        dlg = ConfirmDialog("Вы уверены, что хотите выйти?", "Выйти")
        if dlg.exec():
            self.db.close()
            event.accept()
        else:
            event.ignore()