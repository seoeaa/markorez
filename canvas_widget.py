import tkinter as tk
import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw
from image_utils import BoundingBox
from constants import COLORS

class StampCanvas(tk.Canvas):
    """
    Специализированный виджет холста для отображения изображения,
    рисования рамок и управления ими.
    """
    def __init__(self, parent, **kwargs):
        # Настройка фона и отсутствия рамок по умолчанию
        kwargs.setdefault("bg", COLORS["bg"])
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)
        
        self.parent = parent
        self.original_image = None
        self.bounding_boxes = []
        
        # Состояние отображения
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.photo_image = None
        
        # Состояние рисования
        self.is_drawing_mode = False
        self.draw_start = None
        self.draw_current = None
        
        self.callback = None
        
        # События
        self.bind("<Configure>", self._on_resize)
        self.bind("<Button-1>", self._on_mouse_down)
        self.bind("<B1-Motion>", self._on_mouse_move)
        self.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.bind("<Button-3>", self._on_right_click)

    def set_callback(self, callback):
        """Установить функцию обратного вызова для обновлений."""
        self.callback = callback

    def set_image(self, image: np.ndarray):
        """Установить новое базовое изображение."""
        self.original_image = image
        self.bounding_boxes = []
        self.draw_start = None
        self.draw_current = None
        self.redraw()

    def set_drawing_mode(self, enabled: bool):
        """Включить или выключить режим рисования."""
        self.is_drawing_mode = enabled
        self.configure(cursor="crosshair" if enabled else "arrow")
        if not enabled:
            self.draw_start = None
            self.draw_current = None
        self.redraw()

    def toggle_drawing_mode(self):
        """Переключить режим рисования и вернуть текущее состояние."""
        self.set_drawing_mode(not self.is_drawing_mode)
        return self.is_drawing_mode

    def clear_boxes(self):
        """Очистить все рамки."""
        self.bounding_boxes = []
        self.redraw()

    def set_bounding_boxes(self, boxes):
        """Установить список рамок и перерисовать."""
        self.bounding_boxes = boxes
        self.redraw()

    def _on_resize(self, event):
        self.redraw()

    def redraw(self):
        """Полная перерисовка содержимого."""
        if self.original_image is None:
            self.delete("all")
            return

        canvas_w = self.winfo_width()
        canvas_h = self.winfo_height()

        if canvas_w < 10 or canvas_h < 10:
            return

        img_h, img_w = self.original_image.shape[:2]

        # Вычислить масштаб
        self.scale_factor = min(canvas_w / img_w, canvas_h / img_h, 1.0)
        disp_w = int(img_w * self.scale_factor)
        disp_h = int(img_h * self.scale_factor)

        # Центрирование
        self.offset_x = (canvas_w - disp_w) // 2
        self.offset_y = (canvas_h - disp_h) // 2

        # Подготовка изображения для отображения
        resized = cv2.resize(self.original_image, (disp_w, disp_h), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)

        # Рисование элементов поверх PIL (для производительности или последующего извлечения)
        # Но на самом деле для отображения лучше рисовать прямо на Canvas или на PIL
        # В оригинале рисовалось на PIL. Сохраним этот подход.
        draw = ImageDraw.Draw(pil_img)
        line_w = max(2, int(disp_w / 400))

        for i, box in enumerate(self.bounding_boxes):
            sx = int(box.x * self.scale_factor)
            sy = int(box.y * self.scale_factor)
            sw = int(box.width * self.scale_factor)
            sh = int(box.height * self.scale_factor)

            # Рамка
            for offset in range(line_w):
                draw.rectangle(
                    [sx + offset, sy + offset, sx + sw - offset, sy + sh - offset],
                    outline="#10b981"
                )

            # Метка номера
            label_h = max(16, int(disp_w / 40))
            label_w = max(30, int(disp_w / 20))
            draw.rectangle([sx, sy - label_h, sx + label_w, sy], fill="#10b981")
            draw.text((sx + 4, sy - label_h + 2), f"#{i+1}", fill="white")

        # Текущая рамка (в процессе рисования)
        if self.draw_start and self.draw_current:
            sx1, sy1 = self.draw_start
            sx2, sy2 = self.draw_current
            x1 = min(sx1, sx2)
            y1 = min(sy1, sy2)
            x2 = max(sx1, sx2)
            y2 = max(sy1, sy2)
            for offset in range(line_w):
                draw.rectangle(
                    [x1 + offset, y1 + offset, x2 - offset, y2 - offset],
                    outline="#3b82f6"
                )

        self.photo_image = ImageTk.PhotoImage(pil_img)
        self.delete("all")
        self.create_image(self.offset_x, self.offset_y, anchor="nw", image=self.photo_image)
        
        if self.callback:
            self.callback(len(self.bounding_boxes))
        elif hasattr(self.parent, "_on_canvas_updated"):
            self.parent._on_canvas_updated(len(self.bounding_boxes))

    def _canvas_to_display(self, x, y):
        return x - self.offset_x, y - self.offset_y

    def _display_to_original(self, x, y):
        if self.scale_factor == 0:
            return 0, 0
        return int(x / self.scale_factor), int(y / self.scale_factor)

    def _on_mouse_down(self, event):
        if not self.is_drawing_mode or self.original_image is None:
            return
        x, y = self._canvas_to_display(event.x, event.y)
        self.draw_start = (x, y)
        self.draw_current = (x, y)

    def _on_mouse_move(self, event):
        if not self.is_drawing_mode or self.draw_start is None:
            return
        x, y = self._canvas_to_display(event.x, event.y)
        self.draw_current = (x, y)
        self.redraw()

    def _on_mouse_up(self, event):
        if not self.is_drawing_mode or self.draw_start is None or self.draw_current is None:
            return

        x1, y1 = self.draw_start
        x2, y2 = self.draw_current

        # Конвертируем в ориг. координаты
        ox1, oy1 = self._display_to_original(min(x1, x2), min(y1, y2))
        ox2, oy2 = self._display_to_original(max(x1, x2), max(y1, y2))

        width = ox2 - ox1
        height = oy2 - oy1

        if width > 10 and height > 10:
            self.bounding_boxes.append(BoundingBox(ox1, oy1, width, height))

        self.draw_start = None
        self.draw_current = None
        self.redraw()

    def _on_right_click(self, event):
        if self.original_image is None:
            return

        dx, dy = self._canvas_to_display(event.x, event.y)
        ox, oy = self._display_to_original(dx, dy)

        # Удаление рамки
        for i in range(len(self.bounding_boxes) - 1, -1, -1):
            box = self.bounding_boxes[i]
            if (box.x <= ox <= box.x + box.width and
                box.y <= oy <= box.y + box.height):
                self.bounding_boxes.pop(i)
                self.redraw()
                break
