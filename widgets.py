from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, Line
from constants import *
import time

class CustomButton(Button):
    def __init__(self, **kwargs):
        kwargs['font_size'] = '15sp'
        kwargs['bold'] = True
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = C_BTN
        self.disabled_color = C_TEXT_DISABLED
        
        self.bind(disabled=self._update_disabled_color)
        self.bind(state=self._update_state_color)
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        
        with self.canvas.after:
            self.border_color = Color(*C_RED_LINE)
            self.border_rect = Line(width=1)
            
        self._update_disabled_color(self, self.disabled)
        self._update_canvas()

    def _update_canvas(self, *args):
        if hasattr(self, 'border_rect'):
            self.border_rect.rectangle = (self.x + 1, self.y + 1, self.width - 2, self.height - 2)

    def _update_disabled_color(self, instance, value):
        if value:
            self.background_color = C_BTN_DISABLED
        else:
            self._update_state_color(self, self.state)

    def _update_state_color(self, instance, value):
        if self.disabled:
            return
        if value == 'down':
            self.background_color = C_BTN_DOWN
        else:
            self.background_color = C_BTN


class RootLayout(BoxLayout):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            if hasattr(app, 'scroll') and app.scroll.collide_point(*touch.pos):
                hit_row = False
                for row in getattr(app, 'current_rows', []):
                    if row.collide_point(*touch.pos):
                        hit_row = True
                        break
                if not hit_row:
                    app.deselect_all()
            return super().on_touch_down(touch)
        return super().on_touch_down(touch)


class ExcelRow(BoxLayout):
    def __init__(self, app, node_type, db_id, level, col1_parts, col_city, col2, col3,
                 expandable=False, expanded=False, is_header=False, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=32, **kwargs)
        self.app = app
        self.node_type = node_type
        self.db_id = db_id
        self.level = level
        self.is_header = is_header
        self.is_selected = False
        self.last_click_time = 0
        self._expand_event = None

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

        self.bind(pos=self._update_canvas, size=self._update_canvas)

        self.toggle_lbl = Label(
            text="", size_hint_x=None, width=30, color=C_TEXT, bold=True
        )
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
            
        self.col1_box.bind(pos=self._update_col1_canvas, size=self._update_col1_canvas)
        
        pad_left = level * 15 + 10
        for i, (text, weight) in enumerate(col1_parts):
            lbl = Label(
                text=text, size_hint_x=weight, halign='left', valign='middle',
                color=C_TEXT, padding=(pad_left if i == 0 else 10, 0), 
                bold=is_header, font_size='14sp', shorten=True, shorten_from='right'
            )
            lbl.bind(size=lbl.setter('text_size'))
            self.col1_box.add_widget(lbl)
            
        self.add_widget(self.col1_box)

        self.lbl_city = Label(
            text=col_city, size_hint_x=0.15, halign='left', valign='middle',
            color=C_TEXT if is_header else C_TEXT_DIM, padding=(10, 0), font_size='14sp',
            shorten=True, shorten_from='right'
        )
        self.lbl_city.bind(size=self.lbl_city.setter('text_size'))
        self.add_widget(self.lbl_city)

        self.lbl2 = Label(
            text=col2, size_hint_x=0.25, halign='left', valign='middle',
            color=C_TEXT if is_header else C_TEXT_DIM, padding=(10, 0), 
            font_size='14sp', shorten=True, shorten_from='right'
        )
        self.lbl2.bind(size=self.lbl2.setter('text_size'))
        self.add_widget(self.lbl2)

        self.lbl3 = Label(
            text=col3, size_hint_x=0.15, halign='left', valign='middle',
            color=C_TEXT if is_header else C_TEXT_DIM, padding=(10, 0), 
            font_size='14sp', shorten=True, shorten_from='right'
        )
        self.lbl3.bind(size=self.lbl3.setter('text_size'))
        self.add_widget(self.lbl3)

    def _update_canvas(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        
        self.line_rect.rectangle = (self.x + 1, self.y, self.width - 2, self.height)
        self.line_left.points = [self.x + 1, self.y, self.x + 1, self.top]
        
        avail_w = self.width - 30
        x0 = self.x + 30
        x1 = x0 + avail_w * 0.45
        x2 = x1 + avail_w * 0.15
        x3 = x2 + avail_w * 0.25
        
        if self.node_type == 'rp':
            self.line_v1.points = [x1, self.y, x1, self.top]
            self.line_v2.points = [x2, self.y, x2, self.top]
        else:
            self.line_v1.points = [] 
            self.line_v2.points = [x2, self.y, x2, self.top]
            
        self.line_v3.points = [x3, self.y, x3, self.top]

    def _update_col1_canvas(self, *args):
        w = self.col1_box.width
        h = self.col1_box.height
        x = self.col1_box.x
        y = self.col1_box.y
        
        current_x = x
        for i, weight in enumerate(self.col1_weights[:-1]):
            current_x += (w * weight) / self.col1_total
            self.col1_lines[i].points = [current_x, y, current_x, y + h]

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            current_time = time.time()
            is_double = (current_time - self.last_click_time) < 0.3
            is_right = getattr(touch, 'button', None) == 'right'
            
            if is_double or is_right or touch.is_double_tap:
                if self._expand_event:
                    self._expand_event.cancel()
                    self._expand_event = None
                
                for child in self.walk():
                    if isinstance(child, Label) and child.collide_point(*touch.pos):
                        txt = child.text
                        if txt and txt.strip() != '-' and txt.strip() != '':
                            Clipboard.copy(txt)
                            orig_color = child.color
                            child.color = (0.5, 1, 0.5, 1)
                            Clock.schedule_once(lambda dt: setattr(child, 'color', orig_color), 0.3)
                        break
                
                self.last_click_time = 0
                return True

            self.last_click_time = current_time
            
            if not self.is_header:
                self.app.select_row(self.node_type, self.db_id)
            
            if self.toggle_lbl.text in ('+', '-') and not is_right:
                if self._expand_event:
                    self._expand_event.cancel()
                
                self._expand_event = Clock.schedule_once(
                    lambda dt: self.app.toggle_expand(self.node_type, self.db_id), 0.25
                )
            
            return True
        return super().on_touch_down(touch)

    def set_selected(self, state):
        self.is_selected = state
        self.bg_color.rgba = C_SELECTED if state else self.bg_normal