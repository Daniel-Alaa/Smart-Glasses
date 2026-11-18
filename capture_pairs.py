# =============================================================================
# camera/calibration/capture_pairs.py
# One-time script: capture synchronized stereo checkerboard image pairs.
# Press S to save a pair, Q to quit.
# Saves to: camera/calibration/data/left/img_NNN.png
#           camera/calibration/data/right/img_NNN.png
# You need 30-40 pairs minimum for a good calibration.
# =============================================================================

import cv2
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import config

# Output directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LEFT_DIR   = os.path.join(SCRIPT_DIR, "data", "left")
RIGHT_DIR  = os.path.join(SCRIPT_DIR, "data", "right")
os.makedirs(LEFT_DIR,  exist_ok=True)
os.makedirs(RIGHT_DIR, exist_ok=True)

# Checkerboard inner corners (columns, rows)
BOARD = (9, 6)


def gst_pipeline(sensor_id: int) -> str:
    w, h, fps = config.CAMERA_WIDTH, config.CAMERA_HEIGHT, config.CAMERA_FPS
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){w}, height=(int){h}, "
        f"format=(string)NV12, framerate=(fraction){fps}/1 ! "
        f"nvvidconv ! "
        f"video/x-raw, width=(int){w}, height=(int){h}, format=(string)BGRx ! "
        f"videoconvert ! video/x-raw, format=(string)BGR ! "
        f"appsink max-buffers=1 drop=true sync=false"
    )


def open_cameras():
    if config.USE_GSTREAMER:
        cap_l = cv2.VideoCapture(gst_pipeline(config.LEFT_SENSOR_ID),  cv2.CAP_GSTREAMER)
        cap_r = cv2.VideoCapture(gst_pipeline(config.RIGHT_SENSOR_ID), cv2.CAP_GSTREAMER)
    else:
        cap_l = cv2.VideoCapture(config.LEFT_CAMERA_INDEX)
        cap_r = cv2.VideoCapture(config.RIGHT_CAMERA_INDEX)
        for cap in (cap_l, cap_r):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS,          config.CAMERA_FPS)

    if not cap_l.isOpened():
        print("[capture_pairs] ERROR: Left camera failed to open.")
        sys.exit(1)
    if not cap_r.isOpened():
        print("[capture_pairs] ERROR: Right camera failed to open.")
        sys.exit(1)

    return cap_l, cap_r


def next_index(directory: str) -> int:
    """Return next available image index based on existing files."""
    existing = [f for f in os.listdir(directory) if f.endswith(".png")]
    return len(existing) + 1


def main():
    cap_l, cap_r = open_cameras()
    print("[capture_pairs] Cameras opened.")
    print(f"[capture_pairs] Target: {LEFT_DIR}")
    print("[capture_pairs] Controls: S = save pair | Q = quit")
    print(f"[capture_pairs] Checkerboard: {BOARD[0]}x{BOARD[1]} inner corners")
    print("-" * 55)

    saved = 0

    while True:
        ret_l, frame_l = cap_l.read()
        ret_r, frame_r = cap_r.read()

        if not ret_l or not ret_r:
            print("[capture_pairs] WARNING: Failed to grab frames.")
            continue

        # Preview: detect corners live so you know when the board is visible
        gray_l = cv2.cvtColor(frame_l, cv2.COLOR_BGR2GRAY)
        gray_r = cv2.cvtColor(frame_r, cv2.COLOR_BGR2GRAY)
        found_l, corners_l = cv2.findChessboardCorners(gray_l, BOARD, None)
        found_r, corners_r = cv2.findChessboardCorners(gray_r, BOARD, None)

        preview_l = frame_l.copy()
        preview_r = frame_r.copy()

        if found_l:
            cv2.drawChessboardCorners(preview_l, BOARD, corners_l, found_l)
        if found_r:
            cv2.drawChessboardCorners(preview_r, BOARD, corners_r, found_r)

        # Status overlay
        status = f"Saved: {saved} | S=save Q=quit"
        both   = "BOTH DETECTED" if (found_l and found_r) else ("LEFT ONLY" if found_l else ("RIGHT ONLY" if found_r else "NOT DETECTED"))
        color  = (0, 255, 0) if (found_l and found_r) else (0, 0, 255)

        for img in (preview_l, preview_r):
            cv2.putText(img, status, (10, 25),  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(img, both,   (10, 55),  cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        combined = cv2.hconcat([preview_l, preview_r])
        cv2.imshow("Stereo Capture — Left | Right", combined)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            print(f"[capture_pairs] Quit. Total saved: {saved}")
            break

        if key == ord('s'):
            if not (found_l and found_r):
                print("[capture_pairs] SKIP — checkerboard not detected in both frames. Reposition and try again.")
                continue

            idx      = next_index(LEFT_DIR)
            filename = f"img_{idx:03d}.png"
            cv2.imwrite(os.path.join(LEFT_DIR,  filename), frame_l)
            cv2.imwrite(os.path.join(RIGHT_DIR, filename), frame_r)
            saved += 1
            print(f"[capture_pairs] Saved pair {saved}: {filename}")

            if saved == 30:
                print("[capture_pairs] 30 pairs saved — minimum reached. Keep going for better accuracy.")

    cap_l.release()
    cap_r.release()
    cv2.destroyAllWindows()

    if saved < 30:
        print(f"[capture_pairs] WARNING: Only {saved} pairs saved. 30+ recommended for good calibration.")
    else:
        print(f"[capture_pairs] Done. {saved} pairs ready for calibrate.py")


if __name__ == "__main__":
    main()
