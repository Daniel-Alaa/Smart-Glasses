import cv2
import numpy as np
from vision.ocr import read_text

# Test 1: blank frame — should return None
frame = np.zeros((480, 640, 3), dtype="uint8")
result = read_text(frame)
print("Blank frame:", result)
assert result is None, "Expected None for blank frame"

# Test 2: real webcam frame
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()
if ret:
    result = read_text(frame)
    print("Webcam frame result:", result)
else:
    print("Could not open webcam")

print("All tests passed.")