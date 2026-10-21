# export.py
import openpyxl
from openpyxl.styles import Border, Side, Alignment, Font
import os

def get_desktop_path():
    """Возвращает путь к рабочему столу пользователя."""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.exists(desktop):
        return desktop
    
    # Для русскоязычных систем
    desktop_ru = os.path.join(os.path.expanduser("~"), "Рабочий стол")
    if os.path.exists(desktop_ru):
        return desktop_ru
        
    # Если ничего не нашли, сохраняем в домашнюю директорию
    return os.path.expanduser("~")

def export_to_excel(db, filepath=None):
    if not filepath:
        # Определяем папку "Экспорт контактов" на рабочем столе
        desktop = get_desktop_path()
        export_dir = os.path.join(desktop, "Экспорт контактов")
        
        # Создаем папку, если её нет
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
            
        # Фиксированное имя файла (без даты)
        filename = "contacts_export.xlsx"
        filepath = os.path.join(export_dir, filename)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Контакты"

    # Настройка стилей
    thin_border = Border(left=Side(style='thin'), 
                         right=Side(style='thin'), 
                         top=Side(style='thin'), 
                         bottom=Side(style='thin'))
    header_font = Font(bold=True)
    align_left = Alignment(horizontal='left', vertical='center')
    align_center = Alignment(horizontal='center', vertical='center')

    # Заголовки таблицы
    headers = ["Тип", "Наименование / ФИО", "Город", "Адрес / Должность", "Телефон"]
    ws.append(headers)

    # Собираем данные из БД
    for rp in db.get_responsible_persons():
        ws.append(["Ответственный", rp['full_name'], rp['city'] or '-', rp['position'] or '-', rp['phone'] or '-'])
        for org in db.get_organizations(rp['id']):
            ws.append(["Организация", org['name'], "", org['address'] or '-', org['phone'] or '-'])
            for store in db.get_stores(org['id']):
                ws.append(["Магазин", store['name'], "", store['unloading_address'] or '-', store['phone'] or '-'])
                for c in db.get_contacts(store['id'], 'decision_maker'):
                    ws.append(["ЛПР", c['full_name'] or '-', "", c['position'] or '-', c['phone'] or '-'])
                for c in db.get_contacts(store['id'], 'payment'):
                    ws.append(["Оплата", c['full_name'] or '-', "", c['position'] or '-', c['phone'] or '-'])

    # Применяем стили ко всем ячейкам
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=5):
        for cell in row:
            cell.border = thin_border
            if cell.row == 1:
                cell.font = header_font
                cell.alignment = align_center
            else:
                cell.alignment = align_left

    # Настройка ширины колонок
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 35
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 35
    ws.column_dimensions['E'].width = 20

    # Сохраняем файл (openpyxl автоматически перезапишет его, если он существует)
    wb.save(filepath)
    return filepath