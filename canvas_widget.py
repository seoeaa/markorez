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
        
        # Состояние выделения и перемещения
        self.selected_box_index = -1
        self.is_dragging = False
        self.is_resizing = False
        self.resize_handle = None  # 'nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'
        self.drag_start = None
        self.drag_box_start = None
        
        # Размер маркера изменения размера
        self.handle_size = 8
        
        self.callback = None
        
        # События
        self.bind("<Configure>", self._on_resize)
        self.bind("<Button-1>", self._on_mouse_down)
        self.bind("<B1-Motion>", self._on_mouse_move)
        self.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.bind("<Button-3>", self._on_right_click)
        
        # Курсоры для разных режимов
        self.cursor_move = "fleur"
        self.cursor_resize_nwse = "sizing"
        self.cursor_resize_nesw = "sizing"
        self.cursor_resize_ns = "sb_v_double_arrow"
        self.cursor_resize_ew = "sb_h_double_arrow"

    def set_callback(self, callback):
        """Установить функцию обратного вызова для обновлений."""
        self.callback = callback

    def set_image(self, image: np.ndarray):
        """Установить новое базовое изображение."""
        self.original_image = image
        self.bounding_boxes = []
        self.draw_start = None
        self.draw_current = None
        self.selected_box_index = -1
        self.is_dragging = False
        self.is_resizing = False
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
        self.selected_box_index = -1
        self.redraw()

    def set_bounding_boxes(self, boxes):
        """Установить список рамок и перерисовать."""
        self.bounding_boxes = boxes
        self.selected_box_index = -1
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

        # Рисование элементов поверх PIL (для производительности)
        draw = ImageDraw.Draw(pil_img)
        line_w = max(2, int(disp_w / 400))

        for i, box in enumerate(self.bounding_boxes):
            # Точки для изменения размера (всегда 4 угла повернутого прямоугольника)
            rect_points = box.get_points()
            
            # Точки для отрисовки контура (точный контур, если есть, иначе углы рамки)
            contour_points = box.get_contour_points() if hasattr(box, 'get_contour_points') else rect_points
            
            # Масштабируем точки для отображения
            disp_contour = [(p[0] * self.scale_factor, p[1] * self.scale_factor) for p in contour_points]
            
            # Цвет рамки: выбранная - синий, обычная - зеленый
            if i == self.selected_box_index:
                box_color = "#3b82f6"  # Синий для выбранной
            else:
                box_color = "#10b981"  # Зеленый для обычной

            # Рисуем контур (многоугольник)
            draw.polygon(disp_contour, outline=box_color, width=line_w)

            # Метка номера (рисуем у верхней точки прямоугольника)
            disp_rect_points = [(p[0] * self.scale_factor, p[1] * self.scale_factor) for p in rect_points]
            disp_rect_points.sort(key=lambda p: p[1]) # Сортировка по Y
            sx, sy = disp_rect_points[0]
            label_h = max(16, int(disp_w / 40))
            label_w = max(30, int(disp_w / 20))
            draw.rectangle([sx, sy - label_h, sx + label_w, sy], fill=box_color)
            draw.text((sx + 4, sy - label_h + 2), f"#{i+1}", fill="white")
            
            # Рисуем маркеры изменения размера для выбранной рамки
            if i == self.selected_box_index:
                handle_size = self.handle_size
                
                # Угловые маркеры (используются реальные 4 угла повернутого прямоугольника)
                # Чтобы не менять много логики выделения в других функциях, 
                # будем рисовать ручки на 4-х углах bounding box.
                for hx, hy in disp_rect_points:
                    draw.rectangle(
                        [hx - handle_size//2, hy - handle_size//2, 
                         hx + handle_size//2, hy + handle_size//2],
                        fill=box_color,
                        outline="white",
                        width=1
                    )


        # Текущая рамка (в процессе рисования)
        if self.draw_start and self.draw_current:
            sx1, sy1 = self.draw_start
            sx2, sy2 = self.draw_current
            x1 = min(sx1, sx2)
            y1 = min(sy1, sy2)
            x2 = max(sx1, sx2)
            y2 = max(sy1, sy2)
            # Проверяем минимальный размер
            if x2 > x1 and y2 > y1:
                for offset in range(line_w):
                    nx1 = x1 + offset
                    ny1 = y1 + offset
                    nx2 = x2 - offset
                    ny2 = y2 - offset
                    if nx2 > nx1 and ny2 > ny1:
                        draw.rectangle(
                            [nx1, ny1, nx2, ny2],
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

    def _get_box_at_position(self, x, y):
        """Найти рамку по координатам экрана."""
        # Для повернутых рамок используем проверку попадания точки в многоугольник
        for i in range(len(self.bounding_boxes) - 1, -1, -1):
            box = self.bounding_boxes[i]
            points = box.get_points() # В координатах оригинала
            # Масштабируем точки
            disp_points = np.array([(p[0] * self.scale_factor, p[1] * self.scale_factor) for p in points], dtype=np.int32)
            
            if cv2.pointPolygonTest(disp_points, (x, y), False) >= 0:
                return i
        return -1

    def _get_resize_handle_at_position(self, x, y):
        """Определить, какой маркер изменения размера под курсором."""
        if self.selected_box_index < 0:
            return None
        
        box = self.bounding_boxes[self.selected_box_index]
        sx = int(box.x * self.scale_factor)
        sy = int(box.y * self.scale_factor)
        sw = int(box.width * self.scale_factor)
        sh = int(box.height * self.scale_factor)
        
        handle_size = self.handle_size
        
        # Проверяем угловые маркеры
        handles = [
            (sx, sy, 'nw'),
            (sx + sw, sy, 'ne'),
            (sx, sy + sh, 'sw'),
            (sx + sw, sy + sh, 'se'),
        ]
        
        for hx, hy, handle_name in handles:
            if (hx - handle_size//2 <= x <= hx + handle_size//2 and
                hy - handle_size//2 <= y <= hy + handle_size//2):
                return handle_name
        
        return None

    def _update_cursor(self, x, y):
        """Обновить курсор в зависимости от положения."""
        if self.original_image is None:
            return
        
        dx, dy = self._canvas_to_display(x, y)
        
        # Проверяем маркеры изменения размера
        handle = self._get_resize_handle_at_position(dx, dy)
        if handle:
            if handle in ('nw', 'se'):
                self.configure(cursor=self.cursor_resize_nwse)
            elif handle in ('ne', 'sw'):
                self.configure(cursor=self.cursor_resize_nesw)
            return
        
        # Проверяем внутри рамки
        box_idx = self._get_box_at_position(dx, dy)
        if box_idx >= 0:
            self.configure(cursor=self.cursor_move)
            return
        
        # Обычный режим
        if self.is_drawing_mode:
            self.configure(cursor="crosshair")
        else:
            self.configure(cursor="arrow")

    def _on_mouse_down(self, event):
        if self.original_image is None:
            return
        
        dx, dy = self._canvas_to_display(event.x, event.y)
        
        # Проверяем маркер изменения размера
        if self.selected_box_index >= 0:
            handle = self._get_resize_handle_at_position(dx, dy)
            if handle:
                self.is_resizing = True
                self.resize_handle = handle
                self.drag_start = (dx, dy)
                self.drag_box_start = BoundingBox(
                    self.bounding_boxes[self.selected_box_index].center,
                    self.bounding_boxes[self.selected_box_index].size,
                    self.bounding_boxes[self.selected_box_index].angle
                )
                return
        
        # Проверяем выбор рамки (не в режиме рисования)
        if not self.is_drawing_mode:
            box_idx = self._get_box_at_position(dx, dy)
            if box_idx >= 0:
                self.selected_box_index = box_idx
                self.is_dragging = True
                self.drag_start = (dx, dy)
                self.drag_box_start = BoundingBox(
                    self.bounding_boxes[box_idx].center,
                    self.bounding_boxes[box_idx].size,
                    self.bounding_boxes[box_idx].angle
                )
                self.redraw()
                return
            else:
                # Клик вне рамки - снимаем выделение
                if self.selected_box_index >= 0:
                    self.selected_box_index = -1
                    self.redraw()
        
        # Режим рисования
        if self.is_drawing_mode:
            self.draw_start = (dx, dy)
            self.draw_current = (dx, dy)

    def _on_mouse_move(self, event):
        if self.original_image is None:
            return
        
        dx, dy = self._canvas_to_display(event.x, event.y)
        
        # Обновляем курсор
        self._update_cursor(event.x, event.y)
        
        # Изменение размера
        if self.is_resizing and self.selected_box_index >= 0 and self.drag_start and self.drag_box_start:
            orig_dx, orig_dy = self.drag_start
            box = self.drag_box_start
            
            delta_x = int((dx - orig_dx) / self.scale_factor)
            delta_y = int((dy - orig_dy) / self.scale_factor)
            
            new_center = list(box.center)
            new_size = list(box.size)
            
            if self.resize_handle == 'se':
                new_size[0] = max(20, box.size[0] + delta_x)
                new_size[1] = max(20, box.size[1] + delta_y)
                new_center[0] = box.center[0] + delta_x / 2
                new_center[1] = box.center[1] + delta_y / 2
            elif self.resize_handle == 'sw':
                new_size[0] = max(20, box.size[0] - delta_x)
                new_size[1] = max(20, box.size[1] + delta_y)
                new_center[0] = box.center[0] + delta_x / 2
                new_center[1] = box.center[1] + delta_y / 2
            elif self.resize_handle == 'ne':
                new_size[0] = max(20, box.size[0] + delta_x)
                new_size[1] = max(20, box.size[1] - delta_y)
                new_center[0] = box.center[0] + delta_x / 2
                new_center[1] = box.center[1] + delta_y / 2
            elif self.resize_handle == 'nw':
                new_size[0] = max(20, box.size[0] - delta_x)
                new_size[1] = max(20, box.size[1] - delta_y)
                new_center[0] = box.center[0] + delta_x / 2
                new_center[1] = box.center[1] + delta_y / 2
            
            new_box = BoundingBox(tuple(new_center), tuple(new_size), box.angle)
            
            self.bounding_boxes[self.selected_box_index] = new_box
            self.redraw()
            return
        
        # Перемещение
        if self.is_dragging and self.selected_box_index >= 0 and self.drag_start and self.drag_box_start:
            orig_dx, orig_dy = self.drag_start
            box = self.drag_box_start
            
            delta_x = int((dx - orig_dx) / self.scale_factor)
            delta_y = int((dy - orig_dy) / self.scale_factor)
            
            # Ограничение перемещения в пределах изображения
            img_h, img_w = self.original_image.shape[:2]
            new_cx = max(0, min(box.center[0] + delta_x, img_w))
            new_cy = max(0, min(box.center[1] + delta_y, img_h))
            
            self.bounding_boxes[self.selected_box_index].center = (new_cx, new_cy)
            self.redraw()
            return
        
        # Рисование новой рамки
        if self.is_drawing_mode and self.draw_start:
            self.draw_current = (dx, dy)
            self.redraw()

    def _on_mouse_up(self, event):
        # Завершение изменения размера
        if self.is_resizing:
            self.is_resizing = False
            self.resize_handle = None
            self.drag_start = None
            self.drag_box_start = None
            return
        
        # Завершение перемещения
        if self.is_dragging:
            self.is_dragging = False
            self.drag_start = None
            self.drag_box_start = None
            return
        
        # Завершение рисования
        if self.is_drawing_mode and self.draw_start and self.draw_current:
            x1, y1 = self.draw_start
            x2, y2 = self.draw_current

            # Конвертируем в ориг. координаты
            ox1, oy1 = self._display_to_original(min(x1, x2), min(y1, y2))
            ox2, oy2 = self._display_to_original(max(x1, x2), max(y1, y2))

            width = ox2 - ox1
            height = oy2 - oy1

            if width > 10 and height > 10:
                cx = ox1 + width / 2
                cy = oy1 + height / 2
                self.bounding_boxes.append(BoundingBox((cx, cy), (width, height), 0.0))
                # Автоматически выбираем созданную рамку
                self.selected_box_index = len(self.bounding_boxes) - 1

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
            points = box.get_points()
            if cv2.pointPolygonTest(points, (ox, oy), False) >= 0:
                self.bounding_boxes.pop(i)
                if self.selected_box_index == i:
                    self.selected_box_index = -1
                elif self.selected_box_index > i:
                    self.selected_box_index -= 1
                self.redraw()
                break
