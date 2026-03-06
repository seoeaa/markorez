"""
Маркорез — Умный инструмент для автоматического поиска и нарезки почтовых марок
Desktop-приложение на Python (CustomTkinter + OpenCV)
"""

import customtkinter as ctk
from tkinter import filedialog, Canvas
from PIL import Image, ImageTk, ImageDraw, ImageFont
import cv2
import numpy as np
import os
import threading

import image_utils
import webbrowser
from i18n import _, set_language, get_current_language
from image_utils import BoundingBox, process_image, detect_dark_background, render_stamp_with_caption
from editor_window import StampEditorWindow
from constants import COLORS, THUMB_SIZE, MAX_DIM
from canvas_widget import StampCanvas



class MarkorezApp(ctk.CTk):
    """Главное окно приложения Маркорез."""

    def __init__(self):
        super().__init__()
        
        # Настройки окна
        self.title(_("app_title"))
        self.geometry("1280x800")
        self.minsize(900, 600)
        
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")

        # Состояние приложения
        self.original_image: np.ndarray | None = None
        self.extracted_stamps: list[np.ndarray] = []
        self.stamp_thumbnails: list[ctk.CTkImage] = []
        self.stamp_captions: list[str] = []  # Подписи к маркам
        self.selected_stamp_index: int = -1  # Индекс выбранной марки
        self.image_path: str = ""

        # Параметры обработки
        self.use_auto_threshold = ctk.BooleanVar(value=True)
        self.threshold_var = ctk.IntVar(value=128)
        self.min_area_var = ctk.IntVar(value=5000)
        self.invert_var = ctk.BooleanVar(value=False)
        self.padding_var = ctk.IntVar(value=20)

        # Параметры подписей
        self.captions_enabled = ctk.BooleanVar(value=False)
        self.caption_font_size = ctk.IntVar(value=24)
        self.caption_bg_color = ctk.StringVar(value="white")  # white или transparent
        self.caption_bold = ctk.BooleanVar(value=False)
        self.caption_italic = ctk.BooleanVar(value=False)
        self.caption_align = ctk.StringVar(value="center")  # left, center, right
        self.caption_text_color = ctk.StringVar(value="black")
        self._preview_after_id = None

        self._build_ui()

    def _build_ui(self):
        """Построение интерфейса."""
        # ─── Шапка ───
        header = ctk.CTkFrame(self, height=56, corner_radius=0, fg_color=COLORS["card"],
                              border_width=1, border_color=COLORS["border"])
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=20, pady=0, expand=True)

        icon_frame = ctk.CTkFrame(header_inner, width=36, height=36, corner_radius=8,
                                  fg_color=COLORS["accent_light"])
        icon_frame.pack(side="left", padx=(0, 10))
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(icon_frame, text="✂️", font=ctk.CTkFont(size=18)).pack(expand=True)

        title_frame = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_frame.pack(side="left")
        ctk.CTkLabel(title_frame, text=_("app_title").split(" —")[0],
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLORS["text"]).pack(anchor="w", pady=(8, 0))

        # Язык
        lang_frame = ctk.CTkFrame(header_inner, fg_color="transparent")
        lang_frame.pack(side="right", padx=10, pady=10)
        self.lang_var = ctk.StringVar(value=get_current_language().upper())
        self.lang_menu = ctk.CTkOptionMenu(lang_frame, values=["RU", "EN"], variable=self.lang_var, 
                                           command=self._on_language_changed, width=70)
        self.lang_menu.pack()

        # ─── Основная область ───
        main_frame = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Левая панель (настройки)
        left_panel = ctk.CTkScrollableFrame(main_frame, width=280, fg_color=COLORS["bg"],
                                            corner_radius=0)
        left_panel.pack(side="left", fill="y", padx=(12, 0), pady=12)

        self._build_auto_search_panel(left_panel)
        self._build_manual_tools_panel(left_panel)
        self._build_info_panel(left_panel)

        # Правая панель (изображение + результаты)
        right_panel = ctk.CTkFrame(main_frame, fg_color=COLORS["bg"], corner_radius=0)
        right_panel.pack(side="left", fill="both", expand=True, padx=12, pady=12)

        self._build_canvas_area(right_panel)
        self._build_results_area(right_panel)

    def _on_language_changed(self, choice):
        lang = "ru" if choice == "RU" else "en"
        set_language(lang)
        self.title(_("app_title"))
        import tkinter.messagebox as messagebox
        messagebox.showinfo(_("msg_restart_title"), _("msg_restart"))

    def _build_auto_search_panel(self, parent):
        """Панель авто-поиска."""
        card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=12,
                            border_width=1, border_color=COLORS["border"])
        card.pack(fill="x", pady=(0, 8))

        # Заголовок
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 12))
        ctk.CTkLabel(header, text="⚙️  " + _("tab_auto").upper(),
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS["text_secondary"]).pack(anchor="w")

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=16, pady=(0, 16))

        # Порог
        thresh_header = ctk.CTkFrame(content, fg_color="transparent")
        thresh_header.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(thresh_header, text=_("lbl_thresh").split(":")[0],
                     font=ctk.CTkFont(size=13),
                     text_color=COLORS["text"]).pack(side="left")

        auto_frame = ctk.CTkFrame(thresh_header, fg_color="transparent")
        auto_frame.pack(side="right")
        self.auto_check = ctk.CTkCheckBox(auto_frame, text=_("lbl_auto_thresh").split("(")[0].strip(), variable=self.use_auto_threshold,
                                          command=self._on_auto_threshold_changed,
                                          font=ctk.CTkFont(size=11),
                                          checkbox_width=18, checkbox_height=18,
                                          fg_color=COLORS["accent"],
                                          hover_color=COLORS["accent_hover"])
        self.auto_check.pack(side="left")

        self.threshold_label = ctk.CTkLabel(thresh_header, text="",
                                            font=ctk.CTkFont(family="Courier", size=11),
                                            text_color=COLORS["text_secondary"])
        self.threshold_label.pack(side="right", padx=(0, 8))

        # Кнопка помощи для чувствительности
        help_btn = ctk.CTkButton(thresh_header, text="?", width=18, height=18,
                                 corner_radius=9, font=ctk.CTkFont(size=11, weight="bold"),
                                 fg_color="transparent", border_width=1,
                                 border_color=COLORS["border"],
                                 text_color=COLORS["text_secondary"],
                                 hover_color=COLORS["blue_light"],
                                 command=lambda: self._show_help("help_thresh"))
        help_btn.pack(side="left", padx=6)

        self.threshold_slider = ctk.CTkSlider(content, from_=0, to=255,
                                              variable=self.threshold_var,
                                              command=lambda v: self._update_slider_label(
                                                  self.threshold_label, int(v)),
                                              button_color=COLORS["accent"],
                                              button_hover_color=COLORS["accent_hover"],
                                              progress_color=COLORS["accent"])
        self.threshold_slider.pack(fill="x", pady=(2, 8))
        self._on_auto_threshold_changed()

        # Мин. площадь
        self._add_slider(content, _("lbl_min_area").split("(")[0].strip(), self.min_area_var,
                         1000, 50000, "area_label", suffix="px²", help_key="help_min_area")

        # Инверсия
        ctk.CTkCheckBox(content, text=_("lbl_invert"), variable=self.invert_var,
                        font=ctk.CTkFont(size=13),
                        checkbox_width=18, checkbox_height=18,
                        fg_color=COLORS["accent"],
                        hover_color=COLORS["accent_hover"]).pack(anchor="w", pady=(8, 12))

        # Разделитель
        sep = ctk.CTkFrame(content, height=1, fg_color=COLORS["border"])
        sep.pack(fill="x", pady=(0, 12))

        # Кнопки поиска и разделения
        self.find_btn = ctk.CTkButton(
            content, text=_("btn_find"), height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._handle_find
        )
        self.find_btn.pack(fill="x", pady=(0, 8))
        
        self.divide_btn = ctk.CTkButton(
            content, text=_("btn_divide"), height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["dark"], hover_color=COLORS["dark_hover"],
            command=self._extract_stamps
        )
        self.divide_btn.pack(fill="x", pady=(0, 8))

    def _build_manual_tools_panel(self, parent):
        """Панель ручных инструментов."""
        card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=12,
                            border_width=1, border_color=COLORS["border"])
        card.pack(fill="x", pady=(0, 8))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 12))
        ctk.CTkLabel(header, text=_("tab_manual_tools"),
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS["text_secondary"]).pack(anchor="w")

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=16, pady=(0, 16))

        # Кнопка режима рисования
        self.draw_btn = ctk.CTkButton(
            content, text=_("btn_draw_mode"), height=36,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["card"], hover_color=COLORS["blue_light"],
            text_color=COLORS["text"],
            border_width=1, border_color=COLORS["border"],
            command=self._toggle_drawing_mode
        )
        self.draw_btn.pack(fill="x", pady=(0, 8))

        # Подсказка для рисования
        self.draw_hint = ctk.CTkFrame(content, fg_color=COLORS["blue_light"], corner_radius=8)
        self.draw_hint_label = ctk.CTkLabel(
            self.draw_hint,
            text=_("hint_draw"),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["blue_text"],
            justify="left"
        )
        self.draw_hint_label.pack(padx=12, pady=8)
        # Изначально скрыта
        self.draw_hint.pack_forget()

        # Отступ обрезки
        self._add_slider(content, _("lbl_padding").split("(")[0].strip(), self.padding_var,
                         0, 100, "padding_label", suffix="px")

        # Разделитель удален, кнопки перенесены
        pass

    def _build_caption_format_toolbar(self, parent):
        """Панель инструментов форматирования подписи как в текстовом редакторе."""
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        
        # Строка 1: размер, стили, выравнивание
        row1 = ctk.CTkFrame(toolbar, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        
        # Размер
        size_frame = ctk.CTkFrame(row1, fg_color="transparent")
        size_frame.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(size_frame, text=_("lbl_size"), font=ctk.CTkFont(size=11)).pack(side="left")
        ctk.CTkSlider(size_frame, from_=10, to=80, variable=self.caption_font_size, width=80, command=lambda _: self._trigger_preview_update()).pack(side="left", padx=4)

        # Кнопки форматирования (B, I)
        style_frame = ctk.CTkFrame(row1, fg_color="transparent")
        style_frame.pack(side="left", padx=(0, 10))
        
        self.bold_btn = ctk.CTkButton(style_frame, text="B", width=30, height=26, 
                                     font=ctk.CTkFont(weight="bold"), 
                                     fg_color=COLORS["card"], text_color=COLORS["text"],
                                     border_width=1, border_color=COLORS["border"],
                                     command=lambda: self._apply_tag("bold"))
        self.bold_btn.pack(side="left", padx=2)
        
        self.italic_btn = ctk.CTkButton(style_frame, text="I", width=30, height=26, 
                                       font=ctk.CTkFont(slant="italic"),
                                       fg_color=COLORS["card"], text_color=COLORS["text"],
                                       border_width=1, border_color=COLORS["border"],
                                       command=lambda: self._apply_tag("italic"))
        self.italic_btn.pack(side="left", padx=2)

        # Выравнивание
        align_frame = ctk.CTkFrame(row1, fg_color="transparent")
        align_frame.pack(side="left")
        menu = ctk.CTkSegmentedButton(align_frame, values=["⬅", "⬛", "➡"], command=self._on_align_changed, font=ctk.CTkFont(size=11))
        menu.set("⬛")
        menu.pack(side="left")

        # Строка 2: Цвета
        row2 = ctk.CTkFrame(toolbar, fg_color="transparent")
        row2.pack(fill="x", pady=2)
        
        # Цвет текста
        color_frame = ctk.CTkFrame(row2, fg_color="transparent")
        color_frame.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(color_frame, text=_("lbl_color"), font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 4))
        c_menu = ctk.CTkSegmentedButton(color_frame, values=[_("val_black"), _("val_white"), _("val_gray"), _("val_blue"), _("val_red")], command=self._on_text_color_changed, font=ctk.CTkFont(size=11))
        c_menu.set(_("val_black"))
        c_menu.pack(side="left")

        # Фон подписи
        bg_frame = ctk.CTkFrame(row2, fg_color="transparent")
        bg_frame.pack(side="left")
        ctk.CTkLabel(bg_frame, text=_("lbl_bg"), font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 4))
        bg_menu = ctk.CTkSegmentedButton(bg_frame, values=[_("val_white"), _("val_transparent")], command=self._on_caption_bg_changed, font=ctk.CTkFont(size=11))
        bg_menu.set(_("val_white"))
        bg_menu.pack(side="left")

        return toolbar

    def _on_caption_bg_changed(self, value):
        self.caption_bg_color.set("white" if value == _("val_white") else "transparent")
        self._trigger_preview_update()

    def _on_align_changed(self, value):
        mapping = {"⬅": "left", "⬛": "center", "➡": "right"}
        self.caption_align.set(mapping.get(value, "center"))
        self._trigger_preview_update()

    def _on_text_color_changed(self, value):
        mapping = {
            _("val_black"): "black", _("val_white"): "white", _("val_gray"): "#666666",
            _("val_blue"): "#1a56db", _("val_red"): "#dc2626"
        }
        self.caption_text_color.set(mapping.get(value, "black"))
        self._trigger_preview_update()

    def _trigger_preview_update(self):
        """Запуск обновления превью с небольшой задержкой (debounce)."""
        if self._preview_after_id:
            self.after_cancel(self._preview_after_id)
        self._preview_after_id = self.after(300, self._update_preview)

    def _update_preview(self):
        """Обновление миниатюры марки с учетом текущей подписи."""
        if self.selected_stamp_index < 0 or self.selected_stamp_index >= len(self.extracted_stamps):
            return

        idx = self.selected_stamp_index
        stamp = self.extracted_stamps[idx]
        caption = self.stamp_captions[idx] if self.captions_enabled.get() else ""
        
        if caption and self.captions_enabled.get():
            rendered_img = self._render_stamp_with_caption(stamp, caption)
        else:
            rgb = cv2.cvtColor(stamp, cv2.COLOR_BGR2RGB)
            rendered_img = Image.fromarray(rgb)
            
        # Масштабирование для превью
        rendered_img.thumbnail((150, 150), Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=rendered_img, dark_image=rendered_img, size=rendered_img.size)
        self.stamp_thumbnails[idx] = ctk_img
        
        # Обновить Label в галерее
        # Label является вторым ребенком во frame (первым был - нет, это Label img_label)
        frame = self.stamp_frames[idx]
        for child in frame.winfo_children():
            if isinstance(child, ctk.CTkLabel) and child.cget("text") == "":
                child.configure(image=ctk_img)
                break

    def _build_info_panel(self, parent):
        """Информационная панель."""
        card = ctk.CTkFrame(parent, fg_color=COLORS["blue_light"], corner_radius=12,
                            border_width=1, border_color="#bfdbfe")
        card.pack(fill="x", pady=(0, 8))

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(content, text=_("tab_how_it_works"),
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["blue_text"]).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(content,
                     text=_("lbl_how_it_works_desc"),
                     font=ctk.CTkFont(size=11),
                     text_color=COLORS["blue_text"],
                     justify="left").pack(anchor="w", pady=(0, 10))

        # Ссылки
        gh_btn = ctk.CTkButton(
            content, text=_("btn_github"),
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#3b82f6", hover_color="#2563eb",
            height=28,
            command=lambda: webbrowser.open("https://github.com/seoeaa/markorez")
        )
        gh_btn.pack(fill="x", pady=(0, 6))

        gh_releases_btn = ctk.CTkButton(
            content, text=_("btn_releases"),
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#10b981", hover_color="#059669",
            height=28,
            command=lambda: webbrowser.open("https://github.com/seoeaa/markorez/releases")
        )
        gh_releases_btn.pack(fill="x", pady=(0, 6))

        tg_btn = ctk.CTkButton(
            content, text=_("btn_telegram"),
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#0088cc", hover_color="#006699",
            height=28,
            command=lambda: webbrowser.open("https://t.me/slaveaa")
        )
        tg_btn.pack(fill="x")

    def _build_canvas_area(self, parent):
        """Область отображения изображения."""
        self.canvas_card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=12,
                                        border_width=1, border_color=COLORS["border"])
        self.canvas_card.pack(fill="both", expand=True, pady=(0, 8))

        # Область загрузки (показывается когда нет изображения)
        self.upload_frame = ctk.CTkFrame(self.canvas_card, fg_color="#f4f4f5", corner_radius=12)
        self.upload_frame.pack(fill="both", expand=True, padx=16, pady=16)

        upload_inner = ctk.CTkFrame(self.upload_frame, fg_color="transparent")
        upload_inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(upload_inner, text="📤", font=ctk.CTkFont(size=48)).pack(pady=(0, 8))
        ctk.CTkLabel(upload_inner, text=_("btn_upload_scan"),
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLORS["text"]).pack()
        ctk.CTkLabel(upload_inner, text=_("lbl_upload_formats"),
                     font=ctk.CTkFont(size=12),
                     text_color=COLORS["text_secondary"]).pack(pady=(2, 12))

        ctk.CTkButton(upload_inner, text=_("btn_choose_file"), height=36,
                      font=ctk.CTkFont(size=13),
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                      command=self._open_file).pack()

        # Контейнер для Canvas (скрыт пока нет фото)
        self.canvas_container = ctk.CTkFrame(self.canvas_card, fg_color="transparent")
        
        # Интерактивный холст
        self.canvas = StampCanvas(self.canvas_container)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.set_callback(self._on_canvas_updated)

        # Кнопка смены фото (поверх холста)
        self.change_photo_btn = ctk.CTkButton(
            self.canvas_container, text=_("btn_change_photo"), width=120, height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["card"], hover_color="#f4f4f5",
            text_color=COLORS["text"],
            border_width=1, border_color=COLORS["border"],
            command=self._open_file
        )
        self.change_photo_btn.place(relx=1.0, rely=0.0, x=-16, y=16, anchor="ne")

        # Кнопка Очистить (под Сменить фото)
        self.main_clear_btn = ctk.CTkButton(
            self.canvas_container, text=_("btn_clear"), width=120, height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["card"], hover_color=COLORS["red_light"],
            text_color=COLORS["text"],
            border_width=1, border_color=COLORS["border"],
            command=self._clear_boxes
        )
        self.main_clear_btn.place(relx=1.0, rely=0.0, x=-16, y=56, anchor="ne")

        # Статус-бар (количество найденных рамок)
        self.status_bar = ctk.CTkFrame(self.canvas_card, height=36, fg_color=COLORS["dark"],
                                       corner_radius=0)
        self.status_label = ctk.CTkLabel(self.status_bar, text="",
                                         font=ctk.CTkFont(family="Courier", size=12),
                                         text_color="#a1a1aa")
        self.status_label.pack(side="left", padx=16)

    def _on_canvas_updated(self, box_count: int):
        """Вызывается при изменении рамок на холсте."""
        self.status_label.configure(text=_("lbl_found_areas", count=box_count))
        if box_count > 0:
            self.status_bar.pack(fill="x", side="bottom")
        else:
            self.status_bar.pack_forget()

    def _build_results_area(self, parent):
        """Галерея результатов."""
        self.results_card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=12,
                                         border_width=1, border_color=COLORS["border"])
        # Изначально скрыта
        
        results_header = ctk.CTkFrame(self.results_card, fg_color="transparent")
        results_header.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(results_header, text=_("tab_extracted_stamps"),
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=COLORS["text"]).pack(side="left")

        self.download_all_btn = ctk.CTkButton(
            results_header, text=_("btn_save_all"), height=30,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["accent_light"], hover_color=COLORS["accent"],
            text_color=COLORS["accent_text"],
            command=self._save_all_stamps
        )
        self.download_all_btn.pack(side="right")

        # Скроллируемая область для миниатюр
        self.stamps_scroll = ctk.CTkScrollableFrame(self.results_card, fg_color="transparent",
                                                     height=180, orientation="horizontal")
        self.stamps_scroll.pack(fill="x", padx=12, pady=(0, 4))

        # Глобальные настройки подписи
        self.caption_settings_card = ctk.CTkFrame(self.results_card, fg_color="#f8f9fa",
                                                 corner_radius=8, border_width=1,
                                                 border_color=COLORS["border"])
        
        caption_settings_header = ctk.CTkFrame(self.caption_settings_card, fg_color="transparent")
        caption_settings_header.pack(fill="x", padx=12, pady=(8, 8))

        self.caption_toggle = ctk.CTkCheckBox(
            caption_settings_header, text=_("toggle_captions"),
            variable=self.captions_enabled,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text"],
            command=self._on_captions_toggled
        )
        self.caption_toggle.pack(side="left")

        # Глобальные параметры (шрифт, цвет и т.д.)
        self.global_tools_frame = ctk.CTkFrame(self.caption_settings_card, fg_color="transparent")
        # Показываем только если галочка "Добавить подписи" включена
        if self.captions_enabled.get():
            self.global_tools_frame.pack(fill="x", padx=12, pady=(0, 12))
        
        # Переиспользуем существующий тулбар для глобальных настроек (размер, цвет, выравнивание)
        self._build_caption_format_toolbar(self.global_tools_frame).pack(fill="x")
        
        # Инструкция
        hint = ctk.CTkLabel(self.global_tools_frame, text=_("hint_caption"),
                            font=ctk.CTkFont(size=11, slant="italic"), text_color="gray")
        hint.pack(pady=(8, 0))

    def _on_captions_toggled(self):
        """Отображение/скрытие инструментов текста."""
        if self.captions_enabled.get():
            self.global_tools_frame.pack(fill="x", padx=12, pady=(0, 12))
            # При включении обновляем все миниатюры
            for i in range(len(self.extracted_stamps)):
                self._update_stamp_thumbnail(i)
        else:
            self.global_tools_frame.pack_forget()
            # При выключении тоже обновляем (убираем текст)
            for i in range(len(self.extracted_stamps)):
                self._update_stamp_thumbnail(i)

    # ═══════════════════════════════════════════════════════════════════
    #  Вспомогательные методы UI
    # ═══════════════════════════════════════════════════════════════════

    def _add_slider(self, parent, label_text, variable, min_val, max_val,
                    label_attr, suffix="", help_key=None):
        """Добавить слайдер с меткой."""
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(8, 2))

        ctk.CTkLabel(header, text=label_text, font=ctk.CTkFont(size=13),
                     text_color=COLORS["text"]).pack(side="left")

        if help_key:
            help_btn = ctk.CTkButton(header, text="?", width=18, height=18,
                                     corner_radius=9, font=ctk.CTkFont(size=11, weight="bold"),
                                     fg_color="transparent", border_width=1,
                                     border_color=COLORS["border"],
                                     text_color=COLORS["text_secondary"],
                                     hover_color=COLORS["blue_light"],
                                     command=lambda: self._show_help(help_key))
            help_btn.pack(side="left", padx=6)

        val_label = ctk.CTkLabel(header, text=f"{variable.get()}{suffix}",
                                 font=ctk.CTkFont(family="Courier", size=11),
                                 text_color=COLORS["text_secondary"])
        val_label.pack(side="right")
        setattr(self, label_attr, val_label)

        slider = ctk.CTkSlider(parent, from_=min_val, to=max_val,
                               variable=variable,
                               number_of_steps=max(1, (max_val - min_val) // max(1, (max_val - min_val) // 100)),
                               command=lambda v, lbl=val_label, s=suffix: lbl.configure(
                                   text=f"{int(v)}{s}"),
                               button_color=COLORS["accent"],
                               button_hover_color=COLORS["accent_hover"],
                               progress_color=COLORS["accent"])
        slider.pack(fill="x", pady=(2, 0))

    def _update_slider_label(self, label, value):
        label.configure(text=str(value))

    def _show_help(self, key):
        """Показывает информационное окно с описанием настройки."""
        import tkinter.messagebox as messagebox
        # Мы используем кастомное окно или стандартный messagebox
        # Но чтобы было красиво в стиле приложения, можно было бы сделать CTkMessagebox, 
        # но для начала хватит и стандартного info.
        messagebox.showinfo(_("tab_how_it_works"), _(key))

    def _on_auto_threshold_changed(self):
        """Переключение авто/ручного порога."""
        is_auto = self.use_auto_threshold.get()
        if is_auto:
            self.threshold_slider.configure(state="disabled")
            self.threshold_label.configure(text="")
        else:
            self.threshold_slider.configure(state="normal")
            self.threshold_label.configure(text=str(self.threshold_var.get()))

    def _toggle_drawing_mode(self):
        """Переключение режима рисования."""
        is_drawing = self.canvas.toggle_drawing_mode()
        
        if is_drawing:
            # Сменить цвет кнопки на активный
            self.draw_btn.configure(
                text=_("btn_draw_mode_on"),
                fg_color=COLORS["blue_light"],
                border_color="#93c5fd",
                text_color=COLORS["blue_text"]
            )
            self.draw_hint.pack(fill="x", pady=(0, 8))
        else:
            self.draw_btn.configure(
                text=_("btn_draw_mode"),
                fg_color=COLORS["card"],
                border_color=COLORS["border"],
                text_color=COLORS["text"]
            )
            self.draw_hint.pack_forget()

    # ═══════════════════════════════════════════════════════════════════
    #  Файловые операции
    # ═══════════════════════════════════════════════════════════════════

    def _open_file(self):
        """Открыть файл изображения."""
        filetypes = [
            (_("val_images"), "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp"),
            (_("val_all_files"), "*.*")
        ]
        path = filedialog.askopenfilename(title=_("dlg_open_scan"),
                                          filetypes=filetypes)
        if not path:
            return

        self.image_path = path
        self._load_image(path)

    def _load_image(self, path: str):
        """Загрузить изображение."""
        # Читаем через OpenCV (поддерживает кириллические пути)
        raw_data = np.fromfile(path, dtype=np.uint8)
        self.original_image = cv2.imdecode(raw_data, cv2.IMREAD_COLOR)

        if self.original_image is None:
            return

        # Сбросить состояние
        self.extracted_stamps = []
        self.stamp_thumbnails = []
        self.stamp_captions = []

        # Авто-определение тёмного фона
        is_dark = detect_dark_background(self.original_image)
        self.invert_var.set(bool(is_dark))

        # Показать canvas, скрыть upload
        self.upload_frame.pack_forget()
        self.canvas_container.pack(fill="both", expand=True, padx=8, pady=8)
        self.change_photo_btn.lift()

        # Скрыть результаты
        self.results_card.pack_forget()

        # Отрисовать на новом холсте
        self.canvas.set_image(self.original_image)


    # ═══════════════════════════════════════════════════════════════════
    #  Логика обработки
    # ═══════════════════════════════════════════════════════════════════

    def _handle_find(self):
        """Запуск автоматического поиска марок (без разделения)."""
        if self.original_image is None:
            return

        self.find_btn.configure(text=_("btn_processing"), state="disabled")

        def process():
            try:
                # Для обработки масштабируем если слишком большое
                h, w = self.original_image.shape[:2]
                scale = 1.0

                if w > MAX_DIM or h > MAX_DIM:
                    scale = min(MAX_DIM / w, MAX_DIM / h)
                    proc_w = int(w * scale)
                    proc_h = int(h * scale)
                    proc_image = cv2.resize(self.original_image, (proc_w, proc_h))
                else:
                    proc_image = self.original_image.copy()

                threshold = -1 if self.use_auto_threshold.get() else self.threshold_var.get()
                scaled_min_area = int(self.min_area_var.get() * scale * scale)

                boxes = process_image(
                    proc_image,
                    threshold=threshold,
                    min_area=max(100, scaled_min_area),
                    invert=self.invert_var.get(),
                    pad=int(self.padding_var.get() * scale)
                )

                # Пересчитать координаты обратно к оригинальному размеру
                original_boxes = []
                for box in boxes:
                    # Масштабируем центр и размер обратно
                    orig_center = (box.center[0] / scale, box.center[1] / scale)
                    orig_size = (box.size[0] / scale, box.size[1] / scale)
                    original_boxes.append(BoundingBox(
                        orig_center,
                        orig_size,
                        box.angle
                    ))

                self.after(0, lambda: self.canvas.set_bounding_boxes(original_boxes))
            except Exception as e:
                print(_("err_processing", error=e))
            finally:
                self.after(0, lambda: self.find_btn.configure(
                    text=_("btn_find"), state="normal"))

        threading.Thread(target=process, daemon=True).start()

    def _extract_stamps(self):
        """Извлечение марок из рамок."""
        if self.original_image is None or not self.canvas.bounding_boxes:
            return

        self.extracted_stamps = []
        self.stamp_thumbnails = []
        self.stamp_captions = []
        padding = self.padding_var.get()
        h, w = self.original_image.shape[:2]

        from image_utils import crop_rotated
        for box in self.canvas.bounding_boxes:
            stamp = crop_rotated(self.original_image, box)
            self.extracted_stamps.append(stamp)

        # Обновить галерею
        self.after(0, self._update_results_gallery)

    def _update_results_gallery(self):
        """Обновление галереи извлечённых марок."""
        # Очистить старые миниатюры
        for widget in self.stamps_scroll.winfo_children():
            widget.destroy()
        self.stamp_thumbnails = []

        if not self.extracted_stamps:
            self.results_card.pack_forget()
            return

        # Показать результаты
        self.results_card.pack(fill="x", pady=(0, 0))

        THUMB_SIZE = 150

        # Создать список подписей если нужно
        while len(self.stamp_captions) < len(self.extracted_stamps):
            self.stamp_captions.append("")

        self.stamp_frames = []  # Для подсветки выбранной

        for i, stamp in enumerate(self.extracted_stamps):
            # Создать рамку для миниатюры
            frame = ctk.CTkFrame(self.stamps_scroll, fg_color=COLORS["card"],
                                 corner_radius=10, border_width=1,
                                 border_color=COLORS["border"],
                                 width=THUMB_SIZE + 16, height=THUMB_SIZE + 40)
            frame.pack(side="left", padx=(0, 8), pady=4)
            frame.pack_propagate(False)
            self.stamp_frames.append(frame)

            # Превью
            rgb = cv2.cvtColor(stamp, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)

            # Масштабирование с сохранением пропорций
            pil_img.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
            self.stamp_thumbnails.append(ctk_img)

            img_label = ctk.CTkLabel(frame, text="", image=ctk_img, cursor="hand2")
            img_label.pack(expand=True, pady=(6, 2))
            img_label.bind("<Button-1>", lambda e, idx=i: self._select_stamp(idx))

            # Блок с номером внизу миниатюры
            bottom = ctk.CTkFrame(frame, fg_color="#f4f4f5", corner_radius=0, height=24)
            bottom.pack(fill="x", side="bottom")
            bottom.pack_propagate(False)

            num_label = ctk.CTkLabel(bottom, text=f"#{i+1}",
                                     font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
                                     text_color=COLORS["text_secondary"])
            num_label.pack(side="left", padx=8)
            num_label.bind("<Button-1>", lambda e, idx=i: self._select_stamp(idx))

            # Кнопка удаления (корзина)
            del_btn = ctk.CTkLabel(bottom, text="🗑️", cursor="hand2",
                                   font=ctk.CTkFont(size=14),
                                   text_color="#ef4444")
            del_btn.pack(side="right", padx=8)
            del_btn.bind("<Button-1>", lambda e, idx=i: self._delete_stamp(idx))

        # Автоматически выбрать первую марку (отключено)
        # if self.extracted_stamps:
        #     self._select_stamp(0)

    def _select_stamp(self, index: int):
        """Выбрать марку и открыть модальный редактор."""
        self.selected_stamp_index = index

        # Обновить подсветку рамок в списке
        for j, fr in enumerate(self.stamp_frames):
            if j == index:
                fr.configure(border_color=COLORS["accent"], border_width=2)
            else:
                fr.configure(border_color=COLORS["border"], border_width=1)

        # Открываем модальное окно редактора
        markup = self.stamp_captions[index] if index < len(self.stamp_captions) else ""
        StampEditorWindow(self, index, self.extracted_stamps[index], markup)

    def _update_stamp_thumbnail(self, index):
        """Обновить миниатюру марки после редактирования."""
        if index >= len(self.stamp_frames) or index >= len(self.extracted_stamps):
            return
            
        stamp = self.extracted_stamps[index]
        caption = self.stamp_captions[index]
        
        # Рендерим с актуальной подписью
        img_with_caption = render_stamp_with_caption(
            stamp, 
            caption,
            self.captions_enabled.get(),
            self.caption_font_size.get(),
            self.caption_text_color.get(),
            self.caption_align.get(),
            self.caption_bg_color.get()
        )
        
        # Создаем миниатюру
        thumb_size = (160, 160)
        img_with_caption.thumbnail(thumb_size, Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(img_with_caption)
        
        # Обновляем Label в соответствующей рамке
        for child in self.stamp_frames[index].winfo_children():
            # Мы знаем, что миниатюра — это Label без текста
            if isinstance(child, ctk.CTkLabel) and not child.cget("text"):
                ctk_img = ctk.CTkImage(light_image=img_with_caption, dark_image=img_with_caption, size=img_with_caption.size)
                child.configure(image=ctk_img)
                child.image = ctk_img # Сохраняем ссылку
                self.stamp_thumbnails[index] = ctk_img
                break

    def _delete_stamp(self, index: int):
        """Удалить конкретную марку из результатов."""
        if 0 <= index < len(self.extracted_stamps):
            self.extracted_stamps.pop(index)
            if index < len(self.stamp_captions):
                self.stamp_captions.pop(index)
            self._update_results_gallery()

    def _clear_boxes(self):
        """Очистить все рамки."""
        self.canvas.clear_boxes()
        self.extracted_stamps = []
        self.stamp_thumbnails = []
        self.stamp_captions = []
        self.stamp_frames = []
        self.selected_stamp_index = -1
        self.caption_settings_card.pack_forget()
        self.results_card.pack_forget()
        self._on_canvas_updated(0)

    def _save_all_stamps(self):
        """Сохранить все извлеченные марки."""
        if not self.extracted_stamps:
            return

        out_dir = filedialog.askdirectory(title=_("dlg_save_folder"))
        if not out_dir:
            return

        try:
            for i, stamp in enumerate(self.extracted_stamps):
                caption = self.stamp_captions[i] if i < len(self.stamp_captions) else ""
                
                # Рендерим
                final_img = render_stamp_with_caption(
                    stamp, 
                    caption,
                    self.captions_enabled.get(),
                    self.caption_font_size.get(),
                    self.caption_text_color.get(),
                    self.caption_align.get(),
                    self.caption_bg_color.get()
                )
                
                # Определяем расширение и сохраняем
                ext = ".png" if final_img.mode == "RGBA" else ".jpg"
                save_path = os.path.join(out_dir, f"stamp_{i+1:03d}{ext}")
                
                if ext == ".png":
                    final_img.save(save_path, "PNG")
                else:
                    final_img.save(save_path, "JPEG", quality=95)

            # Открыть папку
            if os.name == 'nt':
                os.startfile(out_dir)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", out_dir])

            self.status_label.configure(text=_("status_saved", count=len(self.extracted_stamps)))
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror(_("err_saving_title"), str(e))


if __name__ == "__main__":
    app = MarkorezApp()
    app.mainloop()
