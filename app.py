import os
import sys
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle, Line

from database import Database
from constants import *
from widgets import CustomButton, RootLayout, ExcelRow
# Убираем импорт SaveFilePopup, так как он больше не нужен
from popups import FormPopup, ConfirmPopup, ContactTypePopup, AboutPopup, InfoPopup
from about import ABOUT_TEXT
from export import export_to_excel

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class ContactManagerApp(App):
    db = None
    selected_node = None

    def build(self):
        self.title = 'Менеджер контактов организаций v1.0'
        
        icon_path = resource_path('ico/manager.ico')
        if os.path.exists(icon_path):
            self.icon = icon_path
            Window.set_icon(icon_path)
        
        Window.maximize()
        
        self.db = Database()
        self.db.connect()
        
        self.expanded = set()
        self.selected_key = None
        self.current_rows = []

        root = RootLayout(orientation='vertical', padding=10, spacing=10)
        with root.canvas.before:
            Color(*C_BG)
            self.root_bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda i, v: setattr(self.root_bg, 'pos', v),
                  size=lambda i, v: setattr(self.root_bg, 'size', v))

        # Поиск и кнопки справа
        search_bar = BoxLayout(size_hint_y=None, height=45, spacing=8)
        search_bar.add_widget(Label(text='Поиск:', size_hint_x=None, width=60, color=C_TEXT, bold=True))
        
        self.search_input = TextInput(
            hint_text='Поиск по всей базе... (двойной клик по ячейке - копировать)',
            multiline=False,
            font_size=16,
            padding=[10, 10, 10, 10]
        )
        self.search_input.bind(text=self._on_search)
        search_bar.add_widget(self.search_input)
        
        about_btn = CustomButton(text='О программе', size_hint_x=None, width=160, on_press=self.show_about)
        search_bar.add_widget(about_btn)
        
        exit_btn = CustomButton(text='Выход', size_hint_x=None, width=100, on_press=self.stop)
        search_bar.add_widget(exit_btn)
        
        root.add_widget(search_bar)

        # --- ШАПКА ТАБЛИЦЫ ---
        header_bar = BoxLayout(size_hint_y=None, height=35, spacing=0)
        with header_bar.canvas.before:
            Color(*C_TABLE_HDR)
            self.hdr_bg = Rectangle(pos=header_bar.pos, size=header_bar.size)
            
            Color(*C_RED_LINE)
            self.hdr_line_rect = Line(width=1.2)
            self.hdr_line_left = Line(width=1.2)
            self.hdr_line_v1 = Line(width=1.2)
            self.hdr_line_v2 = Line(width=1.2)
            self.hdr_line_v3 = Line(width=1.2)
        
        def update_hdr_canvas(inst, val):
            self.hdr_bg.pos = inst.pos
            self.hdr_bg.size = inst.size
            
            self.hdr_line_rect.rectangle = (inst.x + 1, inst.y, inst.width - 2, inst.height)
            self.hdr_line_left.points = [inst.x + 1, inst.y, inst.x + 1, inst.top]
            
            avail_w = inst.width - 30
            x0 = inst.x + 30
            x1 = x0 + avail_w * 0.45
            x2 = x1 + avail_w * 0.15
            x3 = x2 + avail_w * 0.25
            
            self.hdr_line_v1.points = [x1, inst.y, x1, inst.top]
            self.hdr_line_v2.points = [x2, inst.y, x2, inst.top]
            self.hdr_line_v3.points = [x3, inst.y, x3, inst.top]
            
        header_bar.bind(pos=update_hdr_canvas, size=update_hdr_canvas)

        header_bar.add_widget(Label(text="", size_hint_x=None, width=30))
        header_bar.add_widget(Label(text="Наименование / ФИО", size_hint_x=0.45, halign='left', valign='middle', bold=True, padding=(10,0), font_size='16sp'))
        header_bar.add_widget(Label(text="Город", size_hint_x=0.15, halign='left', valign='middle', bold=True, padding=(10,0), font_size='16sp'))
        header_bar.add_widget(Label(text="Адрес / Должность", size_hint_x=0.25, halign='left', valign='middle', bold=True, padding=(10,0), font_size='16sp'))
        header_bar.add_widget(Label(text="№ телефона", size_hint_x=0.15, halign='left', valign='middle', bold=True, padding=(10,0), font_size='16sp'))
        root.add_widget(header_bar)

        # Скролл с данными
        self.scroll = ScrollView(do_scroll_x=False, bar_width=6)
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=0)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll.add_widget(self.list_layout)
        root.add_widget(self.scroll)

        # Панель действий
        row1 = BoxLayout(size_hint_y=None, height=50, spacing=8)
        self.add_btn = CustomButton(text='Добавить', on_press=self.on_add)
        self.edit_btn = CustomButton(text='Редактировать', on_press=self.on_edit)
        self.delete_btn = CustomButton(text='Удалить', on_press=self.on_delete)
        self.export_btn = CustomButton(text='Экспорт в Excel', on_press=self.export_data)
        for b in (self.add_btn, self.edit_btn, self.delete_btn, self.export_btn):
            row1.add_widget(b)
        root.add_widget(row1)

        # Служебная панель
        row2 = BoxLayout(size_hint_y=None, height=45, spacing=8)
        new_rp_btn = CustomButton(text='Новое ответственное лицо', on_press=lambda *_: self._add_rp())
        collapse_btn = CustomButton(text='Свернуть всё', on_press=lambda *_: self.collapse_all())
        for b in (new_rp_btn, collapse_btn):
            row2.add_widget(b)
        root.add_widget(row2)

        self.refresh_view()
        return root

    def export_data(self, *args):
        # Автоматическое сохранение на рабочий стол
        try:
            filepath = export_to_excel(self.db)
            InfoPopup("Успех", f"Данные успешно сохранены!\n\nФайл: {filepath}").open()
        except Exception as e:
            InfoPopup("Ошибка", f"Не удалось сохранить файл.\nПроверьте, установлена ли библиотека openpyxl.\n\nОшибка: {e}").open()

    def show_about(self, *args):
        repo_url = "https://github.com/Londimain/Organization-Contacts-Manager"
        AboutPopup(text=ABOUT_TEXT, repo_url=repo_url).open()

    def deselect_all(self):
        if self.selected_node:
            self.selected_node = None
            self.selected_key = None
            for row in self.current_rows:
                row.set_selected(False)
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
        key = (node_type, db_id)
        self.selected_key = key
        
        for row in self.current_rows:
            if row.node_type == node_type and row.db_id == db_id:
                row.set_selected(True)
            else:
                row.set_selected(False)
        
        self.selected_node = type('Node', (), {'node_type': node_type, 'db_id': db_id})()
        self.update_buttons()

    def update_buttons(self):
        n = self.selected_node
        has_sel = n is not None
        
        if not has_sel:
            self.add_btn.text = 'Добавить ответственного'
            self.add_btn.disabled = False
        elif n.node_type == 'rp':
            self.add_btn.text = 'Добавить организацию'
            self.add_btn.disabled = False
        elif n.node_type == 'org':
            self.add_btn.text = 'Добавить магазин'
            self.add_btn.disabled = False
        elif n.node_type == 'store':
            self.add_btn.text = 'Добавить контакт'
            self.add_btn.disabled = False
        else:
            self.add_btn.text = 'Добавить'
            self.add_btn.disabled = True
            
        self.edit_btn.disabled = not has_sel
        self.delete_btn.disabled = not has_sel

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
        if keep_scroll:
            Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', scroll_y), 0.05)

    def _build_full(self):
        for rp in self.db.get_responsible_persons():
            is_exp = ('rp', rp['id']) in self.expanded
            row = ExcelRow(self, 'rp', rp['id'], 0, 
                           col1_parts=[("Ответственный", 0.35), (rp['full_name'], 0.65)],
                           col_city=rp['city'] or '-', 
                           col2=rp['position'] or '-', 
                           col3=rp['phone'] or '-', 
                           expandable=True, expanded=is_exp)
            self.list_layout.add_widget(row)
            self.current_rows.append(row)
            
            if is_exp:
                for org in self.db.get_organizations(rp['id']):
                    is_exp_org = ('org', org['id']) in self.expanded
                    row = ExcelRow(self, 'org', org['id'], 1, 
                                   col1_parts=[("Организация", 0.35), (org['name'], 0.65)],
                                   col_city="", 
                                   col2=org['address'] or '-', 
                                   col3=org['phone'] or '-', 
                                   expandable=True, expanded=is_exp_org)
                    self.list_layout.add_widget(row)
                    self.current_rows.append(row)
                    
                    if is_exp_org:
                        for store in self.db.get_stores(org['id']):
                            is_exp_store = ('store', store['id']) in self.expanded
                            row = ExcelRow(self, 'store', store['id'], 2, 
                                           col1_parts=[("Магазин", 0.35), (store['name'], 0.65)],
                                           col_city="", 
                                           col2=store['unloading_address'] or '-', 
                                           col3=store['phone'] or '-', 
                                           expandable=True, expanded=is_exp_store)
                            self.list_layout.add_widget(row)
                            self.current_rows.append(row)
                            
                            if is_exp_store:
                                self._add_store_children(store)

    def _add_store_children(self, store):
        hdr_lpr = ExcelRow(self, 'header', 0, 3, 
                           col1_parts=[("Контакты ЛПР", 1.0)], col_city="", col2="", col3="", is_header=True)
        self.list_layout.add_widget(hdr_lpr)
        self.current_rows.append(hdr_lpr)
        for c in self.db.get_contacts(store['id'], 'decision_maker'):
            row = ExcelRow(self, 'contact_dm', c['id'], 4, 
                           col1_parts=[("ФИО", 0.35), (c['full_name'] or '-', 0.65)],
                           col_city="", col2=c['position'] or '-', col3=c['phone'] or '-')
            self.list_layout.add_widget(row)
            self.current_rows.append(row)

        hdr_pay = ExcelRow(self, 'header', 0, 3, 
                           col1_parts=[("Контакты оплаты", 1.0)], col_city="", col2="", col3="", is_header=True)
        self.list_layout.add_widget(hdr_pay)
        self.current_rows.append(hdr_pay)
        for c in self.db.get_contacts(store['id'], 'payment'):
            row = ExcelRow(self, 'contact_pay', c['id'], 4, 
                           col1_parts=[("ФИО", 0.35), (c['full_name'] or '-', 0.65)],
                           col_city="", col2=c['position'] or '-', col3=c['phone'] or '-')
            self.list_layout.add_widget(row)
            self.current_rows.append(row)

    def _build_filtered(self, text):
        tl = text.lower()
        for rp in self.db.get_responsible_persons():
            rp_match = (tl in (rp['full_name'] or '').lower() 
                        or tl in (rp['city'] or '').lower()
                        or tl in (rp['position'] or '').lower()
                        or tl in (rp['phone'] or '').lower())
            
            orgs_data = []
            for org in self.db.get_organizations(rp['id']):
                org_match = (tl in (org['name'] or '').lower() 
                             or tl in (org['address'] or '').lower()
                             or tl in (org['phone'] or '').lower())
                stores_data = []
                for store in self.db.get_stores(org['id']):
                    store_match = (tl in (store['name'] or '').lower() 
                                   or tl in (store['unloading_address'] or '').lower()
                                   or tl in (store['phone'] or '').lower())
                    contacts_data = []
                    for c in self.db.get_all_contacts(store['id']):
                        if (tl in (c['full_name'] or '').lower() 
                                or tl in (c['position'] or '').lower() 
                                or tl in (c['phone'] or '').lower()):
                            contacts_data.append(c)
                            store_match = True
                    if store_match or contacts_data:
                        stores_data.append((store, contacts_data))
                        org_match = True
                if org_match or stores_data:
                    orgs_data.append((org, stores_data))
                    
            if rp_match or orgs_data:
                row = ExcelRow(self, 'rp', rp['id'], 0, 
                               col1_parts=[("Ответственный", 0.35), (rp['full_name'], 0.65)],
                               col_city=rp['city'] or '-', 
                               col2=rp['position'] or '-', 
                               col3=rp['phone'] or '-', 
                               expandable=True, expanded=True)
                self.list_layout.add_widget(row)
                self.current_rows.append(row)
                
                for org, stores_data in orgs_data:
                    row = ExcelRow(self, 'org', org['id'], 1, 
                                   col1_parts=[("Организация", 0.35), (org['name'], 0.65)],
                                   col_city="", 
                                   col2=org['address'] or '-', 
                                   col3=org['phone'] or '-', 
                                   expandable=True, expanded=True)
                    self.list_layout.add_widget(row)
                    self.current_rows.append(row)
                    
                    for store, contacts_data in stores_data:
                        row = ExcelRow(self, 'store', store['id'], 2, 
                                       col1_parts=[("Магазин", 0.35), (store['name'], 0.65)],
                                       col_city="", 
                                       col2=store['unloading_address'] or '-', 
                                       col3=store['phone'] or '-', 
                                       expandable=True, expanded=True)
                        self.list_layout.add_widget(row)
                        self.current_rows.append(row)

                        for c in contacts_data:
                            ctype = 'ЛПР' if c['contact_type'] == 'decision_maker' else 'Оплата'
                            ntype = 'contact_dm' if c['contact_type'] == 'decision_maker' else 'contact_pay'
                            row = ExcelRow(self, ntype, c['id'], 3, 
                                           col1_parts=[("ФИО", 0.35), (c['full_name'] or '-', 0.65)], 
                                           col_city="", col2=c['position'] or '-', 
                                           col3=f"{c['phone'] or '-'} ({ctype})")
                            self.list_layout.add_widget(row)
                            self.current_rows.append(row)

    def _on_search(self, *args):
        Clock.unschedule(self._do_search)
        Clock.schedule_once(self._do_search, 0.3)

    def _do_search(self, dt):
        self.refresh_view()

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
        if n.node_type == 'rp': self._edit_rp(n.db_id)
        elif n.node_type == 'org': self._edit_org(n.db_id)
        elif n.node_type == 'store': self._edit_store(n.db_id)
        elif n.node_type in ('contact_dm', 'contact_pay'): self._edit_contact(n.db_id)

    def on_delete(self, *args):
        n = self.selected_node
        if not n: return
        msg = {
            'rp': 'Удалить ответственное лицо со всей информацией?',
            'org': 'Удалить организацию со всеми магазинами?',
            'store': 'Удалить магазин со всеми контактами?',
            'contact_dm': 'Удалить контакт ЛПР?',
            'contact_pay': 'Удалить контакт оплаты?',
        }.get(n.node_type)
        if msg:
            ConfirmPopup(msg, lambda: self._delete(n)).open()

    def _delete(self, n):
        if n.node_type == 'rp': self.db.delete_responsible_person(n.db_id)
        elif n.node_type == 'org': self.db.delete_organization(n.db_id)
        elif n.node_type == 'store': self.db.delete_store(n.db_id)
        else: self.db.delete_contact(n.db_id)
        
        self.refresh_view()

    def _add_rp(self):
        def save(data):
            if not data['full_name']: return
            new_id = self.db.add_responsible_person(
                data['full_name'], data['city'], data['position'], data['phone']
            )
            self.refresh_view()
            self.select_row('rp', new_id)
        FormPopup('Новое отв. лицо', 
                  [('full_name', 'ФИО'), ('city', 'Город'), ('position', 'Должность'), ('phone', 'Телефон')], 
                  save).open()

    def _add_organization(self, rp_id):
        def save(data):
            if not data['name']: return
            new_id = self.db.add_organization(rp_id, data['name'], data['address'], data['phone'])
            self.expanded.add(('rp', rp_id))
            self.refresh_view()
            self.select_row('org', new_id)
        FormPopup('Новая организация', 
                  [('name', 'Название'), ('address', 'Адрес'), ('phone', 'Телефон')], 
                  save).open()

    def _add_store(self, org_id):
        def save(data):
            if not data['name']: return
            new_id = self.db.add_store(org_id, data['name'], data['address'], data['phone'])
            self.expanded.add(('org', org_id))
            self.refresh_view()
            self.select_row('store', new_id)
        FormPopup('Новый магазин', 
                  [('name', 'Название'), ('address', 'Адрес разгрузки'), ('phone', 'Телефон')], 
                  save).open()

    def _add_contact(self, store_id, ctype):
        title = 'ЛПР' if ctype == 'decision_maker' else 'Оплата'
        def save(data):
            new_id = self.db.add_contact(store_id, ctype, data['full_name'], data['position'], data['phone'])
            self.expanded.add(('store', store_id))
            self.refresh_view()
            self.select_row('contact_dm' if ctype == 'decision_maker' else 'contact_pay', new_id)
        FormPopup(f'Новый контакт ({title})', 
                  [('full_name', 'ФИО'), ('position', 'Должность'), ('phone', 'Телефон')], 
                  save).open()

    def _edit_rp(self, rp_id):
        cur = self.db.get_rp(rp_id)
        if not cur: return
        def save(data):
            self.db.update_responsible_person(rp_id, data['full_name'], data['city'], data['position'], data['phone'])
            self.refresh_view()
            self.select_row('rp', rp_id)
        FormPopup('Редактировать', 
                  [('full_name', 'ФИО'), ('city', 'Город'), ('position', 'Должность'), ('phone', 'Телефон')], 
                  save, cur).open()

    def _edit_org(self, org_id):
        cur = self.db.get_org(org_id)
        if not cur: return
        def save(data):
            self.db.update_organization(org_id, data['name'], data['address'], data['phone'])
            self.refresh_view()
            self.select_row('org', org_id)
        FormPopup('Редактировать', 
                  [('name', 'Название'), ('address', 'Адрес'), ('phone', 'Телефон')], 
                  save, cur).open()

    def _edit_store(self, store_id):
        cur = self.db.get_store(store_id)
        if not cur: return
        def save(data):
            self.db.update_store(store_id, data['name'], data['address'], data['phone'])
            self.refresh_view()
            self.select_row('store', store_id)
        FormPopup('Редактировать', 
                  [('name', 'Название'), ('address', 'Адрес разгрузки'), ('phone', 'Телефон')], 
                  save, cur).open()

    def _edit_contact(self, contact_id):
        cur = self.db.get_contact(contact_id)
        if not cur: return
        def save(data):
            self.db.update_contact(contact_id, data['full_name'], data['position'], data['phone'])
            ntype = 'contact_dm' if cur['contact_type'] == 'decision_maker' else 'contact_pay'
            self.refresh_view()
            self.select_row(ntype, contact_id)
        FormPopup('Редактировать', 
                  [('full_name', 'ФИО'), ('position', 'Должность'), ('phone', 'Телефон')], 
                  save, cur).open()

    def on_stop(self):
        if self.db: self.db.close()