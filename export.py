# export.py
import os
import re
import logging

log = logging.getLogger('export')


def get_desktop_path():
    for name in ("Desktop", "Рабочий стол"):
        p = os.path.join(os.path.expanduser("~"), name)
        if os.path.exists(p):
            return p
    return os.path.expanduser("~")


def _import_openpyxl():
    try:
        import openpyxl
        return openpyxl
    except ImportError:
        raise RuntimeError(
            "Библиотека openpyxl не установлена.\n"
            "Установите её командой: pip install openpyxl")

# export.py
# ... (ваши импорты)

def export_to_excel(db, filepath=None, only_rp_id=None, only_org_id=None):
    openpyxl = _import_openpyxl()
    # Импортируем нужные стили, включая PatternFill для заливки
    from openpyxl.styles import Border, Side, Alignment, Font, PatternFill

    if not filepath:
        export_dir = os.path.join(get_desktop_path(), "Экспорт контактов")
        os.makedirs(export_dir, exist_ok=True)
        filepath = os.path.join(export_dir, "contacts_export.xlsx")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Контакты"

    ws.sheet_properties.outlinePr.summaryBelow = False

    thin = Border(*[Side(style='thin')] * 4)
    bold = Font(bold=True)
    al = Alignment(horizontal='left', vertical='center')
    ac = Alignment(horizontal='center', vertical='center')

    # --- НОВОЕ: Создаем стили заливки и шрифтов для разных типов ---
    # Цвета взяты из app.py для единого стиля
    fill_rp = PatternFill(start_color="6D015F", end_color="6D015F", fill_type="solid")
    font_rp = Font(color="FFFFFF", bold=True) # Белый текст на фиолетовом

    fill_org = PatternFill(start_color="FFAA55", end_color="FFAA55", fill_type="solid")
    font_org = Font(color="000000", bold=True) # Черный текст на оранжевом

    fill_store = PatternFill(start_color="458A00", end_color="458A00", fill_type="solid")
    font_store = Font(color="FFFFFF", bold=True) # Белый текст на зеленом
    
    fill_contact = PatternFill(start_color="AAAAAA", end_color="AAAAAA", fill_type="solid")
    font_contact = Font(color="000000") # Черный текст на сером
    
    fill_header = PatternFill(start_color="55AAFF", end_color="55AAFF", fill_type="solid")
    font_header = Font(color="000000", bold=True)
    # -------------------------------------------------------------

    ws.append(["Тип", "Наименование / ФИО", "Город / Договор",
               "Дата договора", "Адрес / Должность", "Телефон"])
    
    row_idx = 1

    for rp in db.get_responsible_persons():
        if only_rp_id is not None and rp['id'] != only_rp_id and only_org_id is None:
            continue
        row_idx += 1
        ws.append(["Ответственный", rp['full_name'], rp['city'] or '-', "",
                   rp['position'] or '-', rp['phone'] or '-'])
        
        for org in db.get_organizations(rp['id']):
            if only_org_id is not None and org['id'] != only_org_id:
                continue
            row_idx += 1
            ws.append(["Организация", org['name'], org['contract_number'] or '-',
                       org['contract_date'] or '-', org['address'] or '-',
                       org['phone'] or '-'])
            ws.row_dimensions[row_idx].outlineLevel = 1
            
            for store in db.get_stores(org['id']):
                row_idx += 1
                ws.append(["Магазин", store['name'], "", "",
                           store['unloading_address'] or '-', store['phone'] or '-'])
                ws.row_dimensions[row_idx].outlineLevel = 2
                
                for c in db.get_contacts(store['id'], 'decision_maker'):
                    row_idx += 1
                    ws.append(["ЛПР", c['full_name'] or '-', "", "",
                               c['position'] or '-', c['phone'] or '-'])
                    ws.row_dimensions[row_idx].outlineLevel = 3
                    
                for c in db.get_contacts(store['id'], 'payment'):
                    row_idx += 1
                    ws.append(["Оплата", c['full_name'] or '-', "", "",
                               c['position'] or '-', c['phone'] or '-'])
                    ws.row_dimensions[row_idx].outlineLevel = 3

    # --- НОВОЕ: Применяем стили и цвета к ячейкам ---
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=6):
        first_cell = row[0]
        type_val = str(first_cell.value) if first_cell.value else ""
        
        for cell in row:
            cell.border = thin
            cell.alignment = al

        # Стилизация первой колонки ("Тип") в зависимости от значения
        if first_cell.row == 1:
            first_cell.fill = fill_header
            first_cell.font = font_header
            first_cell.alignment = ac
        elif type_val == "Ответственный":
            first_cell.fill = fill_rp
            first_cell.font = font_rp
        elif type_val == "Организация":
            first_cell.fill = fill_org
            first_cell.font = font_org
        elif type_val == "Магазин":
            first_cell.fill = fill_store
            first_cell.font = font_store
        elif type_val in ("ЛПР", "Оплата"):
            first_cell.fill = fill_contact
            first_cell.font = font_contact
            
        # Шапку таблицы (первую строку) делаем жирной и по центру везде
        if first_cell.row == 1:
            for cell in row:
                cell.font = font_header
                cell.alignment = ac
    # ------------------------------------------------

    # Автоподбор ширины столбцов
    for col_letter in 'ABCDEF':
        max_len = 0
        for cell in ws[col_letter]:
            if cell.value is None:
                continue
            for line in str(cell.value).split('\n'):
                max_len = max(max_len, len(line))
        width = max(max_len + 5, 12)
        ws.column_dimensions[col_letter].width = width

    wb.save(filepath)
    log.info(f"Exported to {filepath}")
    return filepath

