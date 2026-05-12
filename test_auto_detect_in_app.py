from pathlib import Path

import cv2
import numpy as np

import image_utils


class DummyStampEditorWindow:
    def __init__(self, img_path):
        self.stamp_image = cv2.imread(str(img_path))
        self.frame_x = 0
        self.frame_y = 0
        self.frame_w = 100
        self.frame_h = 100
        self.frame_angle = 0

    def auto_detect_frame(self):
        img = self.stamp_image
        assert img is not None
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        is_dark = image_utils.detect_dark_background(img)
        border_pixels = np.concatenate([gray[0, :], gray[-1, :], gray[:, 0], gray[:, -1]])
        median_bg = np.median(border_pixels)

        if is_dark:
            thresh_val = min(255, median_bg + 15)
            _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
        else:
            thresh_val = max(0, median_bg - 15)
            _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return

        cnt = max(contours, key=cv2.contourArea)
        if cv2.contourArea(cnt) < (w * h * 0.1):
            return

        (cx, cy), (rw, rh), angle = cv2.minAreaRect(cnt)
        while angle <= -45:
            angle += 90
            rw, rh = rh, rw
        while angle > 45:
            angle -= 90
            rw, rh = rh, rw

        rw *= 0.98
        rh *= 0.98
        self.frame_x = cx - rw / 2
        self.frame_y = cy - rh / 2
        self.frame_w = rw
        self.frame_h = rh
        self.frame_angle = angle


def test_auto_detect_frame_smoke():
    img_path = Path(__file__).with_name("stamp_05.png")
    editor = DummyStampEditorWindow(img_path)
    editor.auto_detect_frame()
    assert editor.frame_w > 0
    assert editor.frame_h > 0
