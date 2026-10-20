# ============================================================
#  Отключаем эмуляцию multitouch по правому клику
# ============================================================
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,disable_multitouch')

from app import ContactManagerApp

if __name__ == '__main__':
    ContactManagerApp().run()