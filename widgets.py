# widgets.py
import time
import re
from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.properties import BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line
from constants import *


def _escape_markup(text):
    return (str(text)
            .replace('&', '&amp;')
            .replace('[', '&bl;')
            .replace(']', '&br;'))


def _hl_text(text, needle):
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


class HoverBehavior(object):
    hovered = BooleanProperty(False)

    def __init__(self, **kwargs):
        self.register_event_type('on_enter')
        self.register_event_type('on_leave')
        super(HoverBehavior, self).__init__(**kwargs)
        self._mouse_bound = False
        self.bind(parent=self._on_parent_change)
        if self.parent is not None:
            self._bind_mouse()

    def _on_parent_change(self, instance, parent):
        if parent is None:
            self._unbind_mouse()
        else:
            self._bind_mouse()

    def _bind_mouse(self):
        if not self._mouse_bound:
            Window.bind(mouse_pos=self._on_mouse_pos)
            self._mouse_bound = True

    def _unbind_mouse(self):
        if self._mouse_bound:
            Window.unbind(mouse_pos=self._on_mouse_pos)
            self._mouse_bound = False
            if self.hovered:
                self.hovered = False
                self.dispatch('on_leave')

    def _on_mouse_pos(self, window, pos):
        if not self.get_root_window():
            return
            
        parent = self.parent
        in_popup = False
        limit = 10
        while parent and limit > 0:
            if isinstance(parent, Popup):
                in_popup = True
                break
            parent = parent.parent
            limit -= 1

        app = App.get_running_app()
        if app and app._popup_open() and not in_popup:
            if self.hovered:
                self.hovered = False
                self.dispatch('on_leave')
            return
            
        inside = self.collide_point(*self.to_widget(*pos))
        if self.hovered == inside:
            return
        self.hovered = inside
        if inside:
            self.dispatch('on_enter')
        else:
            self.dispatch('on_leave')

    def on_enter(self, *args):
        pass

    def on_leave(self, *args):
        pass


class CustomButton(HoverBehavior, Button):
    def __init__(self, **kwargs):
        kwargs.setdefault('font_size', '15sp')
        kwargs.setdefault('bold', True)
        kwargs.setdefault('halign', 'center')
        kwargs.setdefault('valign', 'middle')
        kwargs.setdefault('shorten', True)
        kwargs.setdefault('shorten_from', 'right')
        super().__init__(**kwargs)
        
        self.background_normal = ''
        self.background_down = ''
        self.background_color = C_BTN
        self.disabled_color = C_TEXT_DISABLED

        self.bind(size=lambda inst, val: setattr(inst, 'text_size', (max(0, val[0] - 10), val[1])))

        self.bind(disabled=self._upd_dis, state=self._upd_state)
        self.bind(pos=self._upd, size=self._upd)

        with self.canvas.after:
            self.border_color = Color(*C_RED_LINE)
            self.border_rect = Line(width=1.2)

        self._apply_color()
        self._upd()

    def on_enter(self, *args):
        self._apply_color()

    def on_leave(self, *args):
        self._apply_color()

    def _apply_color(self):
        if self.disabled:
            self.background_color = C_BTN_DISABLED
        elif self.state == 'down':
            self.background_color = C_BTN_DOWN
        elif self.hovered:
            self.background_color = C_BTN_HOVER
        else:
            self.background_color = C_BTN

    def _upd(self, *a):
        if hasattr(self, 'border_rect'):
            w, h = self.width, self.height
            if w > 2 and h > 2:
                self.border_rect.points = [self.x, self.y, self.x + w, self.y, self.x + w, self.y + h, self.x, self.y + h, self.x, self.y]
            else:
                self.border_rect.points = []

    def _upd_dis(self, inst, val):
        self._apply_color()

    def _upd_state(self, inst, val):
        self._apply_color()


class RootLayout(BoxLayout):
    def on_touch_down(self, touch):
        if touch.is_mouse_scrolling:
            return super().on_touch_down(touch)

        app = App.get_running_app()
        if app and app._popup_open():
            return True

        if getattr(touch, 'button', None) == 'right':
            hit = False
            for child in self.walk():
                if isinstance(child, (CustomButton, TextInput, ExcelRow)) and child.collide_point(*touch.pos):
                    hit = True
                    break
            if not hit:
                app.deselect_all()
                return True

        return super().on_touch_down(touch)


