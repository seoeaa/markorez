import cv2
import numpy as np

img = cv2.imread('/storage/PYTHON/markorez/stamp_05.png')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

print("Gray min:", gray.min(), "max:", gray.max(), "mean:", gray.mean())

# Let's see the 4 corners to check background color
corners = [gray[0,0], gray[0,-1], gray[-1,0], gray[-1,-1]]
print("Corners:", corners)

# Try different thresholds
for th in [30, 45, 60, 80, 100]:
    _, thresh = cv2.threshold(gray, th, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        cnt = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(cnt)
        print(f"thresh {th}: rect size {rect[1]}, area {cv2.contourArea(cnt)}")
    else:
        print(f"thresh {th}: no contours")
