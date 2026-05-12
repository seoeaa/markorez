from pathlib import Path

import cv2
import numpy as np


def test_otsu_and_border_thresholds():
    img_path = Path(__file__).with_name("stamp_05.png")
    img = cv2.imread(str(img_path))
    assert img is not None, f"Sample image not found: {img_path}"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours1, _ = cv2.findContours(thresh1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    assert contours1

    border_pixels = np.concatenate([gray[0, :], gray[-1, :], gray[:, 0], gray[:, -1]])
    median_bg = np.median(border_pixels)
    _, thresh2 = cv2.threshold(gray, median_bg + 15, 255, cv2.THRESH_BINARY)
    contours2, _ = cv2.findContours(thresh2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    assert contours2
