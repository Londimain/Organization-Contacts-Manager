# settings.py
import os
import sys
import json

def app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def data_dir():
    path = os.path.join(os.getenv('APPDATA') or os.path.expanduser('~'), 'ManagerContacts')
    os.makedirs(path, exist_ok=True)
    return path

SETTINGS_PATH = os.path.join(data_dir(), 'settings.json')
LOG_PATH = os.path.join(data_dir(), 'app.log')

DEFAULT_SETTINGS = {
    'window_size': [1400, 900],
    'maximized': True,
    'last_export_dir': '',
    'db_path': '',  # <--- НОВОЕ: путь к сетевой базе (если пусто, то локально)
}

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {**DEFAULT_SETTINGS, **data}
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)

def save_settings(settings):
    try:
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save settings: {e}")

def get_db_path():
    s = load_settings()
    path = s.get('db_path', '')
    if path:
        return path
    return os.path.join(app_dir(), 'contacts.db')

DB_PATH = get_db_path()