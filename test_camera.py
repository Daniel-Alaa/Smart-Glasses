from camera.capture import get_frames
 
def test_camera():
    left, right = get_frames()
    assert left is not None, "Left camera failed"
    assert right is not None, "Right camera failed"
    print("Camera test passed.")
 
if __name__ == "__main__":
    test_camera()
