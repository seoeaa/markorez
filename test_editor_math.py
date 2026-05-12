from pathlib import Path

import cv2
import numpy as np


def test_handle_math_smoke():
    img_path = Path(__file__).with_name("stamp_05.png")
    img = cv2.imread(str(img_path))
    assert img is not None, f"Sample image not found: {img_path}"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 225, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    assert contours

    cnt = max(contours, key=cv2.contourArea)
    (cx, cy), (rw, rh), angle = cv2.minAreaRect(cnt)
    rw *= 0.98
    rh *= 0.98

    frame_x = cx - rw / 2
    frame_y = cy - rh / 2
    sx, sy, sw, sh = frame_x, frame_y, rw, rh
    cx_f = sx + sw / 2
    cy_f = sy + sh / 2
    ang = np.radians(angle)

    def rot(ox2, oy2):
        rx = ox2 * np.cos(ang) - oy2 * np.sin(ang)
        ry = ox2 * np.sin(ang) + oy2 * np.cos(ang)
        return cx_f + rx, cy_f + ry

    nw = rot(-sw / 2, -sh / 2)
    ne = rot(sw / 2, -sh / 2)
    assert nw != ne