def _get_cell_color_type(cell):
    """Определяет тип цвета заливки ячейки: 'yellow', 'orange' или None."""
    if not cell.fill:
        return None
    fg = cell.fill.fgColor
    
    # Прямой RGB
    if fg.type == 'rgb' and fg.rgb:
        hex_color = str(fg.rgb).upper()
        if len(hex_color) == 8:
            hex_color = hex_color[2:] # Отрезаем альфа-канал
        if len(hex_color) == 6:
            try:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                # Желтый
                if r > 200 and g > 180 and b < 120:
                    return 'yellow'
                # Оранжевый
                if r > 200 and 100 < g < 240 and b < 160:
                    return 'orange'
            except ValueError:
                pass
                
    # Тематический цвет (Theme)
    elif fg.type == 'theme':
        if fg.theme == 7:  # Золотой/Желтый
            return 'yellow'
        if fg.theme == 5:  # Оранжевый
            return 'orange'
            
    return None


def import_from_excel(db, filepath):
    if filepath.lower().endswith('.xls'):
        raise ValueError("Формат .xls не поддерживается. Откройте файл в Excel и сохраните как .xlsx")
    
    openpyxl = _import_openpyxl()
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active

    added = updated = skipped = 0

    def _clean(v):
        v = '' if v is None else str(v).strip()
        return '' if v == '-' else v

    if ws.max_column == 1:
        cur_rp_id = None
        cur_org_id = None
        
        # Надежный паттерн для поиска адресов и торговых точек
        address_pattern = re.compile(
            r'(^склад$|^маг\.?$|г\.|ул\.|д\.|обл|р-н|р-он|м-н|маг\.|маг |склад|аг\.|пер\.|пр-т|пр\.|ш\.|тракт|п\.|с/с|район|пос\.|пл\.|/с|пав|тц|кв\.|корп|дом|мкр)',
            re.IGNORECASE
        )

        for row in ws.iter_rows(min_row=1, max_col=1):
            cell = row[0]
            if not cell.value:
                continue

            text = _clean(cell.value)
            if not text or text.lower() in ('пункты разгрузки', 'пункты разгрузок'):
                continue

            color_type = _get_cell_color_type(cell)
            
            node_type = None
            
            # 1. Приоритет - явный цвет
            if color_type == 'yellow':
                node_type = 'rp'
            elif color_type == 'orange':
                node_type = 'org'
            else:
                # 2. Если цвета нет - анализируем текст
                # Если есть маркеры адреса - это магазин
                if address_pattern.search(text):
                    node_type = 'store'
                else:
                    # Если адреса нет - это организация (например, ИП Линник, Бобруйская Оптовая База)
                    node_type = 'org'

            try:
                if node_type == 'rp':
                    existing = db.find_rp_by_name(text)
                    if existing:
                        cur_rp_id = existing['id']
                        updated += 1
                    else:
                        cur_rp_id = db.add_responsible_person(text, "", "", "")
                        added += 1
                    cur_org_id = None
                    
                elif node_type == 'org':
                    if cur_rp_id is None:
                        existing_rp = db.find_rp_by_name("Импортированные ответственные")
                        if not existing_rp:
                            cur_rp_id = db.add_responsible_person("Импортированные ответственные", "", "", "")
                        else:
                            cur_rp_id = existing_rp['id']

                    existing = db.find_org_by_name(cur_rp_id, text)
                    if existing:
                        cur_org_id = existing['id']
                        updated += 1
                    else:
                        cur_org_id = db.add_organization(cur_rp_id, text, "", "", "", "")
                        added += 1
                        
                elif node_type == 'store':
                    if cur_org_id is None:
                        if cur_rp_id is None:
                            existing_rp = db.find_rp_by_name("Импортированные ответственные")
                            if not existing_rp:
                                cur_rp_id = db.add_responsible_person("Импортированные ответственные", "", "", "")
                            else:
                                cur_rp_id = existing_rp['id']
                        
                        existing_org = db.find_org_by_name(cur_rp_id, "Импортированные организации")
                        if not existing_org:
                            cur_org_id = db.add_organization(cur_rp_id, "Импортированные организации", "", "", "", "")
                        else:
                            cur_org_id = existing_org['id']
                    
                    existing = db.find_store_by_name(cur_org_id, text)
                    if existing:
                        updated += 1
                    else:
                        db.add_store(cur_org_id, text, "", "")
                        added += 1
                        
            except Exception as e:
                log.warning(f"Import row skipped: {e}")
                skipped += 1
                
        log.info(f"Imported (smart color parser): added={added}, updated={updated}, skipped={skipped}")
        return added, updated, skipped

    # Логика для многоколоночного файла (осталась без изменений)
    cur_rp_id = cur_org_id = cur_store_id = None
    for row in ws.iter_rows(min_row=2, values_only=True):
        pass

    log.info(f"Imported: added={added}, updated={updated}, skipped={skipped}")
    return added, updated, skipped