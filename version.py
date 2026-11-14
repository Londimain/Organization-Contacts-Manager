# version.py
# Единая точка правки метаданных приложения.

APP_NAME        = "Менеджер контактов организаций"
APP_VERSION     = "1.1.2"
APP_BUILD_DATE  = "2026-11-15"
APP_DESCRIPTION = (
    "Профессиональный инструмент для управления базой данных контактов, "
    "организаций и торговых точек с расширенными возможностями."
)

DEVELOPER       = "Ильенков С.М."
ORGANIZATION    = 'ОАО "Компания МогНат"'
REPO_URL        = "https://github.com/Londimain/Organization-Contacts-Manager"

WINDOW_TITLE    = f"{APP_NAME} v{APP_VERSION}"

def build_about_text():
    return f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; color: #f0f0f0;">
        <h1 style="text-align: center; color: #55aaff; margin-bottom: 5px;">{APP_NAME}</h1>
        <p style="text-align: center; color: #aaaaaa; margin-top: 0;">
            Версия: <b>{APP_VERSION}</b> (сборка от {APP_BUILD_DATE})
        </p>
        
        <p style="text-align: justify; font-style: italic; color: #d0d0d0;">
            {APP_DESCRIPTION}
        </p>

        <h2 style="color: #458a00; border-bottom: 1px solid #458a00; padding-bottom: 3px;">🚀 Основные возможности</h2>
        <ul style="line-height: 1.5;">
            <li><b style="color: #6D015F;">Иерархическая структура:</b> Ответственные лица ➔ Организации ➔ Магазины ➔ Контакты (ЛПР и Оплата).</li>
            <li><b style="color: #ffaa55;">Цветовое кодирование</b> уровней для быстрой навигации.</li>
            <li><b>Сквозной поиск</b> по всей базе. При очистке поиска дерево возвращается в исходное состояние.</li>
            <li><b>Копирование данных</b> с визуальным откликом (строка кратковременно вспыхивает зеленым).</li>
            <li><b>Экспорт в Excel:</b> файл сохраняется с автоподбором ширины столбцов и рамками.</li>
            <li><b>Умный импорт из Excel:</b> распознавание иерархии по цвету заливки ячеек.</li>
        </ul>

        <h2 style="color: #55aaff; border-bottom: 1px solid #55aaff; padding-bottom: 3px;">🌐 Сетевая работа и безопасность</h2>
        <ul style="line-height: 1.5;">
            <li>Поддержка <b>локальной и сетевой</b> базы данных. Смена пути через меню «Настройки».</li>
            <li><b>Индикатор текущей базы</b> в нижней панели (Локальная / Сетевая).</li>
            <li><b>Мгновенное обновление</b> интерфейса при изменении записей (без перезагрузки дерева).</li>
            <li>Фоновое подключение к сети (программа <b>не зависает</b> при медленном соединении).</li>
            <li><b>Автосинхронизация:</b> если коллега изменит сетевую базу, программа сама подтянет обновления.</li>
            <li><b>Защита паролем</b> при запуске программы.</li>
        </ul>

        <h2 style="color: #ffaa55; border-bottom: 1px solid #ffaa55; padding-bottom: 3px;">⌨️ Горячие клавиши</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 3px;"><code style="background: #2d2d2d; color: #ffaa55; padding: 2px 5px; border-radius: 3px;">Ctrl+F</code></td>
                <td style="padding: 3px;">Фокус в поле поиска</td>
            </tr>
            <tr>
                <td style="padding: 3px;"><code style="background: #2d2d2d; color: #ffaa55; padding: 2px 5px; border-radius: 3px;">Ctrl+C</code></td>
                <td style="padding: 3px;">Скопировать выделенные строки для Excel</td>
            </tr>
            <tr>
                <td style="padding: 3px;"><code style="background: #2d2d2d; color: #ffaa55; padding: 2px 5px; border-radius: 3px;">Enter</code></td>
                <td style="padding: 3px;">Редактировать выбранную строку</td>
            </tr>
            <tr>
                <td style="padding: 3px;"><code style="background: #2d2d2d; color: #ffaa55; padding: 2px 5px; border-radius: 3px;">Insert</code></td>
                <td style="padding: 3px;">Добавить элемент</td>
            </tr>
            <tr>
                <td style="padding: 3px;"><code style="background: #2d2d2d; color: #ffaa55; padding: 2px 5px; border-radius: 3px;">Delete</code></td>
                <td style="padding: 3px;">Удалить выбранный элемент</td>
            </tr>
        </table>

        <h2 style="color: #aaaaaa; border-bottom: 1px solid #aaaaaa; padding-bottom: 3px;">🛠 Техническая информация</h2>
        <p style="color: #aaaaaa; font-size: 12px;">
            Технологии: Python 3.8+, PySide6 (Qt6), SQLite3, OpenPyXL.<br>
            База данных по умолчанию: <code>contacts.db</code><br><br>
            Разработчик: <b>{DEVELOPER}</b><br>
            Организация: {ORGANIZATION}
        </p>
    </div>
    """.strip()