# popups.py
import webbrowser
import os
from datetime import datetime
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
        self.title = 'Подтверждение'
        self.size_hint = (0.5, 0.3)
        self.on_confirm_cb = on_confirm
        box = BoxLayout(orientation='vertical', padding=15, spacing=15)
        lbl = Label(text=text, halign='center', color=C_TEXT)
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
        # Базовая папка — либо выбранная в chooser (если это папка),
        # либо текущая открытая папка
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

class TrashPopup(Popup):
    def __init__(self, db, on_changed, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.on_changed = on_changed
        self.title = 'Корзина'
        self.size_hint = (0.7, 0.8)
        self._build()

    def _build(self):
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        items = self.db.get_deleted_items()

        if not items:
            lbl = Label(text='Корзина пуста', color=C_TEXT_DIM)
            layout.add_widget(lbl)
        else:
            scroll = ScrollView()
            lst = BoxLayout(orientation='vertical', size_hint_y=None, spacing=4)
            lst.bind(minimum_height=lst.setter('height'))
            type_names = {'rp': 'Ответственный', 'org': 'Организация',
                          'store': 'Магазин', 'contact': 'Контакт'}
            for node_type, db_id, name, deleted_at in items:
                row = BoxLayout(size_hint_y=None, height=40, spacing=5)
                row.add_widget(Label(text=f"[{type_names[node_type]}] {name}  ({deleted_at})",
                                     color=C_TEXT, halign='left', valign='middle'))
                rest = CustomButton(text='Восстановить', size_hint_x=None, width=140)
                rest.bind(on_press=lambda inst, t=node_type, i=db_id:
                          self._restore(t, i))
                pur = CustomButton(text='Удалить навсегда', size_hint_x=None, width=160)
                pur.bind(on_press=lambda inst, t=node_type, i=db_id:
                         self._purge(t, i))
                row.add_widget(rest)
                row.add_widget(pur)
                lst.add_widget(row)
            scroll.add_widget(lst)
            layout.add_widget(scroll)

        btns = BoxLayout(size_hint_y=None, height=45, spacing=10)
        purge_all = CustomButton(text='Очистить корзину')
        purge_all.bind(on_press=self._purge_all)
        close = CustomButton(text='Закрыть')
        close.bind(on_press=lambda *_: self.dismiss())
        btns.add_widget(purge_all)
        btns.add_widget(close)
        layout.add_widget(btns)
        self.content = layout

    def _restore(self, t, i):
        self.db.restore_item(t, i)
        self.on_changed()
        self._refresh()

    def _purge(self, t, i):
        self.db.purge_item(t, i)
        self.on_changed()
        self._refresh()

    def _purge_all(self, *args):
        self.db.purge_all_deleted()
        self.on_changed()
        self._refresh()

    def _refresh(self):
        self.dismiss()
        TrashPopup(self.db, self.on_changed).open()