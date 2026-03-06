import cv2
import numpy as np

img = cv2.imread('/storage/PYTHON/markorez/stamp_05.png')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

_, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite('/tmp/thresh_otsu.png', thresh1)
contours, _ = cv2.findContours(thresh1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
if contours:
    cnt = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(cnt)
    print(f"Otsu rect size {rect[1]}, area {cv2.contourArea(cnt)}")
else:
    print(f"Otsu no contours")

# What if we just use a slightly expanded margin mean?
border_pixels = np.concatenate([
    gray[0, :], gray[-1, :], gray[:, 0], gray[:, -1]
])
median_bg = np.median(border_pixels)
print("Median BG:", median_bg)
_, thresh2 = cv2.threshold(gray, median_bg + 15, 255, cv2.THRESH_BINARY)
contours, _ = cv2.findContours(thresh2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
if contours:
    cnt = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(cnt)
    print(f"Median+15 rect size {rect[1]}, area {cv2.contourArea(cnt)}")
else:
    print(f"Median+15 no contours")

