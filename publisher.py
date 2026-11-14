# publisher.py
import os
import sys
import json
import shutil
import re
import glob
import tkinter as tk
from tkinter import filedialog, messagebox

# --- ПРАВИЛЬНОЕ ОПРЕДЕЛЕНИЕ ПАПКИ ПРОЕКТА ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "publisher_config.json")

def get_icon_path():
    if getattr(sys, 'frozen', False):
        base = getattr(sys, '_MEIPASS', BASE_DIR)
        icon_path = os.path.join(base, "ico", "manager.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(base, "manager.ico")
    else:
        icon_path = os.path.join(BASE_DIR, "ico", "manager.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(BASE_DIR, "manager.ico")
    return icon_path

class PublisherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Публикатор обновлений Менеджера контактов")
        
        window_width = 600
        window_height = 520
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        if center_y < 0: center_y = 0
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        self.root.resizable(False, False)

        icon_path = get_icon_path()
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(default=icon_path)
            except Exception as e:
                print(f"Не удалось установить иконку: {e}")

        # Проверка файлов
        missing_files = []
        for f in ["version.py", "manager_installer.iss", "version_info.txt", "version.json"]:
            if not os.path.exists(os.path.join(BASE_DIR, f)):
                missing_files.append(f)
                
        if missing_files:
            messagebox.showwarning(
                "Внимание", 
                f"Не найдены файлы проекта в папке:\n{BASE_DIR}\n\n"
                f"Отсутствуют: {', '.join(missing_files)}\n\n"
                "Пожалуйста, положите этот EXE в корень проекта."
            )

        self.config = self._load_config()
        self.network_path = tk.StringVar(value=self.config.get("network_path", ""))

        self._build_ui()

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self):
        self.config["network_path"] = self.network_path.get()
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Ошибка сохранения конфига:", e)

    def _build_ui(self):
        frame1 = tk.LabelFrame(self.root, text=" Шаг 1: Обновление локальных файлов ", padx=10, pady=10)
        frame1.pack(fill="x", padx=10, pady=10)

        tk.Label(frame1, text="Новая версия (например, 1.2.0):").pack(anchor="w")
        self.ver_entry = tk.Entry(frame1, width=20, font=("Arial", 12))
        self.ver_entry.pack(anchor="w", pady=5)
        self.ver_entry.insert(0, "1.2.0")

        btn_update = tk.Button(frame1, text="Обновить файлы (version.py, .iss, .txt, .json)", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=self.update_version_files)
        btn_update.pack(fill="x", pady=5)

        frame2 = tk.LabelFrame(self.root, text=" Шаг 2: Публикация в сеть (после сборки установщика) ", padx=10, pady=10)
        frame2.pack(fill="x", padx=10, pady=10)

        tk.Label(frame2, text="Сетевая папка для обновлений:").pack(anchor="w")
        
        path_frame = tk.Frame(frame2)
        path_frame.pack(fill="x", pady=5)
        
        self.path_entry = tk.Entry(path_frame, textvariable=self.network_path, width=50)
        self.path_entry.pack(side="left", fill="x", expand=True)
        
        btn_browse = tk.Button(path_frame, text="Обзор...", command=self.browse_folder)
        btn_browse.pack(side="left", padx=(5, 0))

        tk.Label(frame2, text="Что нового (Release Notes):").pack(anchor="w", pady=(10, 0))
        self.notes_text = tk.Text(frame2, height=4, width=60, font=("Arial", 10))
        self.notes_text.pack(fill="x", pady=5)
        
        default_notes = "- Исправлены ошибки\n- Улучшена стабильность"
        try:
            local_json = os.path.join(BASE_DIR, "version.json")
            if os.path.exists(local_json):
                with open(local_json, 'r', encoding='utf-8') as f:
                    vdata = json.load(f)
                    if vdata.get('release_notes'):
                        raw_notes = vdata['release_notes']
                        raw_notes = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw_notes)
                        raw_notes = re.sub(r'[^\S\r\n]', ' ', raw_notes)
                        raw_notes = raw_notes.replace('\r\n', '\n').replace('\r', '\n')
                        raw_notes = re.sub(r' +', ' ', raw_notes)
                        default_notes = raw_notes
        except Exception:
            pass
            
        self.notes_text.insert("1.0", default_notes)

        btn_publish = tk.Button(frame2, text="Скопировать установщик и обновить version.json в сети", bg="#2196F3", fg="white", font=("Arial", 10, "bold"), command=self.publish_release)
        btn_publish.pack(fill="x", pady=5)

        self.status_lbl = tk.Label(self.root, text="Готов к работе", fg="gray")
        self.status_lbl.pack(side="bottom", pady=5)

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Выберите сетевую папку для обновлений")
        if folder:
            folder = os.path.normpath(folder)
            self.network_path.set(folder)
            self._save_config()

    def update_version_files(self):
        version = self.ver_entry.get().strip()
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            messagebox.showerror("Ошибка", "Неверный формат версии. Ожидается X.Y.Z (например, 1.2.0)")
            return

        v_parts = version.split('.')
        try:
            v1, v2, v3 = int(v_parts[0]), int(v_parts[1]), int(v_parts[2])
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат версии.")
            return
            
        v_tuple = f"({v1}, {v2}, {v3}, 0)"

        files_updated = 0
        errors = []

        # 1. version.py
        path_py = os.path.join(BASE_DIR, "version.py")
        try:
            with open(path_py, 'r', encoding='utf-8') as f:
                content = f.read()
            content = re.sub(r'APP_VERSION\s*=\s*".*?"', f'APP_VERSION = "{version}"', content)
            with open(path_py, 'w', encoding='utf-8') as f:
                f.write(content)
            files_updated += 1
        except Exception as e:
            errors.append(f"version.py: {e}")

        # 2. manager_installer.iss
        path_iss = os.path.join(BASE_DIR, "manager_installer.iss")
        try:
            with open(path_iss, 'r', encoding='utf-8') as f:
                content = f.read()
            content = re.sub(r'#define\s+MyAppVersion\s+".*?"', f'#define MyAppVersion "{version}"', content)
            with open(path_iss, 'w', encoding='utf-8') as f:
                f.write(content)
            files_updated += 1
        except Exception as e:
            errors.append(f"manager_installer.iss: {e}")

        # 3. version_info.txt
        path_txt = os.path.join(BASE_DIR, "version_info.txt")
        try:
            with open(path_txt, 'r', encoding='utf-8') as f:
                content = f.read()
            clean_ver = f"{v1}.{v2}.{v3}"
            content = re.sub(r'filevers=\(.*?\)', f'filevers={v_tuple}', content)
            content = re.sub(r'prodvers=\(.*?\)', f'prodvers={v_tuple}', content)
            content = re.sub(r"StringStruct\(u'FileVersion', u'.*?'\)", f"StringStruct(u'FileVersion', u'{clean_ver}.0')", content)
            content = re.sub(r"StringStruct\(u'ProductVersion', u'.*?'\)", f"StringStruct(u'ProductVersion', u'{clean_ver}.0')", content)
            with open(path_txt, 'w', encoding='utf-8') as f:
                f.write(content)
            files_updated += 1
        except Exception as e:
            errors.append(f"version_info.txt: {e}")

        # 4. Локальный version.json
        path_json = os.path.join(BASE_DIR, "version.json")
        try:
            if os.path.exists(path_json):
                with open(path_json, 'r', encoding='utf-8') as f:
                    vdata = json.load(f)
                
                vdata['latest_version'] = version
                
                if 'download_url' in vdata and vdata['download_url']:
                    vdata['download_url'] = re.sub(r'ManagerContacts_Setup_v\d+\.\d+\.\d+\.exe', f'ManagerContacts_Setup_v{version}.exe', vdata['download_url'])
                else:
                    vdata['download_url'] = f"ManagerContacts_Setup_v{version}.exe"

                with open(path_json, 'w', encoding='utf-8') as f:
                    json.dump(vdata, f, ensure_ascii=False, indent=4)
                files_updated += 1
            else:
                vdata = {
                    "latest_version": version,
                    "download_url": f"ManagerContacts_Setup_v{version}.exe",
                    "release_notes": "- Исправлены ошибки\n- Улучшена стабильность"
                }
                with open(path_json, 'w', encoding='utf-8') as f:
                    json.dump(vdata, f, ensure_ascii=False, indent=4)
                files_updated += 1
        except Exception as e:
            errors.append(f"version.json: {e}")

        if files_updated == 4:
            self.status_lbl.config(text=f"Все 4 файла обновлены до версии {version}", fg="green")
            messagebox.showinfo("Успех", f"Все 4 файла успешно обновлены до версии {version}.\nТеперь можете собирать EXE и установщик.")
        else:
            self.status_lbl.config(text="Ошибка при обновлении", fg="red")
            messagebox.showerror("Ошибка", "Не удалось обновить некоторые файлы:\n" + "\n".join(errors))

    def publish_release(self):
        version = self.ver_entry.get().strip()
        net_path = self.network_path.get().strip()

        if not net_path:
            messagebox.showwarning("Внимание", "Выберите сетевую папку (Шаг 2)!")
            return

        if not os.path.isdir(net_path):
            messagebox.showerror("Ошибка", f"Папка не найдена или недоступна:\n{net_path}")
            return

        installer_name = f"ManagerContacts_Setup_v{version}.exe"
        local_installer_dir = os.path.join(BASE_DIR, "installer_output")
        installer_src = os.path.join(local_installer_dir, installer_name)

        if not os.path.exists(installer_src):
            messagebox.showerror("Ошибка", f"Установщик не найден:\n{installer_src}\n\nСначала соберите его в Inno Setup.")
            return

        try:
            self.status_lbl.config(text="Копирование установщика...", fg="blue")
            self.root.update()

            installer_dst = os.path.join(net_path, installer_name)
            shutil.copy2(installer_src, installer_dst)

            self.status_lbl.config(text="Удаление старых сборок...", fg="blue")
            self.root.update()

            net_deleted = []
            old_installers = glob.glob(os.path.join(net_path, "ManagerContacts_Setup_v*.exe"))
            for old_file in old_installers:
                if os.path.basename(old_file) != installer_name:
                    try:
                        os.remove(old_file)
                        net_deleted.append(os.path.basename(old_file))
                    except Exception as e:
                        print(f"Не удалось удалить старый файл в сети {old_file}: {e}")

            local_deleted = []
            if os.path.isdir(local_installer_dir):
                local_installers = glob.glob(os.path.join(local_installer_dir, "ManagerContacts_Setup_v*.exe"))
                for old_file in local_installers:
                    if os.path.basename(old_file) != installer_name:
                        try:
                            os.remove(old_file)
                            local_deleted.append(os.path.basename(old_file))
                        except Exception as e:
                            print(f"Не удалось удалить локальный файл {old_file}: {e}")

            self.status_lbl.config(text="Запись version.json...", fg="blue")
            self.root.update()

            notes = self.notes_text.get("1.0", "end-1c").strip()
            
            notes = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', notes)
            notes = re.sub(r'[^\S\r\n]', ' ', notes)
            notes = notes.replace('\r\n', '\n').replace('\r', '\n')
            notes = re.sub(r' +', ' ', notes)
            
            download_url = os.path.join(net_path, installer_name)
            
            version_data = {
                "latest_version": version,
                "download_url": download_url,
                "release_notes": notes
            }

            json_path = os.path.join(net_path, "version.json")
            
            if os.path.exists(json_path):
                try:
                    os.remove(json_path) 
                except Exception as e:
                    raise Exception(f"Не удалось удалить старый version.json: {e}")

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(version_data, f, ensure_ascii=False, indent=4)

            self.status_lbl.config(text=f"Успешно опубликовано v{version}", fg="green")
            
            report_msg = ""
            if net_deleted:
                report_msg += "\n\nУдалены старые сборки в сети:\n- " + "\n- ".join(net_deleted)
            if local_deleted:
                report_msg += "\n\nУдалены старые сборки локально (installer_output):\n- " + "\n- ".join(local_deleted)
            
            messagebox.showinfo(
                "Успех", 
                f"Обновление успешно опубликовано!\n\n"
                f"Скопирован: {installer_name}\n"
                f"Обновлен: version.json{report_msg}"
            )
            
        except Exception as e:
            self.status_lbl.config(text="Ошибка публикации", fg="red")
            messagebox.showerror("Ошибка", f"Не удалось опубликовать:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PublisherApp(root)
    root.mainloop()