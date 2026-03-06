# i18n.py

_current_lang = "ru"

TRANSLATIONS = {
    "ru": {
        "app_title": "Маркорез — Умная нарезка марок",
        "tab_auto": "Авто-поиск",
        "tab_manual": "Ручной",
        "btn_select_file": "Выбрать файл",
        "btn_draw_mode": "✏️ Режим рисования",
        "btn_find": "🔍 Найти",
        "btn_divide": "✂️ Разделить",
        "btn_extract": "✂️ Извлечь",
        "btn_save_all": "💾 Сохранить все",
        "btn_clear_all": "🗑️ Очистить все",
        "btn_gh_check": "🌐  Проект на GitHub",
        "btn_gh_releases": "📦  Скачать обновления (Релизы)",
        "btn_tg_contact": "💬  Связаться в Telegram",
        "info_how_it_works": "ℹ️  Как это работает",
        "info_desc": (
            "Используйте Авто-поиск для автоматического\n"
            "нахождения марок или Режим рисования,\n"
            "чтобы вручную выделить пропущенные.\n"
            "Нажмите Извлечь для обрезки."
        ),
        "upload_title": "Загрузить скан",
        "upload_desc": "JPEG, PNG до 20МБ",
        "results_title": "Результаты",
        "results_empty": "Здесь появятся извлеченные марки",
        "status_ready": "Готов к работе",
        "status_loading": "Загрузка изображения...",
        "status_analyzing": "Анализ изображения...",
        "status_found": "Найдено марок: {count}",
        "status_extracted": "Извлечено марок: {count}",
        "status_no_stamps": "Марки не найдены. Попробуйте изменить параметры или используйте ручной режим.",
        "status_saved": "✅ Сохранено {count} марок",
        "dlg_save_folder": "Выберите папку для сохранения",
        "err_saving_title": "Ошибка сохранения",
        
        # Слайдеры и настройки
        "lbl_auto_thresh": "Авто-порог (Otsu)",
        "lbl_thresh": "Порог (чувствительность): {val}",
        "lbl_min_area": "Мин. площадь ({val}px²)",
        "lbl_dilate": "Радиус объединения ({val}px)",
        "lbl_padding": "Отступ от марки ({val}px)",
        "lbl_invert": "Тёмный фон скана",
        "tab_manual_tools": "🖱️  РУЧНЫЕ ИНСТРУМЕНТЫ",
        "hint_draw": "• ЛКМ зажать + тянуть → рамка\n• ПКМ внутри рамки → удалить",
        "btn_clear": "🗑️ Очистить",
        "btn_extract_imgs": "🖼️ Извлечь",
        "lbl_size": "Размер:",
        "lbl_color": "Цвет:",
        "lbl_bg": "Фон:",
        "val_black": "Чёрный",
        "val_white": "Белый",
        "val_gray": "Серый",
        "val_blue": "Синий",
        "val_red": "Красный",
        "val_transparent": "Прозр.",
        
        # Подписи
        "toggle_captions": "Показать инструменты текста",
        "hint_caption": "💡 Кликните по марке в списке выше, чтобы изменить её текст",
        
        # Инфо панель
        "tab_how_it_works": "ℹ️  Как это работает",
        "lbl_how_it_works_desc": "Используйте Авто-поиск для автоматического\nнахождения марок или Режим рисования,\nчтобы вручную выделить пропущенные.\nНажмите Извлечь для обрезки.",
        "btn_github": "🌐  Проект на GitHub",
        "btn_releases": "📦  Скачать обновления (Релизы)",
        "btn_telegram": "💬  Связаться в Telegram",
        
        # Холст
        "btn_upload_scan": "Загрузить скан",
        "lbl_upload_formats": "JPEG, PNG до 20МБ",
        "btn_choose_file": "Выбрать файл",
        "btn_change_photo": "🔄 Сменить фото",
        "lbl_found_areas": "Найдено областей: {count:02d}",
        "dlg_open_scan": "Выберите скан с марками",
        "btn_draw_mode_on": "🖊️  Режим рисования ВКЛЮЧЕН",
        "btn_processing": "⏳ Обработка...",
        "err_processing": "Ошибка обработки: {error}",
        
        # Галерея результатов
        "tab_extracted_stamps": "🖼️  Извлечённые марки",
        "btn_save_all": "💾 Сохранить все",
        "lbl_bg_style": "Фон подписи",
        "bg_style_cut": "Вырезать",
        "bg_style_transparent": "Прозрачный",
        "bg_style_white": "Белый",
        "bg_style_black": "Черный",
        "lbl_align": "Выравнивание",
        "align_left": "Слева",
        "align_center": "По центру",
        "align_right": "Справа",
        "lbl_text_color": "Цвет текста",
        "color_black": "Черный",
        "color_white": "Белый",
        "color_red": "Красный",
        "color_blue": "Синий",
        
        # Редактор марок
        "editor_title": "Редактирование подписи: Марка #{idx}",
        "editor_lbl": "Подпись (можно многострочную):",
        "lbl_text_format": "Текст и форматирование",
        "lbl_tools": "Инструменты",
        "lbl_rotate": "Поворот фото:",
        "btn_crop_frame": "✂️ Обрезать по рамке",
        "btn_done": "✅ ГОТОВО",
        "btn_apply": "Применить",
        "btn_cancel": "ОТМЕНА",
        "btn_delete": "Удалить",
        "msg_restart": "Пожалуйста, перезапустите приложение для полного применения языка.",
        "msg_restart_title": "Перезапуск требуется",
        "val_images": "Изображения",
        "val_all_files": "Все файлы"
    },
    "en": {
        "app_title": "Markorez — Smart Stamp Cropping",
        "tab_auto": "Auto Search",
        "tab_manual": "Manual",
        "btn_select_file": "Select File",
        "btn_draw_mode": "✏️ Drawing Mode",
        "btn_find": "🔍 Find",
        "btn_divide": "✂️ Divide",
        "btn_extract": "✂️ Extract",
        "btn_save_all": "💾 Save All",
        "btn_clear_all": "🗑️ Clear All",
        "btn_gh_check": "🌐  GitHub Project",
        "btn_gh_releases": "📦  Download Updates (Releases)",
        "btn_tg_contact": "💬  Contact on Telegram",
        "info_how_it_works": "ℹ️  How it works",
        "info_desc": (
            "Use Auto Search to automatically\n"
            "find stamps, or Drawing Mode\n"
            "to manually select missed ones.\n"
            "Click Extract to crop."
        ),
        "upload_title": "Upload Scan",
        "upload_desc": "JPEG, PNG up to 20MB",
        "results_title": "Results",
        "results_empty": "Extracted stamps will appear here",
        "status_ready": "Ready",
        "status_loading": "Loading image...",
        "status_analyzing": "Analyzing image...",
        "status_found": "Found stamps: {count}",
        "status_extracted": "Extracted stamps: {count}",
        "status_no_stamps": "No stamps found. Try changing parameters or use manual mode.",
        "status_saved": "✅ Saved {count} stamps",
        "dlg_save_folder": "Select folder to save",
        "err_saving_title": "Save Error",
        
        # Sliders and settings
        "lbl_auto_thresh": "Auto Threshold (Otsu)",
        "lbl_thresh": "Threshold (Sensitivity): {val}",
        "lbl_min_area": "Min Area ({val}px²)",
        "lbl_dilate": "Merge Radius ({val}px)",
        "lbl_padding": "Stamp Padding ({val}px)",
        "lbl_invert": "Dark Scan Background",
        "tab_manual_tools": "🖱️  MANUAL TOOLS",
        "hint_draw": "• LMB drag → draw box\n• RMB inside box → delete",
        "btn_clear": "🗑️ Clear",
        "btn_extract_imgs": "🖼️ Extract",
        "lbl_size": "Size:",
        "lbl_color": "Color:",
        "lbl_bg": "Background:",
        "val_black": "Black",
        "val_white": "White",
        "val_gray": "Gray",
        "val_blue": "Blue",
        "val_red": "Red",
        "val_transparent": "Transp.",
        
        # Captions
        "toggle_captions": "Show Text Tools",
        "hint_caption": "💡 Click on a stamp in the list above to change its text",
        
        # Info Panel
        "tab_how_it_works": "ℹ️  How It Works",
        "lbl_how_it_works_desc": "Use Auto-Search to automatically\nfind stamps or Draw Mode to\nmanually select missed ones.\nClick Extract to crop.",
        "btn_github": "🌐  GitHub Project",
        "btn_releases": "📦  Download Updates (Releases)",
        "btn_telegram": "💬  Contact on Telegram",
        
        # Canvas
        "btn_upload_scan": "Upload Scan",
        "lbl_upload_formats": "JPEG, PNG up to 20MB",
        "btn_choose_file": "Choose File",
        "btn_change_photo": "🔄 Change Photo",
        "lbl_found_areas": "Areas found: {count:02d}",
        "dlg_open_scan": "Select scan with stamps",
        "btn_draw_mode_on": "🖊️  Drawing Mode ENABLED",
        "btn_processing": "⏳ Processing...",
        "err_processing": "Processing error: {error}",
        
        # Results Gallery
        "tab_extracted_stamps": "🖼️  Extracted Stamps",
        "btn_save_all": "💾 Save All",
        "lbl_bg_style": "Caption Background",
        "bg_style_cut": "Cut",
        "bg_style_transparent": "Transparent",
        "bg_style_white": "White",
        "bg_style_black": "Black",
        "lbl_align": "Alignment",
        "align_left": "Left",
        "align_center": "Center",
        "align_right": "Right",
        "lbl_text_color": "Text Color",
        "color_black": "Black",
        "color_white": "White",
        "color_red": "Red",
        "color_blue": "Blue",
        
        # Stamp Editor
        "editor_title": "Edit Caption: Stamp #{idx}",
        "editor_lbl": "Caption (multiline allowed):",
        "lbl_text_format": "Text and Formatting",
        "lbl_tools": "Tools",
        "lbl_rotate": "Rotate Photo:",
        "btn_crop_frame": "✂️ Crop to Frame",
        "btn_done": "✅ DONE",
        "btn_apply": "Apply",
        "btn_cancel": "CANCEL",
        "btn_delete": "Delete",
        "msg_restart": "Please restart the application to fully apply the language changes.",
        "msg_restart_title": "Restart required",
        "val_images": "Images",
        "val_all_files": "All files"
}
}

import json
import os

SETTINGS_FILE = "settings.json"

def _load_language():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("language", "ru")
        except:
            pass
    return "ru"

_current_lang = _load_language()

def set_language(lang: str):
    global _current_lang
    if lang in TRANSLATIONS:
        _current_lang = lang
        # Save to dict
        data = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except:
                pass
        data["language"] = lang
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except:
            pass

def get_current_language() -> str:
    return _current_lang

def _(key: str, **kwargs) -> str:
    """Translates a given key into the current language."""
    text = TRANSLATIONS.get(_current_lang, TRANSLATIONS["ru"]).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text
