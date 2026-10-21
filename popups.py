# popups.py
import webbrowser
import os
from datetime import datetime
from kivy.clock import Clock  # <--- ВАЖНО: Импорт для обновления корзины
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.graphics import Color, Rectangle
from widgets import CustomButton
from constants import *


def _validate_phone(phone):
    """Простая проверка: хотя бы одна цифра."""
    if not phone:
        return True
    return any(ch.isdigit() for ch in phone)


def _validate_date(date):
    if not date:
        return True
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
        try:
            datetime.strptime(date, fmt)
            return True
        except ValueError:
            continue
    return False


class FormPopup(Popup):
    def __init__(self, title, fields, on_save, initial=None, validators=None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.size_hint = (0.6, 0.85)
        self.auto_dismiss = False
        self.on_save_cb = on_save
        self.validators = validators or {}
        self.inputs = {}

        main = BoxLayout(orientation='vertical', padding=20, spacing=10)
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        content = BoxLayout(orientation='vertical', size_hint=(0.85, None), spacing=12)
        content.bind(minimum_height=content.setter('height'))

        self.hint_labels = {}

        for key, label in fields:
            box = BoxLayout(orientation='vertical', size_hint_y=None, height=95, spacing=4)
            lbl = Label(text=label, size_hint_y=None, height=22, color=C_TEXT,
                        halign='center', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            ti = TextInput(multiline=False, size_hint_y=None, height=42,
                           font_size=16, padding=[10, 10, 10, 10])
            if initial:
                try:
                    val = initial[key]
                    if val is not None:
                        ti.text = str(val)
                except (KeyError, IndexError):
                    pass
            ti.bind(on_text_validate=lambda inst: self._save())
            self.inputs[key] = ti

            hint = Label(text='', size_hint_y=None, height=18, color=C_WARN,
                         font_size='12sp', halign='center')
            hint.bind(size=hint.setter('text_size'))
            self.hint_labels[key] = hint

            box.add_widget(lbl)
            box.add_widget(ti)
            box.add_widget(hint)
            content.add_widget(box)

        anchor.add_widget(content)
        main.add_widget(anchor)

        btns = BoxLayout(size_hint=(0.85, None), pos_hint={'center_x': 0.5},
                         height=45, spacing=15)
        save_btn = CustomButton(text='Сохранить (Enter)')
        save_btn.bind(on_press=self._save)
        cancel_btn = CustomButton(text='Отмена')
        cancel_btn.bind(on_press=lambda *_: self.dismiss())
        btns.add_widget(save_btn)
        btns.add_widget(cancel_btn)
        main.add_widget(btns)

        self.content = main

    def _save(self, *args):
        data = {k: v.text.strip() for k, v in self.inputs.items()}
        ok = True
        for key, validator in self.validators.items():
            valid, msg = validator(data.get(key, ''))
            self.hint_labels[key].text = '' if valid else msg
            if not valid:
                ok = False
        if not ok:
            return
        result = self.on_save_cb(data)
        if result is not False:
            self.dismiss()


class ConfirmPopup(Popup):
    def __init__(self, text, on_confirm, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Подтверждение на удаление'
        self.size_hint = (0.5, 0.3)
        self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.on_confirm_cb = on_confirm
        
        box = BoxLayout(orientation='vertical', padding=15, spacing=15)
        
        # Добавлен valign='middle' чтобы текст был по центру
        lbl = Label(text=text, halign='center', valign='middle', color=C_TEXT)
        lbl.bind(size=lbl.setter('text_size'))
        box.add_widget(lbl)
        
        btns = BoxLayout(size_hint_y=None, height=45, spacing=10)
        yes = CustomButton(text='Удалить')
        yes.bind(on_press=self._confirm)
        no = CustomButton(text='Отмена')
        no.bind(on_press=lambda *_: self.dismiss())
        btns.add_widget(yes)
        btns.add_widget(no)
        
        box.add_widget(btns)
        self.content = box

    def _confirm(self, *a):
        self.on_confirm_cb()
        self.dismiss()


class ContactTypePopup(Popup):
    def __init__(self, on_choice, title='Тип контакта', current_type=None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.size_hint = (0.5, 0.3)
        self.on_choice_cb = on_choice
        box = BoxLayout(orientation='vertical', padding=15, spacing=10)
        box.add_widget(Label(text='Выберите тип контакта:', halign='center', color=C_TEXT))
        btns = BoxLayout(size_hint_y=None, height=45, spacing=10)
        
        # Показываем ЛПР только если текущий тип - не ЛПР
        if current_type != 'decision_maker':
            lpr = CustomButton(text='ЛПР')
            lpr.bind(on_press=lambda *_: self._choose('decision_maker'))
            btns.add_widget(lpr)
            
        # Показываем Оплату только если текущий тип - не Оплата
        if current_type != 'payment':
            pay = CustomButton(text='Оплата')
            pay.bind(on_press=lambda *_: self._choose('payment'))
            btns.add_widget(pay)
            
        cancel = CustomButton(text='Отмена')
        cancel.bind(on_press=lambda *_: self.dismiss())
        btns.add_widget(cancel)
        box.add_widget(btns)
        self.content = box

    def _choose(self, t):
        self.on_choice_cb(t)
        self.dismiss()


class AboutPopup(Popup):
    def __init__(self, text, repo_url="https://github.com/", **kwargs):
        super().__init__(**kwargs)
        self.title = 'О программе'
        self.size_hint = (0.6, 0.7)
        layout = BoxLayout(orientation='vertical', padding=15, spacing=15)
        scroll = ScrollView()
        lbl = Label(text=text, halign='left', valign='top', color=C_TEXT, size_hint_y=None)
        lbl.bind(width=lambda *x: lbl.setter('text_size')(lbl, (lbl.width, None)))
        lbl.bind(texture_size=lambda *x: lbl.setter('height')(lbl, lbl.texture_size[1]))
        scroll.add_widget(lbl)
        layout.add_widget(scroll)
        btns = BoxLayout(size_hint_y=None, height=45, spacing=10)
        repo = CustomButton(text='Перейти в репозиторий')
        repo.bind(on_press=lambda *_: webbrowser.open(repo_url))
        close = CustomButton(text='Закрыть')
        close.bind(on_press=lambda *_: self.dismiss())
        btns.add_widget(repo)
        btns.add_widget(close)
        layout.add_widget(btns)
        self.content = layout


class InfoPopup(Popup):
    def __init__(self, title, text, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.size_hint = (0.55, 0.4)
        box = BoxLayout(orientation='vertical', padding=15, spacing=15)
        lbl = Label(text=text, halign='center', valign='middle', color=C_TEXT)
        lbl.bind(size=lbl.setter('text_size'))
        box.add_widget(lbl)
        close = CustomButton(text='OK', size_hint_y=None, height=45)
        close.bind(on_press=lambda *_: self.dismiss())
        box.add_widget(close)
        self.content = box


class SaveFilePopup(Popup):
    def __init__(self, on_save, initial_path=None, default_name='contacts_export.xlsx', **kwargs):
        super().__init__(**kwargs)
        self.title = 'Куда сохранить файл?'
        self.size_hint = (0.9, 0.9)
        self.on_save_cb = on_save

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        with layout.canvas.before:
            Color(*C_BG)
            self.bg = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda i, v: setattr(self.bg, 'pos', v),
                    size=lambda i, v: setattr(self.bg, 'size', v))

        # Поле для имени файла (отдельно от chooser)
        name_row = BoxLayout(size_hint_y=None, height=42, spacing=8)
        name_row.add_widget(Label(text='Имя файла:', size_hint_x=None, width=100,
                                  color=C_TEXT, halign='left', valign='middle'))
        self.name_input = TextInput(text=default_name, multiline=False,
                                    font_size=16, padding=[10, 10, 10, 10])
        name_row.add_widget(self.name_input)
        layout.add_widget(name_row)

        # Выбор папки
        self.chooser = FileChooserListView(
            filters=['*.xlsx'],
            path=initial_path or os.path.expanduser('~'),
            dirselect=True,
        )
        layout.add_widget(self.chooser)

        btns = BoxLayout(size_hint_y=None, height=45, spacing=10)
        save = CustomButton(text='Сохранить')
        save.bind(on_press=self._save)
        cancel = CustomButton(text='Отмена')
        cancel.bind(on_press=lambda *_: self.dismiss())
        btns.add_widget(save)
        btns.add_widget(cancel)
        layout.add_widget(btns)

        self.content = layout

    def _save(self, *a):
        path = self.chooser.path
        if self.chooser.selection:
            sel = self.chooser.selection[0]
            if os.path.isdir(sel):
                path = sel
        name = (self.name_input.text or '').strip() or 'contacts_export.xlsx'
        if not name.endswith('.xlsx'):
            name += '.xlsx'
        self.on_save_cb(os.path.join(path, name))
        self.dismiss()


class TrashItem(BoxLayout):
    def __init__(self, node_type, db_id, text, on_select, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=40, spacing=5, **kwargs)
        self.node_type = node_type
        self.db_id = db_id
        self.on_select = on_select
        self.is_selected = False
        
        # Внутренний отступ слева, чтобы текст не прилипал к краю
        self.lbl = Label(text=text, color=C_TEXT, halign='left', valign='middle', padding=(20, 0))
        self.lbl.bind(size=self.lbl.setter('text_size'))
        self.add_widget(self.lbl)
        
        with self.canvas.before:
            self.bg_color = Color(*C_BG)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)
        
    def _upd(self, *a):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def set_selected(self, state):
        self.is_selected = state
        self.bg_color.rgba = C_SELECTED if state else C_BG

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.on_select(self)
            return True
        return super().on_touch_down(touch)


class TrashPopup(Popup):
    def __init__(self, db, on_changed, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.on_changed = on_changed
        self.title = 'Корзина'
        self.size_hint = (0.7, 0.8)
        self.selected_items = []
        self._build()

    def _build(self):
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        self.scroll = ScrollView()
        self.lst = BoxLayout(orientation='vertical', size_hint_y=None, spacing=4)
        self.lst.bind(minimum_height=self.lst.setter('height'))
        self.scroll.add_widget(self.lst)
        layout.add_widget(self.scroll)

        btns = BoxLayout(size_hint_y=None, height=45, spacing=10)
        restore_btn = CustomButton(text='Восстановить выбранные', on_press=self._restore)
        purge_all = CustomButton(text='Очистить корзину', on_press=self._purge_all)
        close = CustomButton(text='Закрыть', on_press=lambda *_: self.dismiss())
        
        btns.add_widget(restore_btn)
        btns.add_widget(purge_all)
        btns.add_widget(close)
        layout.add_widget(btns)
        
        self.content = layout
        self._populate_list()

    def _populate_list(self):
        self.lst.clear_widgets()
        self.selected_items.clear()
        items = self.db.get_deleted_items()

        if not items:
            self.lst.add_widget(Label(text='Корзина пуста', color=C_TEXT_DIM, size_hint_y=None, height=40))
            return

        type_names = {'rp': 'Ответственный', 'org': 'Организация',
                      'store': 'Магазин', 'contact': 'Контакт'}
        for node_type, db_id, name, deleted_at in items:
            text = f"[{type_names[node_type]}] {name}  ({deleted_at})"
            item = TrashItem(node_type, db_id, text, self._toggle_select)
            self.lst.add_widget(item)

    def on_touch_down(self, touch):
        # Сбрасываем выделение ТОЛЬКО если кликнули по пустому месту (не по строке и не по кнопке)
        if self.collide_point(*touch.pos):
            clicked_on_interactive = False
            for w in self.walk():
                if isinstance(w, (TrashItem, CustomButton)) and w.collide_point(*touch.pos):
                    clicked_on_interactive = True
                    break
            if not clicked_on_interactive:
                self._clear_selection()
        return super().on_touch_down(touch)

    def _clear_selection(self):
        for item in self.selected_items:
            item.set_selected(False)
        self.selected_items.clear()

    def _toggle_select(self, item):
        if item in self.selected_items:
            self.selected_items.remove(item)
            item.set_selected(False)
        else:
            self.selected_items.append(item)
            item.set_selected(True)

    def _restore(self, *args):
        if not self.selected_items:
            return
            
        for item in self.selected_items:
            self.db.restore_item(item.node_type, item.db_id)
            
        self.on_changed()
        # Откладываем обновление интерфейса на 0.01 сек, чтобы кнопка успела "отпуститься" и запись исчезла
        Clock.schedule_once(lambda dt: self._populate_list(), 0.01)

    def _purge_all(self, *args):
        self.db.purge_all_deleted()
        self.on_changed()
        Clock.schedule_once(lambda dt: self._populate_list(), 0.01)