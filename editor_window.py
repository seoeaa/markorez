import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import image_utils
import cv2
import numpy as np
import re
from i18n import _

class StampEditorWindow(ctk.CTkToplevel):
    def __init__(self, parent, index, stamp_image, initial_markup):
        super().__init__(parent)
        self.parent = parent
        self.index = index
        self.stamp_image = stamp_image
        self.markup = initial_markup
        
        self.title(_("editor_title", idx=index + 1))
        self.geometry("1100x850")
        self.minsize(900, 700)
        
        # Состояние рамки (в координатах оригинала)
        h, w = stamp_image.shape[:2]
        self.frame_x, self.frame_y = 50, 50
        self.frame_w, self.frame_h = min(200, w//2), min(200, h//2)
        self.frame_angle = 0.0
        
        self._auto_detect_frame()
        self.drag_mode = None
        self.drag_start = None
        self.frame_start_vals = None
        self.last_ratio = 1.0
        self.img_offset = (0, 0)
        
        self._build_ui()
        self._deserialize_text(self.markup)
        self.after(100, self._final_setup)

    def _final_setup(self):
        if not self.winfo_exists(): return
        try:
            self.grab_set()
            self.focus_set()
        except: pass
        self._update_preview()

    def _get_img_origin(self):
        # Используем смещение и масштаб от отрендеренного превью (которое содержит текст)
        # Это гарантирует правильное позиционирование поверхностей, даже если пропорции меняются из-за текста
        return self.img_offset[0], self.img_offset[1], self.last_ratio

    def _get_handles(self):
        ox, oy, r = self._get_img_origin()
        sx = ox + self.frame_x * r
        sy = oy + self.frame_y * r
        sw = self.frame_w * r
        sh = self.frame_h * r
        cx_f = sx + sw/2
        cy_f = sy + sh/2
        ang = np.radians(self.frame_angle)
        def rot(ox2, oy2):
            rx = ox2*np.cos(ang) - oy2*np.sin(ang)
            ry = ox2*np.sin(ang) + oy2*np.cos(ang)
            return cx_f+rx, cy_f+ry
        return {
            'nw': rot(-sw/2, -sh/2),
            'ne': rot(sw/2, -sh/2),
            'sw': rot(-sw/2, sh/2),
            'se': rot(sw/2, sh/2),
            'rotate': rot(0, -sh/2 - 22),
            'center': (cx_f, cy_f)
        }

    def _hit_handle(self, x, y, handles):
        for name, (hx, hy) in handles.items():
            if (hx-10 <= x <= hx+10) and (hy-10 <= y <= hy+10):
                return name
        return None

    def _on_mouse_down(self, event):
        x, y = event.x, event.y
        handles = self._get_handles()
        hit = self._hit_handle(x, y, handles)
        if hit == 'rotate':
            self.drag_mode = 'rotate'
        elif hit in ('nw', 'ne', 'sw', 'se'):
            self.drag_mode = 'resize_' + hit
        else:
            self.drag_mode = 'move'
        self.drag_start = (x, y)
        self.frame_start_vals = (self.frame_x, self.frame_y, self.frame_w, self.frame_h, self.frame_angle)

    def _on_mouse_move(self, event):
        if not self.drag_mode: return
        x, y = event.x, event.y
        r = self.last_ratio
        dx = (x - self.drag_start[0]) / r
        dy = (y - self.drag_start[1]) / r
        fx0, fy0, fw0, fh0, fa0 = self.frame_start_vals

        if self.drag_mode == 'move':
            self.frame_x = fx0 + dx
            self.frame_y = fy0 + dy
        elif self.drag_mode == 'rotate':
            handles = self._get_handles()
            cx_f, cy_f = handles['center']
            a1 = np.degrees(np.arctan2(self.drag_start[1]-cy_f, self.drag_start[0]-cx_f))
            a2 = np.degrees(np.arctan2(y-cy_f, x-cx_f))
            self.frame_angle = fa0 + (a2-a1)
        elif self.drag_mode == 'resize_se':
            self.frame_w = max(20, fw0+dx)
            self.frame_h = max(20, fh0+dy)
        elif self.drag_mode == 'resize_sw':
            nw = max(20, fw0-dx)
            self.frame_x = fx0 + fw0 - nw
            self.frame_w = nw
            self.frame_h = max(20, fh0+dy)
        elif self.drag_mode == 'resize_ne':
            self.frame_w = max(20, fw0+dx)
            nh = max(20, fh0-dy)
            self.frame_y = fy0 + fh0 - nh
            self.frame_h = nh
        elif self.drag_mode == 'resize_nw':
            nw = max(20, fw0-dx)
            nh = max(20, fh0-dy)
            self.frame_x = fx0 + fw0 - nw
            self.frame_y = fy0 + fh0 - nh
            self.frame_w = nw
            self.frame_h = nh
        self._update_preview()

    def _on_mouse_up(self, event):
        self.drag_mode = None

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self.preview_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#27272a")
        self.preview_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        self.crop_canvas = tk.Canvas(self.preview_frame, bg="#27272a", highlightthickness=0)
        self.crop_canvas.pack(expand=True, fill="both", padx=10, pady=10)
        self.crop_canvas.bind("<Button-1>", self._on_mouse_down)
        self.crop_canvas.bind("<B1-Motion>", self._on_mouse_move)
        self.crop_canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

        self.edit_frame = ctk.CTkScrollableFrame(self, width=400, corner_radius=0, fg_color="#f4f4f5")
        self.edit_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        
        ctk.CTkLabel(self.edit_frame, text=_("lbl_text_format"), 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))

        toolbar = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        toolbar.pack(fill="x", padx=30, pady=5)
        ctk.CTkButton(toolbar, text="B", width=50, height=40, font=ctk.CTkFont(weight="bold", size=16),
                      command=lambda: self._apply_tag("bold")).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="I", width=50, height=40, font=ctk.CTkFont(slant="italic", size=16),
                      command=lambda: self._apply_tag("italic")).pack(side="left", padx=5)

        align_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        align_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(align_frame, text=_("lbl_align"), font=ctk.CTkFont(size=12)).pack(side="left", padx=(0,10))
        align_menu = ctk.CTkSegmentedButton(align_frame, values=["⬅","⬛","➡"], command=self._on_align_changed)
        align_menu.set({"left":"⬅","center":"⬛","right":"➡"}.get(self.parent.caption_align.get(),"⬛"))
        align_menu.pack(side="left")

        size_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        size_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(size_frame, text=_("lbl_size"), font=ctk.CTkFont(size=12)).pack(side="left", padx=(0,10))
        ctk.CTkSlider(size_frame, from_=10, to=80, variable=self.parent.caption_font_size,
                      command=lambda _: self._update_preview()).pack(side="left", fill="x", expand=True)

        color_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        color_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(color_frame, text=_("lbl_color"), font=ctk.CTkFont(size=12)).pack(side="left", padx=(0,10))
        color_menu = ctk.CTkSegmentedButton(color_frame, values=[_("val_black"),_("val_white"),_("val_gray"),_("val_blue"),_("val_red")], command=self._on_color_changed)
        color_menu.set({"black":_("val_black"),"white":_("val_white"),"gray":_("val_gray"),"blue":_("val_blue"),"red":_("val_red")}.get(self.parent.caption_text_color.get(),_("val_black")))
        color_menu.pack(side="left")

        bg_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        bg_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(bg_frame, text=_("lbl_bg"), font=ctk.CTkFont(size=12)).pack(side="left", padx=(0,10))
        bg_menu = ctk.CTkSegmentedButton(bg_frame, values=[_("val_white"),_("val_transparent")], command=self._on_bg_changed)
        bg_menu.set({"white":_("val_white"),"transparent":_("val_transparent")}.get(self.parent.caption_bg_color.get(),_("val_white")))
        bg_menu.pack(side="left")

        self.textbox = ctk.CTkTextbox(self.edit_frame, height=100, font=("Segoe UI", 16))
        self.textbox.pack(fill="x", padx=30, pady=20)
        self.textbox.bind("<<Modified>>", self._on_text_modified)
        self.textbox.bind("<KeyRelease>", lambda e: self._on_text_modified())
        self.textbox._textbox.tag_configure("bold", font=("Segoe UI", 16, "bold"))
        self.textbox._textbox.tag_configure("italic", font=("Segoe UI", 16, "italic"))
        self.textbox._textbox.tag_configure("bold_italic", font=("Segoe UI", 16, "bold", "italic"))

        ctk.CTkLabel(self.edit_frame, text=_("lbl_tools"), font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20,5))
        
        # Вращение самого изображения марки
        rotate_row = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        rotate_row.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(rotate_row, text=_("lbl_rotate"), font=ctk.CTkFont(size=12)).pack(side="left", padx=(0,10))
        ctk.CTkButton(rotate_row, text="↺ 90°", width=70, height=36, fg_color="#f59e0b", hover_color="#d97706",
                      command=lambda: self._rotate_image(-90)).pack(side="left", padx=3)
        ctk.CTkButton(rotate_row, text="↻ 90°", width=70, height=36, fg_color="#f59e0b", hover_color="#d97706",
                      command=lambda: self._rotate_image(90)).pack(side="left", padx=3)
        ctk.CTkButton(rotate_row, text="180°", width=70, height=36, fg_color="#f59e0b", hover_color="#d97706",
                      command=lambda: self._rotate_image(180)).pack(side="left", padx=3)
        
        ctk.CTkButton(self.edit_frame, text=_("btn_crop_frame"), height=45, fg_color="#6366f1", command=self._crop_image).pack(fill="x", padx=30, pady=10)

        btn_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=30, pady=20)
        ctk.CTkButton(btn_frame, text=_("btn_done"), height=50, font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color="#10b981", hover_color="#059669", command=self._save_and_close).pack(fill="x", pady=5)
        ctk.CTkButton(btn_frame, text=_("btn_cancel"), height=40, fg_color="#94a3b8", command=self.destroy).pack(fill="x")

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
                elif "bold" in current_tags: self.textbox._textbox.tag_remove("bold", start, end)
                elif "italic" in current_tags:
                    self.textbox._textbox.tag_remove("italic", start, end)
                    self.textbox._textbox.tag_add("bold_italic", start, end)
                else: self.textbox._textbox.tag_add("bold", start, end)
            elif tag_type == "italic":
                if "bold_italic" in current_tags:
                    self.textbox._textbox.tag_remove("bold_italic", start, end)
                    self.textbox._textbox.tag_add("bold", start, end)
                elif "italic" in current_tags: self.textbox._textbox.tag_remove("italic", start, end)
                elif "bold" in current_tags:
                    self.textbox._textbox.tag_remove("bold", start, end)
                    self.textbox._textbox.tag_add("bold_italic", start, end)
                else: self.textbox._textbox.tag_add("italic", start, end)
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
            prefix = ("<b>" if is_b else "") + ("<i>" if is_i else "")
            suffix = ("</i>" if is_i else "") + ("</b>" if is_b else "")
            result.append(f"{prefix}{char}{suffix}")
        return "".join(result).replace("</b><b>", "").replace("</i><i>", "")

    def _deserialize_text(self, markup):
        self.textbox.delete("1.0", "end")
        if not markup: return
        parts = re.split(r'(<b>|</b>|<i>|</i>)', markup)
        is_b, is_i = False, False
        for part in parts:
            if part == "<b>": is_b = True
            elif part == "</b>": is_b = False
            elif part == "<i>": is_i = True
            elif part == "</i>": is_i = False
            elif part:
                s = self.textbox.index("end-1c")
                self.textbox.insert("end", part)
                e = self.textbox.index("end-1c")
                if is_b and is_i: self.textbox._textbox.tag_add("bold_italic", s, e)
                elif is_b: self.textbox._textbox.tag_add("bold", s, e)
                elif is_i: self.textbox._textbox.tag_add("italic", s, e)

    def _on_text_modified(self, event=None):
        if self.textbox._textbox.edit_modified():
            self._update_preview()
            self._adjust_textbox_height()
            self.textbox._textbox.edit_modified(False)
        else:
            # Для случаев, когда Modified не сработал (например, KeyRelease)
            self._adjust_textbox_height()

    def _auto_detect_frame(self):
        """Пытается автоматически найти границы марки на изображении."""
        try:
            img = self.stamp_image
            h, w = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Определяем фон для выбора метода порога
            is_dark = image_utils.detect_dark_background(img)
            if is_dark:
                # На темном фоне ищем светлую марку
                _, thresh = cv2.threshold(gray, 45, 255, cv2.THRESH_BINARY)
            else:
                # На светлом фоне ищем всё, что не белый
                _, thresh = cv2.threshold(gray, 225, 255, cv2.THRESH_BINARY_INV)
            
            # Закрываем дыры в контуре
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return

            # Берем самый большой контур (предположительно марка)
            cnt = max(contours, key=cv2.contourArea)
            if cv2.contourArea(cnt) < (w * h * 0.1): # Минимум 10% площади
                return

            # Получаем минимально охватывающий повернутый прямоугольник
            rect = cv2.minAreaRect(cnt)
            (cx, cy), (rw, rh), angle = rect
            
            # Нормализуем угол, чтобы рамка всегда была в пределах [-45, 45] (или около того), 
            # чтобы маркер вращения оставался физически наверху
            while angle <= -45:
                angle += 90
                rw, rh = rh, rw
            while angle > 45:
                angle -= 90
                rw, rh = rh, rw
                
            # Небольшой отступ внутрь, чтобы не захватить фон (уменьшаем на 2%)
            rw *= 0.98
            rh *= 0.98
            
            # Центрируем и сохраняем
            self.frame_x = cx - rw/2
            self.frame_y = cy - rh/2
            self.frame_w = rw
            self.frame_h = rh
            self.frame_angle = angle
            
        except Exception as e:
            # Если что-то пошло не так, оставляем значения по умолчанию
            print(f"Auto-detect frame error: {e}")

    def _adjust_textbox_height(self):
        """Динамически меняет высоту текстового поля под количество строк."""
        try:
            # Получаем количество строк
            content = self.textbox.get("1.0", "end-1c")
            num_lines = len(content.splitlines()) if content.strip() else 1
            if content.endswith('\n'):
                 num_lines += 1
            
            # Минимум 4 строки, максимум допустим 15, чтобы не уходило слишком далеко
            display_lines = max(4, num_lines)
            new_height = (display_lines * 26) + 20 # 26px на строку + отступы
            
            if self.textbox.cget("height") != new_height:
                self.textbox.configure(height=new_height)
        except:
            pass

    def _update_preview(self):
        if not self.winfo_exists(): return
        markup = self._serialize_text()
        rendered_pil = image_utils.render_stamp_with_caption(
            self.stamp_image, markup, True, self.parent.caption_font_size.get(),
            self.parent.caption_text_color.get(), self.parent.caption_align.get(),
            self.parent.caption_bg_color.get()
        )
        cw = self.crop_canvas.winfo_width()
        ch = self.crop_canvas.winfo_height()
        if cw < 50: cw, ch = 600, 600
        iw, ih = rendered_pil.size
        self.last_ratio = min((cw-40)/iw, (ch-40)/ih, 1.0)
        nw, nh = int(iw*self.last_ratio), int(ih*self.last_ratio)
        cx, cy = cw//2, ch//2
        ox, oy = cx - nw//2, cy - nh//2
        self.img_offset = (ox, oy)
        
        img_tk = ImageTk.PhotoImage(rendered_pil.resize((nw, nh), Image.Resampling.LANCZOS))
        self.crop_canvas.delete("all")
        self.crop_canvas.create_image(cx, cy, image=img_tk)
        self.crop_canvas.image = img_tk
        
        # Отрисовка рамки с учетом поворота
        handles = self._get_handles()
        nw_h, ne_h, sw_h, se_h = handles['nw'], handles['ne'], handles['sw'], handles['se']
        rot_h = handles['rotate']
        cx_f, cy_f = handles['center']
        
        # Линия от центра рамки до маркера вращения
        self.crop_canvas.create_line(cx_f, cy_f - int(self.frame_h*self.last_ratio/2), rot_h[0], rot_h[1], fill="red", dash=(4,2))
        
        # Контур рамки
        self.crop_canvas.create_polygon(*nw_h, *ne_h, *se_h, *sw_h, outline="red", fill="", width=2)
        
        # Маркер вращения
        r_rad = 8
        self.crop_canvas.create_oval(rot_h[0]-r_rad, rot_h[1]-r_rad, rot_h[0]+r_rad, rot_h[1]+r_rad, fill="white", outline="red", width=2)
        
        # Угловые маркеры
        for (hx, hy) in [nw_h, ne_h, sw_h, se_h]:
            s = 6
            self.crop_canvas.create_rectangle(hx-s, hy-s, hx+s, hy+s, fill="blue", outline="white")

    def _on_align_changed(self, value):
        self.parent.caption_align.set({"⬅":"left","⬛":"center","➡":"right"}.get(value,"center"))
        self._update_preview()

    def _on_color_changed(self, value):
        self.parent.caption_text_color.set({_("val_black"):"black",_("val_white"):"white",_("val_gray"):"gray",_("val_blue"):"blue",_("val_red"):"red"}.get(value,"black"))
        self._update_preview()

    def _on_bg_changed(self, value):
        self.parent.caption_bg_color.set({_("val_white"):"white",_("val_transparent"):"transparent"}.get(value,"white"))
        self._update_preview()

    def _rotate_image(self, degrees):
        """Повернуть само изображение марки на заданный угол."""
        h, w = self.stamp_image.shape[:2]
        center = (w/2, h/2)
        M = cv2.getRotationMatrix2D(center, -degrees, 1.0)
        # Вычислить новый размер изображения после поворота
        cos_val = abs(M[0,0])
        sin_val = abs(M[0,1])
        new_w = int(h * sin_val + w * cos_val)
        new_h = int(h * cos_val + w * sin_val)
        M[0,2] += (new_w/2) - center[0]
        M[1,2] += (new_h/2) - center[1]
        self.stamp_image = cv2.warpAffine(self.stamp_image, M, (new_w, new_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        # Сбросить рамку
        self.frame_x, self.frame_y = 20, 20
        self.frame_w = min(200, new_w - 40)
        self.frame_h = min(200, new_h - 40)
        self.frame_angle = 0
        self._update_preview()

    def _crop_image(self):
        # Обрезать изображение по рамке с учетом угла
        ang = self.frame_angle
        if abs(ang) > 0.5:
            # Повернуть изображение и затем обрезать прямоугольник
            h, w = self.stamp_image.shape[:2]
            center = (w/2, h/2)
            M = cv2.getRotationMatrix2D(center, ang, 1.0)
            rotated = cv2.warpAffine(self.stamp_image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            x = max(0, int(self.frame_x))
            y = max(0, int(self.frame_y))
            ww = min(int(self.frame_w), w - x)
            hh = min(int(self.frame_h), h - y)
            cropped = rotated[y:y+hh, x:x+ww]
        else:
            x = max(0, int(self.frame_x))
            y = max(0, int(self.frame_y))
            ww = min(int(self.frame_w), self.stamp_image.shape[1] - x)
            hh = min(int(self.frame_h), self.stamp_image.shape[0] - y)
            cropped = self.stamp_image[y:y+hh, x:x+ww]
        
        if cropped.size > 0:
            self.stamp_image = cropped
            self.frame_x, self.frame_y = 10, 10
            self.frame_w = min(200, cropped.shape[1]-20)
            self.frame_h = min(200, cropped.shape[0]-20)
            self.frame_angle = 0
            self._update_preview()

    def _save_and_close(self):
        markup = self._serialize_text()
        # Рендерим финальное фото с текстом как одно изображение
        final_pil = image_utils.render_stamp_with_caption(
            self.stamp_image, markup, bool(markup.strip()),
            self.parent.caption_font_size.get(),
            self.parent.caption_text_color.get(),
            self.parent.caption_align.get(),
            self.parent.caption_bg_color.get()
        )
        # Конвертируем PIL -> numpy (BGR) и сохраняем как новое изображение марки
        import numpy as _np
        final_np = cv2.cvtColor(_np.array(final_pil.convert("RGB")), cv2.COLOR_RGB2BGR)
        self.parent.extracted_stamps[self.index] = final_np
        self.parent.stamp_captions[self.index] = ""  # Текст уже запечён в изображение
        self.parent._update_stamp_thumbnail(self.index)
        self.destroy()
