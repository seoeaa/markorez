import cv2
import numpy as np
import math

img = cv2.imread('/storage/PYTHON/markorez/stamp_05.png')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 225, 255, cv2.THRESH_BINARY_INV)
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cnt = max(contours, key=cv2.contourArea)
rect = cv2.minAreaRect(cnt)
(cx, cy), (rw, rh), angle = rect
rw *= 0.98
rh *= 0.98

frame_x = cx - rw/2
frame_y = cy - rh/2
frame_w = rw
frame_h = rh
frame_angle = angle

# Now emulate _get_handles
ox, oy, r = 0, 0, 1.0 # assume scaled 1.0, positioned at origin
sx = ox + frame_x * r
sy = oy + frame_y * r
sw = frame_w * r
sh = frame_h * r
cx_f = sx + sw/2
cy_f = sy + sh/2
ang = np.radians(frame_angle)

def rot(ox2, oy2):
    rx = ox2*np.cos(ang) - oy2*np.sin(ang)
    ry = ox2*np.sin(ang) + oy2*np.cos(ang)
    return cx_f+rx, cy_f+ry

nw = rot(-sw/2, -sh/2)
ne = rot(sw/2, -sh/2)
print(f"Rect result:")
print(f"frame_x={frame_x}, frame_y={frame_y}, frame_w={frame_w}, frame_h={frame_h}, frame_angle={frame_angle}")
print(f"Center: ({cx_f}, {cy_f})")
print(f"Handles NW: {nw}, NE: {ne}")

