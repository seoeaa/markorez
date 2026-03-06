import cv2
import numpy as np
import os
from PIL import Image, ImageDraw, ImageFont

class BoundingBox:
    """Представляет ограничивающую рамку найденного объекта (может быть повернута)."""
    def __init__(self, center: tuple[float, float], size: tuple[float, float], angle: float, contour: np.ndarray = None):
        self.center = center  # (x, y)
        self.size = size      # (w, h)
        self.angle = angle    # градусы
        self.contour = contour

    @property
    def x(self) -> int:
        return int(self.center[0] - self.size[0] / 2)

    @property
    def y(self) -> int:
        return int(self.center[1] - self.size[1] / 2)

    @property
    def width(self) -> int:
        return int(self.size[0])

    @property
    def height(self) -> int:
        return int(self.size[1])

    def get_points(self) -> np.ndarray:
        """Возвращает 4 угла рамки."""
        box = cv2.boxPoints((self.center, self.size, self.angle))
        return np.int32(box)
        
    def get_contour_points(self) -> np.ndarray:
        """Возвращает точный контур объекта, если он есть."""
        if self.contour is not None:
            return self.contour.astype(np.int32)
        return self.get_points()

    def area(self) -> float:
        return self.size[0] * self.size[1]


def coarse_boxes(gray: np.ndarray, thresh_val: int) -> list[tuple[int, int, int, int]]:
    """Шаг 1: грубая сегментация из Stamp Cutter v3."""
    _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
    k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    k_open  = cv2.getStructuringElement(cv2.MORPH_RECT, (6, 6))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, k_close)
    opened = cv2.morphologyEx(closed,  cv2.MORPH_OPEN,  k_open)
    contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    img_h, img_w = gray.shape[:2]
    for cnt in contours:
        area = cv2.contourArea(cnt)
        x, y, bw, bh = cv2.boundingRect(cnt)
        aspect = bw / bh if bh else 0
        if area < 2000 or aspect > 8 or aspect < 0.1:
            continue
        # Большой кластер → разбиваем изнутри
        if bw > img_w * 0.80 and bh > img_h * 0.60:
            roi = gray[y:y + bh, x:x + bw]
            _, rt = cv2.threshold(roi, thresh_val + 25, 255, cv2.THRESH_BINARY)
            ke = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            rt = cv2.erode(rt, ke, iterations=2)
            k2 = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 18))
            rc = cv2.morphologyEx(rt, cv2.MORPH_CLOSE, k2)
            subs, _ = cv2.findContours(rc, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for sc in subs:
                if cv2.contourArea(sc) < 2000: continue
                sx, sy, sbw, sbh = cv2.boundingRect(sc)
                if (sbw / sbh if sbh else 0) > 8: continue
                # Игнорировать гигантский контур, который охватывает весь сканер
                if sbw > img_w * 0.9 and sbh > img_h * 0.9: continue
                boxes.append((x + sx, y + sy, sbw, sbh))
        else:
            boxes.append((x, y, bw, bh))

    return _merge(boxes)

def _merge(boxes, gap=8):
    if not boxes: return []
    rects = [[x, y, x+bw, y+bh] for x, y, bw, bh in boxes]
    merged = True
    while merged:
        merged = False; out = []; used = [False] * len(rects)
        for i in range(len(rects)):
            if used[i]: continue
            x1,y1,x2,y2 = rects[i]
            for j in range(i+1, len(rects)):
                if used[j]: continue
                ax1,ay1,ax2,ay2 = rects[j]
                if x1-gap<=ax2 and ax1-gap<=x2 and y1-gap<=ay2 and ay1-gap<=y2:
                    x1,y1=min(x1,ax1),min(y1,ay1); x2,y2=max(x2,ax2),max(y2,ay2)
                    used[j]=True; merged=True
            out.append([x1,y1,x2,y2]); used[i]=True
        rects = out
    return [(r[0],r[1],r[2]-r[0],r[3]-r[1]) for r in rects]


def precise_rect(gray: np.ndarray, coarse_box: tuple[int, int, int, int], pad: int = 0) -> BoundingBox:
    """Шаг 2: точный контур по Canny-рёбрам → minAreaRect."""
    x, y, bw, bh = coarse_box
    ih, iw = gray.shape[:2]
    pad_outer = 25
    x1=max(x-pad_outer,0); y1=max(y-pad_outer,0)
    x2=min(x+bw+pad_outer,iw); y2=min(y+bh+pad_outer,ih)
    roi_g = gray[y1:y2, x1:x2]

    # Canny-рёбра дают точные границы без раздутия
    edges = cv2.Canny(roi_g, 15, 60)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, k)

    cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if cnts:
        cnt = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(cnt) >= 800:
            cnt_full = cnt + np.array([x1, y1])
            center, (rw, rh), angle = cv2.minAreaRect(cnt_full)
            # Добавляем минимальный отступ
            return BoundingBox(center, (rw + pad * 2, rh + pad * 2), angle, contour=cnt_full)

    # Если точный контур не найден, возвращаем обычный бокс
    pts = np.array([
        [x, y], [x + bw, y], [x + bw, y + bh], [x, y + bh]
    ])
    return BoundingBox((float(x+bw/2), float(y+bh/2)), (float(bw + pad*2), float(bh + pad*2)), 0.0, contour=pts)


