# widgets.py
import time
import re
from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle, Line
from constants import *


def _escape_markup(text):
    """Экранирование символов Kivy-markup."""
    return (str(text)
            .replace('&', '&amp;')
            .replace('[', '&bl;')
            .replace(']', '&br;'))


def _hl_text(text, needle):
    """Подсветка совпадений через markup."""
    text = '' if text is None else str(text)
    if not needle or not text:
        return _escape_markup(text)
    lower = text.lower()
    ln = needle.lower()
    idx = lower.find(ln)
    if idx < 0:
        return _escape_markup(text)
    end = idx + len(needle)
    return (_escape_markup(text[:idx]) +
            f'[color=ffff00]{_escape_markup(text[idx:end])}[/color]' +
            _escape_markup(text[end:]))


def _make_text(text, highlight=None, markup=False):
    if markup or highlight:
        return (_hl_text(text, highlight) if highlight
                else _escape_markup(text if text else ''))
    return str(text) if text is not None else ''


class CustomButton(Button):
    def __init__(self, **kwargs):
        kwargs.setdefault('font_size', '15sp')
        kwargs.setdefault('bold', True)
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = C_BTN
        self.disabled_color = C_TEXT_DISABLED
        self.bind(disabled=self._upd_dis, state=self._upd_state)
        self.bind(pos=self._upd, size=self._upd)
        with self.canvas.after:
            self.border_color = Color(*C_RED_LINE)
            self.border_rect = Line(width=1)
        self._upd_dis(self, self.disabled)
        self._upd()

    def _upd(self, *a):
        if hasattr(self, 'border_rect'):
            self.border_rect.rectangle = (self.x + 1, self.y + 1, self.width - 2, self.height - 2)

    def _upd_dis(self, inst, val):
        if val:
            self.background_color = C_BTN_DISABLED
        else:
            self._upd_state(self, self.state)

    def _upd_state(self, inst, val):
        if self.disabled:
            return
        self.background_color = C_BTN_DOWN if val == 'down' else C_BTN

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            if app:
                app._skip_deselect = True
        return super().on_touch_down(touch)


class RootLayout(BoxLayout):
    def on_touch_down(self, touch):
        if touch.is_mouse_scrolling:
            return super().on_touch_down(touch)

        app = App.get_running_app()
        if app:
            app._skip_deselect = False
            consumed = super().on_touch_down(touch)
            if not getattr(app, '_skip_deselect', False):
                hit = False
                for child in self.walk():
                    if child.collide_point(*touch.pos) and isinstance(child, (CustomButton, TextInput)):
                        hit = True
                        break
                if not hit:
                    app.deselect_all()
            return consumed
        return super().on_touch_down(touch)


