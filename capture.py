# =============================================================================
# camera/capture.py
# Responsibility: Open stereo cameras and deliver (left, right) frame pairs.
# Interface: get_frames() -> tuple[np.ndarray, np.ndarray] | None
# =============================================================================

import cv2
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


# ---------------------------------------------------------------------------
# GStreamer pipeline builder — tested on Jetson Orin Nano + IMX219
# ---------------------------------------------------------------------------

def _gst_pipeline(sensor_id: int) -> str:
    """
    Build a GStreamer pipeline string for a single IMX219 on Jetson Orin Nano.
    Uses nvarguscamerasrc → nvvidconv → BGR for OpenCV compatibility.
    max-buffers=1 drop=true prevents buffer buildup causing lag.
    """
    w, h, fps = config.CAMERA_WIDTH, config.CAMERA_HEIGHT, config.CAMERA_FPS
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){w}, height=(int){h}, "
        f"format=(string)NV12, framerate=(fraction){fps}/1 ! "
        f"nvvidconv ! "
        f"video/x-raw, width=(int){w}, height=(int){h}, format=(string)BGRx ! "
        f"videoconvert ! "
        f"video/x-raw, format=(string)BGR ! "
        f"appsink max-buffers=1 drop=true sync=false"
    )


# ---------------------------------------------------------------------------
# Module-level camera handles
# ---------------------------------------------------------------------------

_cap_left  = None
_cap_right = None


def open_cameras() -> bool:
    """
    Open both cameras. Call once at startup before any get_frames() call.
    Returns True on success, False if either camera fails to open.
    """
    global _cap_left, _cap_right

    if config.USE_GSTREAMER:
        # ── Jetson path (IMX219 dual stereo) ──────────────────────────────
        print("[capture] Opening cameras via GStreamer (Jetson mode)...")

        _cap_left = cv2.VideoCapture(
            _gst_pipeline(config.LEFT_SENSOR_ID), cv2.CAP_GSTREAMER
        )
        _cap_right = cv2.VideoCapture(
            _gst_pipeline(config.RIGHT_SENSOR_ID), cv2.CAP_GSTREAMER
        )

        if not _cap_left.isOpened():
            print("[capture] ERROR: Left camera (sensor_id=0) failed to open.")
            print("[capture] TIP: Run 'sudo systemctl restart nvargus-daemon' and try again.")
            return False

        if not _cap_right.isOpened():
            print("[capture] ERROR: Right camera (sensor_id=1) failed to open.")
            print("[capture] TIP: Check ribbon cable and run 'sudo systemctl restart nvargus-daemon'")
            return False

    else:
        # ── Laptop / development path ──────────────────────────────────────
        print("[capture] Opening cameras via OpenCV (laptop mode)...")
        idx = config.LAPTOP_CAM_INDEX
        _cap_left  = cv2.VideoCapture(idx)
        _cap_right = cv2.VideoCapture(idx)

        for cap in (_cap_left, _cap_right):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS,          config.CAMERA_FPS)

        if not _cap_left.isOpened() or not _cap_right.isOpened():
            print(f"[capture] ERROR: Could not open webcam at index {idx}.")
            return False

    print(f"[capture] Cameras open "
          f"({'GStreamer/Jetson' if config.USE_GSTREAMER else 'OpenCV/laptop'})")
    return True


def get_frames():
    """
    Capture one (left, right) BGR frame pair.

    Returns:
        (left_frame, right_frame) as uint8 numpy arrays, or None on failure.
        Frames are raw — rectification happens in vision/depth.py.
    """
    if _cap_left is None or _cap_right is None:
        raise RuntimeError("open_cameras() must be called before get_frames().")

    ret_l, frame_l = _cap_left.read()
    ret_r, frame_r = _cap_right.read()

    if not ret_l or frame_l is None:
        print("[capture] WARNING: failed to read LEFT frame.")
        return None

    if not ret_r or frame_r is None:
        print("[capture] WARNING: failed to read RIGHT frame.")
        return None

    return frame_l, frame_r


def release_cameras() -> None:
    """Release both camera handles. Call at shutdown."""
    global _cap_left, _cap_right
    if _cap_left  is not None: _cap_left.release()
    if _cap_right is not None: _cap_right.release()
    _cap_left = _cap_right = None
    print("[capture] Cameras released.")