def process_image(
    image: np.ndarray,
    threshold: int = -1,
    min_area: int = 5000,
    blur_radius: int = 3,
    invert: bool = False,
    pad: int = 0
) -> list[BoundingBox]:
    """Обработка изображения для нахождения марок с использованием Stamp Cutter v3 логики."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Если порог не задан, используем Оцу для определения базового порога
    if threshold == -1:
        if invert:
             thresh_val, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
             thresh_val, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    else:
        thresh_val = threshold

    # 1. Грубый поиск областей
    c_boxes = coarse_boxes(gray, thresh_val)
    
    # 2. Уточнение каждой области
    results: list[BoundingBox] = []
    for cb in c_boxes:
        bbox = precise_rect(gray, cb, pad=pad)
        if bbox.area() >= min_area:
            results.append(bbox)

    # Сортировка (сверху вниз, слева направо)
    results.sort(key=lambda b: (b.center[1] // 100, b.center[0]))
    return results


def crop_rotated(img: np.ndarray, bbox: BoundingBox) -> np.ndarray:
    """Шаг 3: вырезание с поворотом и маскированием фона по контуру."""
    center, size, angle = bbox.center, bbox.size, bbox.angle
    rw, rh = size
    ih, iw = img.shape[:2]
    
    # 1. Конвертация в RGBA, чтобы можно было сделать фон прозрачным
    if img.shape[2] == 3:
        img_rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    else:
        img_rgba = img.copy()
        
    # 2. Создание маски контура и применение её к альфа-каналу
    mask = np.zeros((ih, iw), dtype=np.uint8)
    if hasattr(bbox, 'contour') and bbox.contour is not None:
        cv2.drawContours(mask, [bbox.contour.astype(np.int32)], -1, 255, -1)
    else:
        box_points = cv2.boxPoints((center, size, angle))
        cv2.drawContours(mask, [np.int32(box_points)], -1, 255, -1)
        
    img_rgba[:, :, 3] = mask
    
    # 3. Поворот
    if rh > rw:
        rw, rh = rh, rw
        angle += 90
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    rotated = cv2.warpAffine(img_rgba, M, (iw, ih),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=(0, 0, 0, 0))
                              
    # 4. Обрезка
    cx, cy = int(center[0]), int(center[1])
    x1=max(cx-int(rw/2),0); y1=max(cy-int(rh/2),0)
    x2=min(cx+int(rw/2),iw); y2=min(cy+int(rh/2),ih)
    return rotated[y1:y2, x1:x2]


def detect_dark_background(image: np.ndarray) -> bool:
    """Определяет, тёмный ли фон изображения (по углам)."""
    h, w = image.shape[:2]
    corner_size = max(10, min(w, h) // 20)
    
    corners = [
        image[0:corner_size, 0:corner_size],
        image[0:corner_size, w-corner_size:w],
        image[h-corner_size:h, 0:corner_size],
        image[h-corner_size:h, w-corner_size:w],
    ]
    
    avg_luminance = np.mean([np.mean(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)) for c in corners])
    return avg_luminance < 128


def get_font(size: int, bold: bool = False, italic: bool = False):
    """Получить шрифт для подписи с поддержкой bold/italic."""
    font_variants = {
        (True, True): [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/arialbi.ttf",
            "C:/Windows/Fonts/calibriz.ttf",
        ],
        (True, False): [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
        ],
        (False, True): [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            "C:/Windows/Fonts/ariali.ttf",
            "C:/Windows/Fonts/calibrii.ttf",
        ],
        (False, False): [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ],
    }

    paths = font_variants.get((bold, italic), font_variants[(False, False)])
    for fp in paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    
    # Резервные пути для Linux если DejaVu не найден
    linux_backups = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf"
    ]
    for fp in linux_backups:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue

    return ImageFont.load_default()


def parse_markup(markup):
    """Разбивает строку с <b> и <i> на список сегментов."""
    import re
    parts = re.split(r'(<b>|</b>|<i>|</i>)', markup)
    segments = []
    is_bold = False
    is_italic = False
    
    for part in parts:
        if part == "<b>": is_bold = True
        elif part == "</b>": is_bold = False
        elif part == "<i>": is_italic = True
        elif part == "</i>": is_italic = False
        elif part:
            segments.append({
                "text": part,
                "bold": is_bold,
                "italic": is_italic
            })
    return segments


def get_segment_width(segment, font_size, draw):
    """Вычисляет ширину сегмента текста."""
    font = get_font(font_size, bold=segment.get("bold", False), italic=segment.get("italic", False))
    bbox = draw.textbbox((0, 0), segment["text"], font=font)
    return bbox[2] - bbox[0], font


def wrap_rich_text(markup: str, font_size: int, max_width: int, draw: ImageDraw.Draw) -> list:
    """Разбивает текст с разметкой на строки."""
    all_lines = []
    
    for para_markup in markup.split("\n"):
        para_segments = parse_markup(para_markup)
        if not para_segments:
            all_lines.append([])
            continue
            
        current_line = []
        current_line_width = 0
        
        for seg in para_segments:
            words = seg["text"].split(" ")
            for i, word in enumerate(words):
                if not word and i != len(words) - 1:
                    # Одиночный пробел, если он есть между словами
                    continue
                    
                # Если это не первое слово в сегменте и мы не в начале строки, добавим пробел
                needs_space = (i > 0 or current_line) and current_line
                actual_text = " " + word if needs_space else word
                
                word_seg = seg.copy()
                word_seg["text"] = actual_text
                w, _ = get_segment_width(word_seg, font_size, draw)
                
                # Если слово длиннее max_width, разбиваем его на части
                if w > max_width:
                    # Сначала добавляем текущую строку, если она не пустая
                    if current_line:
                        all_lines.append(current_line)
                        current_line = []
                        current_line_width = 0
                    
                    # Разбиваем слово на части
                    word_seg_clean = seg.copy()
                    word_seg_clean["text"] = word
                    char_width = w / len(word) if len(word) > 0 else font_size / 2
                    chars_per_line = max(1, int(max_width / char_width))
                    
                    for j in range(0, len(word), chars_per_line):
                        part = word[j:j + chars_per_line]
                        part_seg = seg.copy()
                        part_seg["text"] = part
                        part_w, _ = get_segment_width(part_seg, font_size, draw)
                        
                        if current_line_width + part_w <= max_width or not current_line:
                            current_line.append(part_seg)
                            current_line_width += part_w
                        else:
                            if current_line:
                                all_lines.append(current_line)
                            current_line = [part_seg]
                            current_line_width = part_w
                elif current_line_width + w <= max_width or (not current_line and needs_space is False):
                    # Помещается в текущую строку, либо строка пустая и слово длиннее ширины (выводим как есть)
                    current_line.append(word_seg)
                    current_line_width += w
                else:
                    # Не помещается, переносим на новую строку
                    if current_line:
                        all_lines.append(current_line)
                    
                    word_seg["text"] = word.strip() if word.strip() else word
                    w, _ = get_segment_width(word_seg, font_size, draw)
                    current_line = [word_seg]
                    current_line_width = w
                    
        if current_line:
            all_lines.append(current_line)
            
    return all_lines


def render_stamp_with_caption(
    stamp: np.ndarray, 
    caption: str, 
    captions_enabled: bool,
    font_size: int,
    text_color: str,
    align: str,
    bg_style: str
) -> Image.Image:
    """Рендерит марку с Rich Text подписью."""
    if stamp.shape[2] == 4:
        rgb = cv2.cvtColor(stamp, cv2.COLOR_BGRA2RGBA)
        stamp_img = Image.fromarray(rgb, "RGBA")
    else:
        rgb = cv2.cvtColor(stamp, cv2.COLOR_BGR2RGB)
        stamp_img = Image.fromarray(rgb, "RGB")
        
    stamp_w, stamp_h = stamp_img.size

    if not captions_enabled or not caption.strip():
        return stamp_img

    temp_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    max_text_w = stamp_w - int(font_size) 
    
    lines = wrap_rich_text(caption, font_size, max_text_w, temp_draw)
    
    line_height = int(font_size * 1.4)
    padding_v = int(font_size * 0.5)
    caption_h = len(lines) * line_height + padding_v * 2
    
    if bg_style == "transparent":
        res_img = Image.new("RGBA", (stamp_w, stamp_h + caption_h), (255, 255, 255, 0))
    else:
        res_img = Image.new("RGBA", (stamp_w, stamp_h + caption_h), "white")
        
    mask = stamp_img if stamp_img.mode == "RGBA" else None
    res_img.paste(stamp_img, (0, 0), mask)
    draw = ImageDraw.Draw(res_img)
    
    curr_y = stamp_h + padding_v
    
    for line in lines:
        if not line:
            curr_y += line_height
            continue
            
        total_w = 0
        line_segments = []
        for seg in line:
            w, font = get_segment_width(seg, font_size, draw)
            line_segments.append((seg, w, font))
            total_w += w
        
        if align == "center":
            curr_x = (stamp_w - total_w) // 2
        elif align == "right":
            curr_x = stamp_w - total_w - int(font_size * 0.5)
        else: # left
            curr_x = int(font_size * 0.5)
            
        for seg, w, font in line_segments:
            draw.text((curr_x, curr_y), seg["text"], font=font, fill=text_color)
            curr_x += w
            
        curr_y += line_height
        
    return res_img
