import cv2
import numpy as np
import os
from PIL import Image, ImageDraw, ImageFont

class BoundingBox:
    """Представляет ограничивающую рамку найденного объекта."""
    def __init__(self, x: int, y: int, width: int, height: int, angle: float = 0.0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.angle = angle

    def area(self) -> int:
        return self.width * self.height

    def overlaps(self, other: 'BoundingBox', margin: int = 15) -> bool:
        """Проверяет перекрытие с другой рамкой (с учётом отступа)."""
        overlap_x = (self.x < other.x + other.width + margin and
                     self.x + self.width + margin > other.x)
        overlap_y = (self.y < other.y + other.height + margin and
                     self.y + self.height + margin > other.y)
        return overlap_x and overlap_y

    def merge(self, other: 'BoundingBox') -> 'BoundingBox':
        """Объединяет две рамки в одну."""
        min_x = min(self.x, other.x)
        min_y = min(self.y, other.y)
        max_x = max(self.x + self.width, other.x + other.width)
        max_y = max(self.y + self.height, other.y + other.height)
        return BoundingBox(min_x, min_y, max_x - min_x, max_y - min_y)


def process_image(
    image: np.ndarray,
    threshold: int = -1,
    min_area: int = 5000,
    blur_radius: int = 3,
    invert: bool = False
) -> list[BoundingBox]:
    """Обработка изображения для нахождения марок."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if threshold == -1:
        if invert:
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    else:
        if invert:
            _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        else:
            _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)

    if blur_radius > 0:
        kernel_size = blur_radius * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        binary = cv2.dilate(binary, kernel, iterations=1)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    results: list[BoundingBox] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w * h >= min_area:
            results.append(BoundingBox(x, y, w, h))

    merged = True
    while merged:
        merged = False
        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                if results[i].overlaps(results[j]):
                    results[i] = results[i].merge(results[j])
                    results.pop(j)
                    merged = True
                    break
            if merged:
                break

    results.sort(key=lambda b: (b.y // 50, b.x))
    return results


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
    rgb = cv2.cvtColor(stamp, cv2.COLOR_BGR2RGB)
    stamp_img = Image.fromarray(rgb)
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
        res_img = Image.new("RGB", (stamp_w, stamp_h + caption_h), "white")
        
    res_img.paste(stamp_img, (0, 0))
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
