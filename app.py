# app.py
import os
import sys
import logging
from datetime import datetime
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line

from settings import DB_PATH, load_settings, save_settings, app_dir
from database import Database
from constants import *
from widgets import CustomButton, RootLayout, ExcelRow
from popups import (FormPopup, ConfirmPopup, ContactTypePopup, AboutPopup,
                    InfoPopup, SaveFilePopup, TrashPopup,
                    _validate_phone, _validate_date)
from about import ABOUT_TEXT
from export import export_to_excel, get_desktop_path

log = logging.getLogger('app')

def resource_path(relative_path):
    try:
        base = sys._MEIPASS
    except Exception:
        base = os.path.abspath(".")
    return os.path.join(base, relative_path)


def _phone_validator(phone):
    if _validate_phone(phone):
        return True, ''
    return False, 'Телефон должен содержать хотя бы одну цифру'


def _date_validator(date):
    if _validate_date(date):
        return True, ''
    return False, 'Формат: ДД.ММ.ГГГГ или ГГГГ-ММ-ДД'


class ContactManagerApp(App):
    db = None
    selected_node = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = load_settings()
        self.sort_key = 'name'
        self.sort_dir = 'ASC'
        self.status_label = None
        self.header_labels = {}
        self._skip_deselect = False

    def build(self):
        self.title = 'Менеджер контактов организаций v1.1'
        icon = resource_path('ico/manager.ico')
        if os.path.exists(icon):
            try:
                self.icon = icon
                Window.set_icon(icon)
            except Exception as e:
                log.warning(f"Set icon failed: {e}")

        if self.settings.get('maximized', True):
            Window.maximize()
        else:
            Window.size = tuple(self.settings.get('window_size', (1400, 900)))

        self.db = Database(DB_PATH)
        self.db.connect()

        self.expanded = set()
        self.selected_key = None
        self.current_rows = []

        root = RootLayout(orientation='vertical', padding=10, spacing=8)
        with root.canvas.before:
            Color(*C_BG)
            self.root_bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda i, v: setattr(self.root_bg, 'pos', v),
                  size=lambda i, v: setattr(self.root_bg, 'size', v))

        # Поиск + кнопки
        top = BoxLayout(size_hint_y=None, height=45, spacing=8)
        top.add_widget(Label(text='Поиск:', size_hint_x=None, width=60,
                             color=C_TEXT, bold=True))
        self.search_input = TextInput(hint_text='Поиск по всей базе... (Ctrl+F)',
                                      multiline=False, font_size=16,
                                      padding=[10, 10, 10, 10])
        self.search_input.bind(text=self._on_search)
        top.add_widget(self.search_input)
        top.add_widget(CustomButton(text='Корзина', size_hint_x=None, width=110,
                                    on_press=self.show_trash))
        top.add_widget(CustomButton(text='О программе', size_hint_x=None, width=140,
                                    on_press=self.show_about))
        top.add_widget(CustomButton(text='Выход', size_hint_x=None, width=90,
                                    on_press=self.stop))
        root.add_widget(top)

        # Шапка (теперь без сортировки и с выравниванием по центру)
        header = BoxLayout(size_hint_y=None, height=35, spacing=0)
        with header.canvas.before:
            Color(*C_TABLE_HDR)
            self.hdr_bg = Rectangle(pos=header.pos, size=header.size)
            Color(*C_RED_LINE)
            self.hdr_lines = [Line(width=1.2) for _ in range(6)]

        def upd_hdr(inst, val):
            self.hdr_bg.pos = inst.pos
            self.hdr_bg.size = inst.size
            self.hdr_lines[0].rectangle = (inst.x + 1, inst.y, inst.width - 2, inst.height)
            self.hdr_lines[1].points = [inst.x + 1, inst.y, inst.x + 1, inst.top]
            aw = inst.width - 30
            x0 = inst.x + 30
            xs = [x0, x0 + aw * 0.35, x0 + aw * 0.50, x0 + aw * 0.60, x0 + aw * 0.85]
            for i, x in enumerate(xs[1:], start=2):
                self.hdr_lines[i].points = [x, inst.y, x, inst.top]
        header.bind(pos=upd_hdr, size=upd_hdr)

        header.add_widget(Label(text="", size_hint_x=None, width=30))

        def make_hdr(text, hint_x):
            lbl = Label(text=text, size_hint_x=hint_x, halign='center', valign='middle',
                        bold=True, padding=(5, 0), font_size='15sp', color=C_TEXT)
            lbl.bind(size=lbl.setter('text_size'))
            return lbl

        header.add_widget(make_hdr("Наименование / ФИО",   0.35))
        header.add_widget(make_hdr("Город / Договор",      0.15))
        header.add_widget(make_hdr("Дата договора",        0.10))
        header.add_widget(make_hdr("Адрес / Должность",    0.25))
        header.add_widget(make_hdr("№ телефона",           0.15))
        root.add_widget(header)

        # Таблица
        self.scroll = ScrollView(do_scroll_x=False, bar_width=6)
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=0)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll.add_widget(self.list_layout)
        root.add_widget(self.scroll)

        # Панель действий (без Дублировать и Импорт)
        row1 = BoxLayout(size_hint_y=None, height=46, spacing=8)
        self.add_btn = CustomButton(on_press=self.on_add)
        self.edit_btn = CustomButton(text='Редактировать', on_press=self.on_edit)
        self.delete_btn = CustomButton(text='Удалить', on_press=self.on_delete)
        self.change_type_btn = CustomButton(text='Сменить тип', on_press=self.on_change_contact_type)
        self.export_btn = CustomButton(text='Экспорт в Excel', on_press=self.export_data)
        
        for b in (self.add_btn, self.edit_btn, self.delete_btn,
                  self.change_type_btn, self.export_btn):
            row1.add_widget(b)
        root.add_widget(row1)

        # Служебная панель
        row2 = BoxLayout(size_hint_y=None, height=40, spacing=8)
        row2.add_widget(CustomButton(text='Свернуть всё',
                                     on_press=lambda *_: self.collapse_all()))
        root.add_widget(row2)

        # Статус-бар (без сортировки)
        self.status_label = Label(text='', size_hint_y=None, height=24,
                                  color=C_TEXT_DIM, font_size='13sp',
                                  halign='left', valign='middle', padding=(10, 0))
        self.status_label.bind(size=self.status_label.setter('text_size'))
        with self.status_label.canvas.before:
            Color(*C_STATUS_BG)
            self.status_bg = Rectangle(pos=self.status_label.pos, size=self.status_label.size)
        self.status_label.bind(pos=lambda i, v: setattr(self.status_bg, 'pos', v),
                               size=lambda i, v: setattr(self.status_bg, 'size', v))
        root.add_widget(self.status_label)

        Window.bind(on_key_down=self._on_key_down)

        self.refresh_view()
        return root

    # ---------- Keyboard ----------
    def _has_text_focus(self):
        if self.root:
            for w in self.root.walk():
                if isinstance(w, TextInput) and w.focus:
                    return True
        for w in Window.children:
            if isinstance(w, Popup):
                for sub in w.walk():
                    if isinstance(sub, TextInput) and sub.focus:
                        return True
        return False

    def _popup_open(self):
        for w in Window.children:
            if isinstance(w, Popup):
                return True
        return False

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        if 'ctrl' in modifiers and key == 102:  # Ctrl+F
            self.search_input.focus = True
            return True
        if self._has_text_focus() or self._popup_open():
            return False
        if key == 13:   # Enter
            self.on_edit(); return True
        if key == 127:  # Delete
            self.on_delete(); return True
        if key == 277:  # Insert
            self.on_add(); return True
        return False

    # ---------- Context menu ----------
    def show_context_menu(self, node_type, db_id, touch):
        # Оставлено для совместимости, но правый клик теперь копирует текст
        pass

    def _copy_selected_cell(self):
        pass

    # ---------- CRUD helpers ----------
    def _confirm_delete(self, node_type, db_id):
        msg = {
            'rp': 'Удалить ответственное лицо со всей информацией?',
            'org': 'Удалить организацию со всеми магазинами?',
            'store': 'Удалить магазин со всеми контактами?',
            'contact_dm': 'Удалить контакт ЛПР?',
            'contact_pay': 'Удалить контакт оплаты?',
        }.get(node_type, 'Удалить?')
        ConfirmPopup(msg, lambda: self._delete_by(node_type, db_id)).open()

    def _delete_by(self, node_type, db_id):
        if node_type == 'rp':
            self.db.delete_responsible_person(db_id)
        elif node_type == 'org':
            self.db.delete_organization(db_id)
        elif node_type == 'store':
            self.db.delete_store(db_id)
        else:
            self.db.delete_contact(db_id)
        self.refresh_view()

    def on_change_contact_type(self, *args):
        n = self.selected_node
        if not n or n.node_type not in ('contact_dm', 'contact_pay'):
            return
        
        cur = self.db.get_contact(n.db_id)
        if not cur:
            return
        
        def do_change(t):
            self._do_change_contact_type(n.db_id, t)
            
        ContactTypePopup(
            title='Сменить тип контакта',
            current_type=cur['contact_type'],  # <--- Добавлена эта строка
            on_choice=do_change
        ).open()
        
    def _do_change_contact_type(self, contact_id, new_type):
        self.db.change_contact_type(contact_id, new_type)
        self.refresh_view()

    # ---------- Export / Integrity ----------
    def export_data(self, *args):
        export_dir = os.path.join(get_desktop_path(), 'Экспорт контактов')
        filepath = os.path.join(export_dir, 'contacts_export.xlsx')
        
        try:
            os.makedirs(export_dir, exist_ok=True)
            export_to_excel(self.db, filepath=filepath)
            InfoPopup("Успех", f"Данные сохранены:\n{filepath}").open()
        except PermissionError:
            InfoPopup("Ошибка", 
                      f"Не удалось сохранить файл.\n\n"
                      f"Файл открыт в другой программе (например, в Excel):\n"
                      f"{filepath}\n\n"
                      f"Закройте файл и повторите попытку.").open()
        except Exception as e:
            log.exception("Export failed")
            InfoPopup("Ошибка", f"Не удалось сохранить файл.\n\n{e}").open()

    def show_trash(self, *args):
        TrashPopup(self.db, self.refresh_view).open()

    # ---------- Selection ----------
    def deselect_all(self):
        self.selected_node = None
        self.selected_key = None
        for row in self.current_rows:
            row.set_selected(False)
            for child in row.walk():
                if isinstance(child, Label) and hasattr(child, '_orig_color'):
                    child.color = child._orig_color
        self.update_buttons()

    def toggle_expand(self, node_type, db_id):
        key = (node_type, db_id)
        if key in self.expanded:
            self.expanded.remove(key)
        else:
            self.expanded.add(key)
        self.refresh_view(keep_scroll=True, keep_selection=True)
        self.select_row(node_type, db_id)

    def collapse_all(self):
        self.expanded.clear()
        self.refresh_view()

    def select_row(self, node_type, db_id):
        self.selected_key = (node_type, db_id)
        for row in self.current_rows:
            row.set_selected(row.node_type == node_type and row.db_id == db_id)
        self.selected_node = type('N', (), {'node_type': node_type, 'db_id': db_id})()
        self.update_buttons()

    def update_buttons(self):
        n = self.selected_node
        has = n is not None
        if not has:
            self.add_btn.text = 'Добавить ответственного'
        elif n.node_type == 'rp':
            self.add_btn.text = 'Добавить организацию'
        elif n.node_type == 'org':
            self.add_btn.text = 'Добавить магазин'
        elif n.node_type == 'store':
            self.add_btn.text = 'Добавить контакт'
        else:
            self.add_btn.text = 'Добавить'
            
        self.edit_btn.disabled = not has
        self.delete_btn.disabled = not has
        
        if has and n.node_type in ('contact_dm', 'contact_pay'):
            self.change_type_btn.disabled = False
        else:
            self.change_type_btn.disabled = True

        # Эту строку нужно УДАЛИТЬ:
        # self.new_rp_btn.disabled = has

    # ---------- Refresh ----------
    def refresh_view(self, keep_scroll=False, keep_selection=False):
        scroll_y = self.scroll.scroll_y if keep_scroll else 1.0
        self.list_layout.clear_widgets()
        self.current_rows.clear()
        if not keep_selection:
            self.selected_node = None
            self.selected_key = None

        text = self.search_input.text.strip() if self.search_input else ''
        if text:
            self._build_filtered(text)
        else:
            self._build_full()

        self.update_buttons()
        self._update_status()
        
        # Теперь прокрутка наверх (или сохранение позиции) срабатывает ВСЕГДА
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', scroll_y), 0.05)

    def _update_status(self):
        if not self.status_label:
            return
        c = self.db.get_counts()
        self.status_label.text = (
            f"Ответственных: {c['rp']}  |  Организаций: {c['org']}  |  "
            f"Магазинов: {c['store']}  |  Контактов: {c['contact']}")

    def _row(self, node_type, db_id, level, col1_parts, c2, c3, c4, c5,
             expandable=False, expanded=False, is_header=False, highlight=None):
        r = ExcelRow(self, node_type, db_id, level, col1_parts, c2, c3, c4, c5,
                     expandable=expandable, expanded=expanded,
                     is_header=is_header, highlight=highlight)
        self.list_layout.add_widget(r)
        self.current_rows.append(r)
        return r

    def _build_full(self):
        for rp in self.db.get_responsible_persons(self.sort_key, self.sort_dir):
            orgs = self.db.get_organizations(rp['id'], self.sort_key, self.sort_dir)
            is_exp = ('rp', rp['id']) in self.expanded
            self._row('rp', rp['id'], 0,
                      [("Ответственный", 0.35),
                       (f"{rp['full_name']} ({len(orgs)})", 0.65)],
                      rp['city'] or '-', '', rp['position'] or '-', rp['phone'] or '-',
                      expandable=True, expanded=is_exp)
            if is_exp:
                for org in orgs:
                    stores = self.db.get_stores(org['id'], self.sort_key, self.sort_dir)
                    is_exp_org = ('org', org['id']) in self.expanded
                    self._row('org', org['id'], 1,
                              [("Организация", 0.35),
                               (f"{org['name']} ({len(stores)})", 0.65)],
                              org['contract_number'] or '-',
                              org['contract_date'] or '-',
                              org['address'] or '-', org['phone'] or '-',
                              expandable=True, expanded=is_exp_org)
                    if is_exp_org:
                        for st in stores:
                            contacts = self.db.get_all_contacts(st['id'])
                            is_exp_st = ('store', st['id']) in self.expanded
                            self._row('store', st['id'], 2,
                                      [("Магазин", 0.35),
                                       (f"{st['name']} ({len(contacts)})", 0.65)],
                                      '', '', st['unloading_address'] or '-',
                                      st['phone'] or '-',
                                      expandable=True, expanded=is_exp_st)
                            if is_exp_st:
                                self._add_store_children(st)

    def _add_store_children(self, store):
        self._row('header', 0, 3, [("Контакты ЛПР", 1.0)], '', '', '', '',
                  is_header=True)
        for c in self.db.get_contacts(store['id'], 'decision_maker',
                                      self.sort_key, self.sort_dir):
            self._row('contact_dm', c['id'], 4,
                      [("ФИО", 0.35), (c['full_name'] or '-', 0.65)],
                      '', '', c['position'] or '-', c['phone'] or '-')
        self._row('header', 0, 3, [("Контакты оплаты", 1.0)], '', '', '', '',
                  is_header=True)
        for c in self.db.get_contacts(store['id'], 'payment',
                                      self.sort_key, self.sort_dir):
            self._row('contact_pay', c['id'], 4,
                      [("ФИО", 0.35), (c['full_name'] or '-', 0.65)],
                      '', '', c['position'] or '-', c['phone'] or '-')

    def _build_filtered(self, text):
        tl = text.lower()
        for rp in self.db.get_responsible_persons(self.sort_key, self.sort_dir):
            rp_match = any(tl in (rp[f] or '').lower()
                           for f in ('full_name', 'city', 'position', 'phone'))
            orgs_data = []
            for org in self.db.get_organizations(rp['id'], self.sort_key, self.sort_dir):
                org_match = any(tl in (org[f] or '').lower()
                                for f in ('name', 'address', 'phone',
                                          'contract_number', 'contract_date'))
                stores_data = []
                for st in self.db.get_stores(org['id'], self.sort_key, self.sort_dir):
                    st_match = any(tl in (st[f] or '').lower()
                                   for f in ('name', 'unloading_address', 'phone'))
                    contacts = []
                    for c in self.db.get_all_contacts(st['id']):
                        if any(tl in (c[f] or '').lower()
                               for f in ('full_name', 'position', 'phone')):
                            contacts.append(c)
                            st_match = True
                    if st_match or contacts:
                        stores_data.append((st, contacts))
                        org_match = True
                if org_match or stores_data:
                    orgs_data.append((org, stores_data))
            if rp_match or orgs_data:
                self._row('rp', rp['id'], 0,
                          [("Ответственный", 0.35), (rp['full_name'], 0.65)],
                          rp['city'] or '-', '', rp['position'] or '-',
                          rp['phone'] or '-', expandable=True, expanded=True,
                          highlight=text)
                for org, stores_data in orgs_data:
                    self._row('org', org['id'], 1,
                              [("Организация", 0.35), (org['name'], 0.65)],
                              org['contract_number'] or '-',
                              org['contract_date'] or '-',
                              org['address'] or '-', org['phone'] or '-',
                              expandable=True, expanded=True, highlight=text)
                    for st, contacts in stores_data:
                        self._row('store', st['id'], 2,
                                  [("Магазин", 0.35), (st['name'], 0.65)],
                                  '', '', st['unloading_address'] or '-',
                                  st['phone'] or '-', expandable=True,
                                  expanded=True, highlight=text)
                        for c in contacts:
                            ntype = ('contact_dm' if c['contact_type'] == 'decision_maker'
                                     else 'contact_pay')
                            ctype = 'ЛПР' if c['contact_type'] == 'decision_maker' else 'Оплата'
                            self._row(ntype, c['id'], 4,
                                      [("ФИО", 0.35), (c['full_name'] or '-', 0.65)],
                                      '', '', c['position'] or '-',
                                      f"{c['phone'] or '-'} ({ctype})",
                                      highlight=text)

    def _on_search(self, *args):
        Clock.unschedule(self._do_search)
        Clock.schedule_once(self._do_search, 0.3)

    def _do_search(self, dt):
        self.refresh_view()

    # ---------- Actions ----------
    def on_add(self, *args):
        n = self.selected_node
        if not n:
            self._add_rp()
        elif n.node_type == 'rp':
            self._add_organization(n.db_id)
        elif n.node_type == 'org':
            self._add_store(n.db_id)
        elif n.node_type == 'store':
            ContactTypePopup(on_choice=lambda t: self._add_contact(n.db_id, t)).open()

    def on_edit(self, *args):
        n = self.selected_node
        if not n: return
        {'rp': self._edit_rp, 'org': self._edit_org, 'store': self._edit_store,
         'contact_dm': self._edit_contact, 'contact_pay': self._edit_contact
         }.get(n.node_type, lambda x: None)(n.db_id)

    def on_delete(self, *args):
        n = self.selected_node
        if n:
            self._confirm_delete(n.node_type, n.db_id)

    # ---------- Add/Edit forms ----------
    def _add_rp(self):
        def save(data):
            if not data['full_name']:
                return False
            new_id = self.db.add_responsible_person(
                data['full_name'], data['city'], data['position'], data['phone'])
            self.refresh_view()
            self.select_row('rp', new_id)
            return True
        FormPopup('Новое отв. лицо',
                  [('full_name', 'ФИО'), ('city', 'Город'),
                   ('position', 'Должность'), ('phone', 'Телефон')],
                  save, validators={'phone': _phone_validator}).open()

    def _add_organization(self, rp_id):
        def save(data):
            if not data['name']:
                return False
            new_id = self.db.add_organization(
                rp_id, data['name'], data['address'], data['phone'],
                data['contract_number'], data['contract_date'])
            self.expanded.add(('rp', rp_id))
            self.refresh_view()
            self.select_row('org', new_id)
            return True
        FormPopup('Новая организация',
                  [('name', 'Название'), ('contract_number', '№ договора'),
                   ('contract_date', 'Дата договора'),
                   ('address', 'Адрес'), ('phone', 'Телефон')],
                  save, validators={'phone': _phone_validator,
                                    'contract_date': _date_validator}).open()

    def _add_store(self, org_id):
        def save(data):
            if not data['name']:
                return False
            new_id = self.db.add_store(org_id, data['name'],
                                       data['address'], data['phone'])
            self.expanded.add(('org', org_id))
            self.refresh_view()
            self.select_row('store', new_id)
            return True
        FormPopup('Новый магазин',
                  [('name', 'Название'), ('address', 'Адрес разгрузки'),
                   ('phone', 'Телефон')],
                  save, validators={'phone': _phone_validator}).open()

    def _add_contact(self, store_id, ctype):
        title = 'ЛПР' if ctype == 'decision_maker' else 'Оплата'
        def save(data):
            if not data['full_name']:
                return False
            new_id = self.db.add_contact(store_id, ctype,
                                         data['full_name'],
                                         data['position'], data['phone'])
            self.expanded.add(('store', store_id))
            self.refresh_view()
            self.select_row('contact_dm' if ctype == 'decision_maker'
                            else 'contact_pay', new_id)
            return True
        FormPopup(f'Новый контакт ({title})',
                  [('full_name', 'ФИО'), ('position', 'Должность'),
                   ('phone', 'Телефон')],
                  save, validators={'phone': _phone_validator}).open()

    def _edit_rp(self, rp_id):
        cur = self.db.get_rp(rp_id)
        if not cur: return
        def save(data):
            self.db.update_responsible_person(rp_id, data['full_name'],
                                              data['city'], data['position'],
                                              data['phone'])
            self.refresh_view(); self.select_row('rp', rp_id)
            return True
        FormPopup('Редактирование отв. лица',
                  [('full_name', 'ФИО'), ('city', 'Город'),
                   ('position', 'Должность'), ('phone', 'Телефон')],
                  save, cur, validators={'phone': _phone_validator}).open()

    def _edit_org(self, org_id):
        cur = self.db.get_org(org_id)
        if not cur: return
        def save(data):
            self.db.update_organization(org_id, data['name'], data['address'],
                                        data['phone'], data['contract_number'],
                                        data['contract_date'])
            self.refresh_view(); self.select_row('org', org_id)
            return True
        FormPopup('Редактирование организации',
                  [('name', 'Название'), ('contract_number', '№ договора'),
                   ('contract_date', 'Дата договора'), ('address', 'Адрес'),
                   ('phone', 'Телефон')],
                  save, cur, validators={'phone': _phone_validator,
                                         'contract_date': _date_validator}).open()

    def _edit_store(self, store_id):
        cur = self.db.get_store(store_id)
        if not cur: return
        def save(data):
            self.db.update_store(store_id, data['name'], data['address'],
                                 data['phone'])
            self.refresh_view(); self.select_row('store', store_id)
            return True
        FormPopup('Редактирование магазина',
                  [('name', 'Название'), ('address', 'Адрес разгрузки'),
                   ('phone', 'Телефон')],
                  save, cur, validators={'phone': _phone_validator}).open()

    def _edit_contact(self, contact_id):
        cur = self.db.get_contact(contact_id)
        if not cur: return
        def save(data):
            self.db.update_contact(contact_id, data['full_name'],
                                   data['position'], data['phone'])
            ntype = ('contact_dm' if cur['contact_type'] == 'decision_maker'
                     else 'contact_pay')
            self.refresh_view(); self.select_row(ntype, contact_id)
            return True
        FormPopup('Редактирование контакта',
                  [('full_name', 'ФИО'), ('position', 'Должность'),
                   ('phone', 'Телефон')],
                  save, cur, validators={'phone': _phone_validator}).open()

    def show_about(self, *args):
        AboutPopup(text=ABOUT_TEXT,
                   repo_url="https://github.com/Londimain/Organization-Contacts-Manager").open()

    def on_stop(self):
        try:
            if not self.settings.get('maximized', True):
                self.settings['window_size'] = list(Window.size)
            save_settings(self.settings)
        except Exception as e:
            log.warning(f"Save settings failed: {e}")
        if self.db:
            self.db.close()