class ExcelRow(BoxLayout):
    def __init__(self, app, node_type, db_id, level, col1_parts, c2, c3, c4, c5,
                 expandable=False, expanded=False, is_header=False,
                 highlight=None, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=32, **kwargs)
        self.app = app
        self.node_type = node_type
        self.db_id = db_id
        self.level = level
        self.is_header = is_header
        self.is_selected = False
        self.last_click_time = 0
        self._expand_event = None
        self.highlight = highlight

        if is_header:
            self.bg_normal = C_LVL_HEADER
        elif level == 0:
            self.bg_normal = C_LVL_RP
        elif level == 1:
            self.bg_normal = C_LVL_ORG
        elif level == 2:
            self.bg_normal = C_LVL_STORE
        else:
            self.bg_normal = C_LVL_CONTACT

        with self.canvas.before:
            self.bg_color = Color(*self.bg_normal)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            self.grid_color = Color(*C_RED_LINE)
            self.line_rect = Line(width=1)
            self.line_left = Line(width=1)
            self.line_v1 = Line(width=1)
            self.line_v2 = Line(width=1)
            self.line_v3 = Line(width=1)
            self.line_v4 = Line(width=1)

        self.bind(pos=self._upd, size=self._upd)

        self.toggle_lbl = Label(text="", size_hint_x=None, width=30,
                                color=C_TEXT, bold=True)
        if expandable:
            self.toggle_lbl.text = "-" if expanded else "+"
        self.add_widget(self.toggle_lbl)

        if isinstance(col1_parts, str):
            col1_parts = [(col1_parts, 1.0)]

        self.col1_weights = [w for _, w in col1_parts]
        self.col1_total = sum(self.col1_weights)
        self.col1_box = BoxLayout(size_hint_x=0.35, orientation='horizontal')
        with self.col1_box.canvas.after:
            self.col1_line_color = Color(*C_RED_LINE)
            self.col1_lines = [Line(width=1) for _ in range(len(col1_parts) - 1)]
        self.col1_box.bind(pos=self._upd_col1, size=self._upd_col1)

        # Немного уменьшен отступ, чтобы "ФИО" не сжималось
        pad_left = level * 10 + 10
        
        for i, (text, weight) in enumerate(col1_parts):
            align = 'center' if is_header else 'left'
            
            # Отключаем сжатие (shorten) для слова "ФИО", чтобы оно не превращалось в "Ф..."
            do_shorten = True
            if len(col1_parts) > 1 and i == 0:
                do_shorten = False

            lbl = Label(text=_make_text(text, highlight, markup=True),
                        size_hint_x=weight, halign=align, valign='middle',
                        color=C_TEXT, padding=(pad_left if not is_header and i == 0 else 10, 0),
                        bold=is_header, font_size='14sp', shorten=do_shorten,
                        shorten_from='right', markup=True)
            lbl.bind(size=lbl.setter('text_size'))
            self.col1_box.add_widget(lbl)
        self.add_widget(self.col1_box)

        self.lbl2 = self._mk(c2, 0.15, is_header, 10)
        self.lbl3 = self._mk(c3, 0.10, is_header, 10)
        self.lbl4 = self._mk(c4, 0.25, is_header, 10)
        self.lbl5 = self._mk(c5, 0.15, is_header, 10)
        for l in (self.lbl2, self.lbl3, self.lbl4, self.lbl5):
            self.add_widget(l)

    def _mk(self, text, hint_x, is_header, pad):
        align = 'center' if is_header else 'left'
        lbl = Label(text=_make_text(text, self.highlight, markup=True),
                    size_hint_x=hint_x, halign=align, valign='middle',
                    color=C_TEXT if is_header else C_TEXT_DIM,
                    padding=(pad, 0), font_size='14sp',
                    shorten=True, shorten_from='right', markup=True)
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    def _upd(self, *a):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.line_rect.rectangle = (self.x + 1, self.y, self.width - 2, self.height)
        self.line_left.points = [self.x + 1, self.y, self.x + 1, self.top]

        avail = self.width - 30
        x0 = self.x + 30
        x1 = x0 + avail * 0.35
        x2 = x1 + avail * 0.15
        x3 = x2 + avail * 0.10
        x4 = x3 + avail * 0.25

        self.line_v1.points = []
        self.line_v2.points = []
        self.line_v3.points = []
        self.line_v4.points = []

        if self.node_type != 'header':
            self.line_v3.points = [x3, self.y, x3, self.top]
            self.line_v4.points = [x4, self.y, x4, self.top]
            if self.node_type in ('rp', 'org'):
                self.line_v1.points = [x1, self.y, x1, self.top]
            if self.node_type == 'org':
                self.line_v2.points = [x2, self.y, x2, self.top]

    def _upd_col1(self, *a):
        w, h, x, y = self.col1_box.width, self.col1_box.height, self.col1_box.x, self.col1_box.y
        cx = x
        for i, weight in enumerate(self.col1_weights[:-1]):
            cx += (w * weight) / self.col1_total
            self.col1_lines[i].points = [cx, y, cx, y + h]

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if touch.is_mouse_scrolling:
                return super().on_touch_down(touch)

            app = App.get_running_app()
            if app:
                app._skip_deselect = True

            is_right = getattr(touch, 'button', None) == 'right'
            now = time.time()
            is_double = (now - self.last_click_time) < 0.3
            
            # Читаем модификаторы напрямую из системы (защита от залипания)
            sys_modifiers = getattr(Window._system_keyboard, 'modifiers', [])
            shift_held = 'shift' in sys_modifiers
            ctrl_held = 'ctrl' in sys_modifiers
            
            # Синхронизируем состояние в программе
            if not shift_held: app.shift_pressed = False
            if not ctrl_held: app.ctrl_pressed = False

            # Правый клик или двойной клик (без Shift/Ctrl) → копирование текста
            if is_right or (is_double and not shift_held and not ctrl_held):
                if self.is_header:
                    return True
                    
                if self._expand_event:
                    self._expand_event.cancel()
                    self._expand_event = None
                
                for child in self.walk():
                    if isinstance(child, Label) and child.collide_point(*touch.pos):
                        txt = child.text
                        clean_txt = re.sub(r'\[.*?\]', '', txt).replace('&amp;', '&').replace('&bl;', '[').replace('&br;', ']')
                        if clean_txt and clean_txt.strip() not in ('-', ''):
                            Clipboard.copy(clean_txt)
                            
                            if not hasattr(child, '_orig_color'):
                                child._orig_color = list(child.color)
                                
                            child.color = (0.5, 1, 0.5, 1)
                            
                            def reset_color(dt, c=child):
                                if hasattr(c, '_orig_color'):
                                    c.color = c._orig_color
                                    
                            Clock.schedule_once(reset_color, 0.3)
                        break
                self.last_click_time = 0
                return True

            self.last_click_time = now

            if not self.is_header:
                # --- ЛОГИКА МУЛЬТИВЫДЕЛЕНИЯ ---
                if ctrl_held:
                    app.handle_ctrl_click(self)
                elif shift_held:
                    app.handle_shift_click(self)
                else:
                    app.select_row(self.node_type, self.db_id)

            # Разворачивание — при клике в любом месте строки, если есть +/- (без Shift/Ctrl)
            if self.toggle_lbl.text in ('+', '-') and not ctrl_held and not shift_held:
                if self._expand_event:
                    self._expand_event.cancel()
                self._expand_event = Clock.schedule_once(
                    lambda dt: app.toggle_expand(self.node_type, self.db_id), 0.20)
            return True
        return super().on_touch_down(touch)

    def set_selected(self, state):
        self.is_selected = state
        self.bg_color.rgba = C_SELECTED if state else self.bg_normal