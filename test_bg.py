from pathlib import Path

import cv2
import numpy as np


def test_background_stats():
    img_path = Path(__file__).with_name("stamp_05.png")
    img = cv2.imread(str(img_path))
    assert img is not None, f"Sample image not found: {img_path}"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    assert gray.size > 0

    corners = [gray[0, 0], gray[0, -1], gray[-1, 0], gray[-1, -1]]
    assert len(corners) == 4

    found_any = False
    for th in [30, 45, 60, 80, 100]:
        _, thresh = cv2.threshold(gray, th, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            found_any = True
            cnt = max(contours, key=cv2.contourArea)
            rect = cv2.minAreaRect(cnt)
            assert rect[1][0] >= 0 and rect[1][1] >= 0

    assert found_any
