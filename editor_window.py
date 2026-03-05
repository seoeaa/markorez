import customtkinter as ctk
from PIL import Image, ImageTk
import image_utils

class StampEditorWindow(ctk.CTkToplevel):
    """Окно для детального редактирования и предпросмотра конкретной марки."""
    def __init__(self, parent, index, stamp_image, initial_markup):
        super().__init__(parent)
        self.parent = parent
        self.index = index
        self.stamp_image = stamp_image
        self.markup = initial_markup
        
        self.title(f"Редактор марки #{index + 1}")
        self.geometry("1000x800")
        self.minsize(800, 600)
        
        self._build_ui()
        self._deserialize_text(self.markup)
        
        # Исправление пустого превью и ошибки grab_set:
        # Планируем настройку после того, как окно станет видимым.
        self.after(100, self._final_setup)

    def _final_setup(self):
        """Завершающая настройка окна после его появления."""
        if not self.winfo_exists(): return
        
        try:
            self.grab_set()
            self.focus_set()
        except:
            pass # Если всё еще не готово, не роняем приложение
            
        self._update_preview()

    def _build_ui(self):
        # Основной контейнер
        self.grid_columnconfigure(0, weight=3) # Просмотр
        self.grid_columnconfigure(1, weight=2) # Редактор
        self.grid_rowconfigure(0, weight=1)

        # --- Левая часть: Предпросмотр ---
        self.preview_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#27272a")
        self.preview_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="")
        self.preview_label.pack(expand=True, fill="both", padx=20, pady=20)

        # --- Правая часть: Редактор ---
        self.edit_frame = ctk.CTkFrame(self, width=350, corner_radius=0, fg_color="#f4f4f5")
        self.edit_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        
        ctk.CTkLabel(self.edit_frame, text="Текст и форматирование", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(30, 10))

        # Панель инструментов (B, I)
        toolbar = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        toolbar.pack(fill="x", padx=30, pady=5)
        
        btn_bold = ctk.CTkButton(toolbar, text="B", width=50, height=40, font=ctk.CTkFont(weight="bold", size=16),
                                 command=lambda: self._apply_tag("bold"))
        btn_bold.pack(side="left", padx=5)
        
        btn_italic = ctk.CTkButton(toolbar, text="I", width=50, height=40, font=ctk.CTkFont(slant="italic", size=16),
                                  command=lambda: self._apply_tag("italic"))
        btn_italic.pack(side="left", padx=5)

        # Выравнивание
        align_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        align_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(align_frame, text="Выравнивание:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        
        align_menu = ctk.CTkSegmentedButton(align_frame, 
                                            values=["⬅", "⬛", "➡"], 
                                            command=self._on_align_changed)
        # Устанавливаем текущее значение из родителя
        current_align = self.parent.caption_align.get()
        mapping_inv = {"left": "⬅", "center": "⬛", "right": "➡"}
        align_menu.set(mapping_inv.get(current_align, "⬛"))
        align_menu.pack(side="left")

        # Дополнительно: Размер шрифта
        size_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        size_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(size_frame, text="Размер:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        size_slider = ctk.CTkSlider(size_frame, from_=10, to=80, 
                                    variable=self.parent.caption_font_size, 
                                    command=lambda _: self._update_preview())
        size_slider.pack(side="left", fill="x", expand=True)

        # Дополнительно: Цвета
        color_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        color_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(color_frame, text="Цвет:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        
        color_menu = ctk.CTkSegmentedButton(color_frame, 
                                           values=["Чёрный", "Белый", "Серый", "Синий", "Красный"],
                                           command=self._on_color_changed)
        # Маппинг для цвета
        mapping_color_inv = {"black": "Чёрный", "white": "Белый", "gray": "Серый", "blue": "Синий", "red": "Красный"}
        color_menu.set(mapping_color_inv.get(self.parent.caption_text_color.get(), "Чёрный"))
        color_menu.pack(side="left")

        # Дополнительно: Фон
        bg_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        bg_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(bg_frame, text="Фон:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        
        bg_menu = ctk.CTkSegmentedButton(bg_frame, 
                                        values=["Белый", "Прозр."],
                                        command=self._on_bg_changed)
        mapping_bg_inv = {"white": "Белый", "transparent": "Прозр."}
        bg_menu.set(mapping_bg_inv.get(self.parent.caption_bg_color.get(), "Белый"))
        bg_menu.pack(side="left")

        # Текстовое поле
        self.textbox = ctk.CTkTextbox(self.edit_frame, height=250, font=("Segoe UI", 16))
        self.textbox.pack(fill="x", padx=30, pady=20)
        self.textbox.bind("<<Modified>>", self._on_text_modified)
        
        # Конфигурация тегов для редактора
        self.textbox._textbox.tag_configure("bold", font=("Segoe UI", 16, "bold"))
        self.textbox._textbox.tag_configure("italic", font=("Segoe UI", 16, "italic"))
        self.textbox._textbox.tag_configure("bold_italic", font=("Segoe UI", 16, "bold", "italic"))

        # Подсказки
        hint = "Используйте кнопки выше для выделения важных слов.\nТекст автоматически переносится."
        ctk.CTkLabel(self.edit_frame, text=hint, font=ctk.CTkFont(size=12),
                     text_color="#71717a", justify="left").pack(padx=30, pady=5, anchor="w")

        # Кнопки управления внизу
        btn_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=30, pady=40)
        
        ctk.CTkButton(btn_frame, text="✅ ГОТОВО", height=50, font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color="#10b981", hover_color="#059669",
                      command=self._save_and_close).pack(fill="x", pady=10)
        
        ctk.CTkButton(btn_frame, text="ОТМЕНА", height=40, font=ctk.CTkFont(size=14),
                      fg_color="#94a3b8", hover_color="#64748b",
                      command=self.destroy).pack(fill="x")

    def _apply_tag(self, tag_type):
        try:
            sel = self.textbox._textbox.tag_ranges("sel")
            if not sel: return
            start, end = sel[0], sel[1]
            
            current_tags = self.textbox._textbox.tag_names(start)
            
            if tag_type == "bold":
                if "bold_italic" in current_tags:
                    self.textbox._textbox.tag_remove("bold_italic", start, end)
                    self.textbox._textbox.tag_add("italic", start, end)
                elif "bold" in current_tags:
                    self.textbox._textbox.tag_remove("bold", start, end)
                elif "italic" in current_tags:
                    self.textbox._textbox.tag_remove("italic", start, end)
                    self.textbox._textbox.tag_add("bold_italic", start, end)
                else:
                    self.textbox._textbox.tag_add("bold", start, end)
            
            elif tag_type == "italic":
                if "bold_italic" in current_tags:
                    self.textbox._textbox.tag_remove("bold_italic", start, end)
                    self.textbox._textbox.tag_add("bold", start, end)
                elif "italic" in current_tags:
                    self.textbox._textbox.tag_remove("italic", start, end)
                elif "bold" in current_tags:
                    self.textbox._textbox.tag_remove("bold", start, end)
                    self.textbox._textbox.tag_add("bold_italic", start, end)
                else:
                    self.textbox._textbox.tag_add("italic", start, end)
            
            self._update_preview()
        except: pass

    def _serialize_text(self):
        text_widget = self.textbox._textbox
        content = text_widget.get("1.0", "end-1c")
        result = []
        for i in range(len(content)):
            char = content[i]
            index = f"1.0 + {i} chars"
            tags = text_widget.tag_names(index)
            
            is_b = "bold" in tags or "bold_italic" in tags
            is_i = "italic" in tags or "bold_italic" in tags
            
            prefix = ""
            suffix = ""
            if is_b:
                prefix += "<b>"
                suffix = "</b>" + suffix
            if is_i:
                prefix += "<i>"
                suffix = "</i>" + suffix
            
            result.append(f"{prefix}{char}{suffix}")
        
        raw = "".join(result)
        raw = raw.replace("</b><b>", "").replace("</i><i>", "")
        return raw

    def _deserialize_text(self, markup):
        self.textbox.delete("1.0", "end")
        if not markup: return
        
        import re
        parts = re.split(r'(<b>|</b>|<i>|</i>)', markup)
        
        is_b = False
        is_i = False
        
        for part in parts:
            if part == "<b>": is_b = True
            elif part == "</b>": is_b = False
            elif part == "<i>": is_i = True
            elif part == "</i>": is_i = False
            elif part:
                start_idx = self.textbox.index("end-1c")
                self.textbox.insert("end", part)
                end_idx = self.textbox.index("end-1c")
                
                if is_b and is_i: self.textbox._textbox.tag_add("bold_italic", start_idx, end_idx)
                elif is_b: self.textbox._textbox.tag_add("bold", start_idx, end_idx)
                elif is_i: self.textbox._textbox.tag_add("italic", start_idx, end_idx)

    def _on_text_modified(self, event=None):
        if self.textbox._textbox.edit_modified():
            self._update_preview()
            self.textbox._textbox.edit_modified(False)

    def _update_preview(self):
        if not self.winfo_exists(): return
        
        markup = self._serialize_text()
        # Вызываем рендеринг через image_utils
        rendered_pil = image_utils.render_stamp_with_caption(
            self.stamp_image,
            markup,
            captions_enabled=True,
            font_size=self.parent.caption_font_size.get(),
            text_color=self.parent.caption_text_color.get(),
            align=self.parent.caption_align.get(),
            bg_style=self.parent.caption_bg_color.get()
        )
        
        # Получаем размеры контейнера
        w = self.preview_frame.winfo_width()
        h = self.preview_frame.winfo_height()
        
        # Если размеры еще не определены (окно только открылось), используем геометрию
        if w <= 1 or h <= 1:
            try:
                geom = self.geometry().split("+")[0].split("x")
                w, h = int(geom[0]) // 2, int(geom[1]) # Примерная оценка
            except:
                w, h = 400, 400
        
        # Масштабируем
        img_w, img_h = rendered_pil.size
        # Оставляем отступы
        target_w = max(50, w - 60)
        target_h = max(50, h - 60)
        
        ratio = min(target_w/img_w, target_h/img_h)
        new_size = (int(img_w * ratio), int(img_h * ratio))
        
        preview_img = rendered_pil.resize(new_size, Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(preview_img)
        
        self.preview_label.configure(image=tk_img)
        self.preview_label.image = tk_img

    def _on_align_changed(self, value):
        mapping = {"⬅": "left", "⬛": "center", "➡": "right"}
        self.parent.caption_align.set(mapping.get(value, "center"))
        self._update_preview()

    def _on_color_changed(self, value):
        mapping = {"Чёрный": "black", "Белый": "white", "Серый": "gray", "Синий": "blue", "Красный": "red"}
        self.parent.caption_text_color.set(mapping.get(value, "black"))
        self._update_preview()

    def _on_bg_changed(self, value):
        mapping = {"Белый": "white", "Прозр.": "transparent"}
        self.parent.caption_bg_color.set(mapping.get(value, "white"))
        self._update_preview()

    def _save_and_close(self):
        markup = self._serialize_text()
        self.parent.stamp_captions[self.index] = markup
        self.parent._update_stamp_thumbnail(self.index)
        self.destroy()
