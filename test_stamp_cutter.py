import cv2
import numpy as np
import argparse
import os
import sys


# ── Шаг 1: грубая сегментация ─────────────────────────────────────────────────

def coarse_boxes(gray, img_w, img_h, thresh_val=55):
    _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
    k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    k_open  = cv2.getStructuringElement(cv2.MORPH_RECT, (6, 6))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, k_close)
    opened = cv2.morphologyEx(closed,  cv2.MORPH_OPEN,  k_open)
    contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    print(f"[DEBUG] img_w={img_w}, img_h={img_h}")
    print(f"[DEBUG] Found {len(contours)} initial contours")
    for cnt in contours:
        area = cv2.contourArea(cnt)
        x, y, bw, bh = cv2.boundingRect(cnt)
        aspect = bw / bh if bh else 0
        if area < 2000 or aspect > 8 or aspect < 0.1:
            continue
        print(f"[DEBUG] Valid contour: area={area}, aspect={aspect:.2f}, bw={bw}, bh={bh}")
        # Большой кластер → разбиваем изнутри
        if bw > img_w * 0.80 and bh > img_h * 0.60:
            print(f"[DEBUG] Breaking big cluster: bw={bw}, bh={bh}")
            roi = gray[y:y + bh, x:x + bw]
            _, rt = cv2.threshold(roi, thresh_val + 25, 255, cv2.THRESH_BINARY)
            ke = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            rt = cv2.erode(rt, ke, iterations=2)
            k2 = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 18))
            rc = cv2.morphologyEx(rt, cv2.MORPH_CLOSE, k2)
            subs, _ = cv2.findContours(rc, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            print(f"[DEBUG] Big cluster found {len(subs)} sub-contours")
            for sc in subs:
                if cv2.contourArea(sc) < 2000: continue
                sx, sy, sbw, sbh = cv2.boundingRect(sc)
                if (sbw / sbh if sbh else 0) > 8: continue
                # Игнорировать гигантский контур, который охватывает весь сканер
                if sbw > img_w * 0.9 and sbh > img_h * 0.9:
                    print(f"  [DEBUG] Skipping giant sub-contour: bw={sbw}, bh={sbh}")
                    continue
                print(f"  [DEBUG] Sub-contour valid: area={cv2.contourArea(sc)}, bw={sbw}, bh={sbh}")
                boxes.append((x + sx, y + sy, sbw, sbh))
        else:
            boxes.append((x, y, bw, bh))

    print(f"[DEBUG] Total coarse boxes before merge: {len(boxes)}")

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


# ── Шаг 2: точный контур по Canny-рёбрам → minAreaRect ────────────────────────

def precise_rect(gray, box, pad_outer=25, pad_crop=3):
    """
    Ищет точный контур марки в ROI с небольшим запасом (pad_outer),
    возвращает minAreaRect с итоговым отступом pad_crop пикселей.
    """
    x, y, bw, bh = box
    ih, iw = gray.shape[:2]
    x1=max(x-pad_outer,0); y1=max(y-pad_outer,0)
    x2=min(x+bw+pad_outer,iw); y2=min(y+bh+pad_outer,ih)
    roi_g = gray[y1:y2, x1:x2]

    # Canny-рёбра дают точные границы без раздутия
    edges = cv2.Canny(roi_g, 15, 60)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, k)

    cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    cnt = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(cnt) < 800:
        return None

    cnt_full = cnt + np.array([x1, y1])
    center, (rw, rh), angle = cv2.minAreaRect(cnt_full)
    # Добавляем минимальный отступ
    return (center, (rw + pad_crop * 2, rh + pad_crop * 2), angle)


# ── Шаг 3: вырезание с поворотом ──────────────────────────────────────────────

def crop_rotated(img, rect):
    center, (rw, rh), angle = rect
    if rh > rw:
        rw, rh = rh, rw
        angle += 90
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    ih, iw = img.shape[:2]
    rotated = cv2.warpAffine(img, M, (iw, ih),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    cx, cy = int(center[0]), int(center[1])
    x1=max(cx-int(rw/2),0); y1=max(cy-int(rh/2),0)
    x2=min(cx+int(rw/2),iw); y2=min(cy+int(rh/2),ih)
    return rotated[y1:y2, x1:x2]


# ── Главная функция ────────────────────────────────────────────────────────────

def run(image_path, output_dir, thresh_val, pad_crop):
    img = cv2.imread(image_path)
    if img is None:
        sys.exit(f"[ERROR] Не могу открыть файл: {image_path}")
    os.makedirs(output_dir, exist_ok=True)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    boxes = coarse_boxes(gray, w, h, thresh_val)
    if not boxes:
        print("[WARN] Марки не найдены. Попробуйте изменить --thresh.")
        return

    debug = img.copy()
    for i, box in enumerate(boxes, start=1):
        rect = precise_rect(gray, box, pad_outer=25, pad_crop=pad_crop)
        if rect is not None:
            # Исправление для numpy 'int0' если нужно, но пока используем int()
            crop = crop_rotated(img, rect)
            pts = cv2.boxPoints(rect).astype(np.int32)
            cv2.drawContours(debug, [pts], 0, (0, 255, 0), 2)
            cx, cy = int(rect[0][0]), int(rect[0][1])
        else:
            x, y, bw, bh = box
            p = pad_crop
            crop = img[max(y-p,0):min(y+bh+p,h), max(x-p,0):min(x+bw+p,w)]
            cv2.rectangle(debug,(x-p,y-p),(x+bw+p,y+bh+p),(0,165,255),2)
            cx, cy = x+bw//2, y+bh//2

        cv2.putText(debug, str(i), (cx-10, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)
        cv2.imwrite(os.path.join(output_dir, f"stamp_{i:02d}.png"), crop)

    cv2.imwrite(os.path.join(output_dir, "_debug.png"), debug)
    print(f"[OK] Найдено и сохранено марок: {len(boxes)}")
    print(f"     Папка: {os.path.abspath(output_dir)}")
    print(f"     Разметка: {output_dir}/_debug.png")


def main():
    parser = argparse.ArgumentParser(
        description="Вырезает марки вплотную к краям, выравнивает повёрнутые."
    )
    parser.add_argument("image", help="Путь к входному изображению")
    parser.add_argument("--out",    default="stamps_output", help="Папка для сохранения")
    parser.add_argument("--thresh", type=int, default=55,
                        help="Порог бинаризации 0–255 (по умолчанию 55)")
    parser.add_argument("--pad",    type=int, default=3,
                        help="Отступ от края марки в пикселях (по умолчанию 3)")
    args = parser.parse_args()
    run(args.image, args.out, args.thresh, args.pad)

if __name__ == "__main__":
    main()
