import cv2
from vision.object_detection import detect_objects
 
def test_detection():
    frame = cv2.imread("assets/sample_images/obstacle.jpg")
    assert frame is not None, "Sample image not found"
    result = detect_objects(frame)
    assert isinstance(result, list), "Output should be a list"
    print(f"Detected: {result}")
 
if __name__ == "__main__":
    test_detection()
