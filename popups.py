import webbrowser
import os
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.filechooser import FileChooserListView
from kivy.graphics import Color, Rectangle
from widgets import CustomButton
from constants import *

class FormPopup(Popup):
    def __init__(self, title, fields, on_save, initial=None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.size_hint = (0.75, 0.7)
        self.auto_dismiss = False
        self.on_save_cb = on_save
        self.inputs = {}

        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        for key, label in fields:
            content.add_widget(Label(text=label, size_hint_y=None, height=25, halign='left', color=C_TEXT))
            
            ti = TextInput(
                multiline=False, 
                size_hint_y=None, 
                height=45, 
                font_size=16, 
                padding=[10, 10, 10, 10]
            )
            
            if initial:
                try:
                    val = initial[key]
                    if val is not None:
                        ti.text = str(val)
                except (KeyError, IndexError):
                    pass
                    
            ti.bind(on_text_validate=lambda inst: self._save())
            self.inputs[key] = ti
            content.add_widget(ti)

        btns = BoxLayout(size_hint_y=None, height=45, spacing=10)
        save_btn = CustomButton(text='Сохранить (Enter)')
        save_btn.bind(on_press=self._save)
        cancel_btn = CustomButton(text='Отмена')
        cancel_btn.bind(on_press=lambda *_: self.dismiss())
        btns.add_widget(save_btn)
        btns.add_widget(cancel_btn)
        content.add_widget(btns)
        self.content = content

    def _save(self, *args):
        data = {k: v.text.strip() for k, v in self.inputs.items()}
        self.on_save_cb(data)
        self.dismiss()


class ConfirmPopup(Popup):
    def __init__(self, text, on_confirm, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Подтверждение'
        self.size_hint = (0.5, 0.3)
        self.on_confirm_cb = on_confirm
        box = BoxLayout(orientation='vertical', padding=15, spacing=15)
        box.add_widget(Label(text=text, halign='center', color=C_TEXT))
        btns = BoxLayout(size_hint_y=None, height=45, spacing=10)
        yes = CustomButton(text='Удалить')
        yes.bind(on_press=self._confirm)
        no = CustomButton(text='Отмена')
        no.bind(on_press=lambda *_: self.dismiss())
        btns.add_widget(yes)
        btns.add_widget(no)
        box.add_widget(btns)
        self.content = box

    def _confirm(self, *args):
        self.on_confirm_cb()
        self.dismiss()


class ContactTypePopup(Popup):
    def __init__(self, on_choice, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Тип контакта'
        self.size_hint = (0.5, 0.3)
        self.on_choice_cb = on_choice
        box = BoxLayout(orientation='vertical', padding=15, spacing=10)
        box.add_widget(Label(text='Выберите тип контакта:', halign='center', color=C_TEXT))
        btns = BoxLayout(size_hint_y=None, height=45, spacing=10)
        lpr = CustomButton(text='ЛПР')
        lpr.bind(on_press=lambda *_: self._choose('decision_maker'))
        pay = CustomButton(text='Оплата')
        pay.bind(on_press=lambda *_: self._choose('payment'))
        cancel = CustomButton(text='Отмена')
        cancel.bind(on_press=lambda *_: self.dismiss())
        btns.add_widget(lpr)
        btns.add_widget(pay)
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
        self.size_hint = (0.6, 0.6)
        
        layout = BoxLayout(orientation='vertical', padding=15, spacing=15)
        
        scroll = ScrollView()
        lbl = Label(
            text=text, 
            halign='left', 
            valign='top', 
            color=C_TEXT,
            size_hint_y=None
        )
        lbl.bind(width=lambda *x: lbl.setter('text_size')(lbl, (lbl.width, None)))
        lbl.bind(texture_size=lambda *x: lbl.setter('height')(lbl, lbl.texture_size[1]))
        scroll.add_widget(lbl)
        layout.add_widget(scroll)
        
        btns = BoxLayout(size_hint_y=None, height=45, spacing=10)
        
        repo_btn = CustomButton(text='Перейти в репозиторий')
        repo_btn.bind(on_press=lambda *_: webbrowser.open(repo_url))
        
        close_btn = CustomButton(text='Закрыть')
        close_btn.bind(on_press=lambda *_: self.dismiss())
        
        btns.add_widget(repo_btn)
        btns.add_widget(close_btn)
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
        
        close_btn = CustomButton(text='OK', size_hint_y=None, height=45)
        close_btn.bind(on_press=lambda *_: self.dismiss())
        box.add_widget(close_btn)
        
        self.content = box


# --- НОВОЕ ОКНО СОХРАНЕНИЯ ФАЙЛА ---
class SaveFilePopup(Popup):
    def __init__(self, on_save, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Укажите место для сохранения'
        self.size_hint = (0.9, 0.9)
        self.on_save_cb = on_save
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Темный фон для попапа
        with layout.canvas.before:
            Color(*C_BG)
            self.bg_rect = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda i, v: setattr(self.bg_rect, 'pos', v),
                    size=lambda i, v: setattr(self.bg_rect, 'size', v))
        
        # Выбор файла (по умолчанию открывается папка пользователя)
        self.chooser = FileChooserListView(
            filters=['*.xlsx'],
            path=os.path.expanduser('~')
        )
        layout.add_widget(self.chooser)
        
        btns = BoxLayout(size_hint_y=None, height=45, spacing=10)
        save_btn = CustomButton(text='Сохранить')
        save_btn.bind(on_press=self._save)
        cancel_btn = CustomButton(text='Отмена')
        cancel_btn.bind(on_press=lambda *_: self.dismiss())
        
        btns.add_widget(save_btn)
        btns.add_widget(cancel_btn)
        layout.add_widget(btns)
        
        self.content = layout

    def _save(self, *args):
        path = self.chooser.path
        filename = self.chooser.filename
        
        if not filename:
            filename = "contacts_export.xlsx"
        elif not filename.endswith('.xlsx'):
            filename += '.xlsx'
            
        full_path = os.path.join(path, filename)
        self.on_save_cb(full_path)
        self.dismiss()