class ExcelRow(HoverBehavior, BoxLayout):
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
        self.col1_box = BoxLayout(size_hint_x=0.45, orientation='horizontal')
        with self.col1_box.canvas.after:
            self.col1_line_color = Color(*C_RED_LINE)
            self.col1_lines = [Line(width=1) for _ in range(len(col1_parts) - 1)]
        self.col1_box.bind(pos=self._upd_col1, size=self._upd_col1)

        pad_left = level * 10 + 10

        for i, (text, weight) in enumerate(col1_parts):
            align = 'center' if is_header else 'left'
            do_shorten = True
            if len(col1_parts) > 1 and i == 0:
                do_shorten = False
            lbl = Label(text=_make_text(text, highlight, markup=True),
                        size_hint_x=weight, halign=align, valign='middle',
                        color=C_TEXT,
                        padding=(pad_left if not is_header and i == 0 else 10, 0),
                        bold=is_header, font_size='14sp', shorten=do_shorten,
                        shorten_from='right', markup=True)
            lbl.bind(size=lbl.setter('text_size'))
            self.col1_box.add_widget(lbl)
        self.add_widget(self.col1_box)

        self.lbl2 = self._mk(c2, 0.15, is_header, 10)
        self.lbl3 = self._mk(c3, 0.10, is_header, 10)
        self.lbl4 = self._mk(c4, 0.15, is_header, 10)
        self.lbl5 = self._mk(c5, 0.15, is_header, 10)
        for l in (self.lbl2, self.lbl3, self.lbl4, self.lbl5):
            self.add_widget(l)

    def on_enter(self, *args):
        if not self.is_header:
            self._update_bg()

    def on_leave(self, *args):
        if not self.is_header:
            self._update_bg()

    def _update_bg(self):
        if self.is_selected:
            self.bg_color.rgba = C_SELECTED
        elif self.hovered:
            self.bg_color.rgba = C_ROW_HOVER
        else:
            self.bg_color.rgba = self.bg_normal

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
        
        if self.width > 2 and self.height > 2:
            self.line_rect.points = [self.x + 1, self.y, self.x + 1, self.top, self.x + self.width - 2, self.top, self.x + self.width - 2, self.y, self.x + 1, self.y]
            self.line_left.points = [self.x + 1, self.y, self.x + 1, self.top]
            
            if self.width > 30:
                avail = self.width - 30
                x0 = self.x + 30
                x1 = x0 + avail * 0.45
                x2 = x1 + avail * 0.15
                x3 = x2 + avail * 0.10
                x4 = x3 + avail * 0.15
                
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
            else:
                self.line_v1.points = []
                self.line_v2.points = []
                self.line_v3.points = []
                self.line_v4.points = []
        else:
            self.line_rect.points = []
            self.line_left.points = []
            self.line_v1.points = []
            self.line_v2.points = []
            self.line_v3.points = []
            self.line_v4.points = []

    def _upd_col1(self, *a):
        w, h = self.col1_box.width, self.col1_box.height
        x, y = self.col1_box.x, self.col1_box.y
        
        if w > 2 and h > 2:
            cx = x
            for i, weight in enumerate(self.col1_weights[:-1]):
                cx += (w * weight) / self.col1_total
                self.col1_lines[i].points = [cx, y, cx, y + h]
        else:
            for i in range(len(self.col1_lines)):
                self.col1_lines[i].points = []

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if touch.is_mouse_scrolling:
            return super().on_touch_down(touch)

        app = App.get_running_app()
        if not app:
            return super().on_touch_down(touch)

        is_right = getattr(touch, 'button', None) == 'right'
        now = time.time()
        is_double = getattr(touch, 'is_double_tap', False) or (now - self.last_click_time) < 0.3

        sys_modifiers = getattr(Window._system_keyboard, 'modifiers', [])
        shift_held = 'shift' in sys_modifiers
        ctrl_held = 'ctrl' in sys_modifiers

        if is_right:
            if not self.is_header:
                for child in self.walk():
                    if isinstance(child, Label) and child.collide_point(*touch.pos):
                        txt = child.text
                        clean_txt = (re.sub(r'\[.*?\]', '', txt)
                                     .replace('&amp;', '&')
                                     .replace('&bl;', '[')
                                     .replace('&br;', ']'))
                        if clean_txt and clean_txt.strip() not in ('-', ''):
                            Clipboard.copy(clean_txt)
                        break
                app.deselect_all()
            return True

        if is_double and not self.is_header:
            for child in self.walk():
                if isinstance(child, Label) and child.collide_point(*touch.pos):
                    txt = child.text
                    clean_txt = (re.sub(r'\[.*?\]', '', txt)
                                 .replace('&amp;', '&')
                                 .replace('&bl;', '[')
                                 .replace('&br;', ']'))
                    if clean_txt and clean_txt.strip() not in ('-', ''):
                        Clipboard.copy(clean_txt)
                    break
            self.last_click_time = 0
            return True

        self.last_click_time = now

        if not self.is_header:
            if ctrl_held:
                app.handle_ctrl_click(self)
            elif shift_held:
                app.handle_shift_click(self)
            else:
                app.select_row(self.node_type, self.db_id)

        if self.toggle_lbl.text in ('+', '-') and not self.is_header:
            nt = self.node_type
            did = self.db_id
            Clock.schedule_once(lambda dt: app.toggle_expand(nt, did), 0.05)

        return True

    def set_selected(self, state):
        if self.is_selected == state:
            return
        self.is_selected = state
        self._update_bg()