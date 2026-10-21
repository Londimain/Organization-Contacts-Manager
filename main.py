# main.py
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,disable_multitouch')
Config.set('kivy', 'exit_on_escape', '0')

from logger import setup_logging
setup_logging()

from app import ContactManagerApp

if __name__ == '__main__':
    ContactManagerApp().run()