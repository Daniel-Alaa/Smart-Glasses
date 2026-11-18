# =============================================================================
# vision/depth.py
# Responsibility: Convert a rectified stereo pair into a per-pixel depth map
#                 in real-world metres.
# Interface: estimate_depth(left, right) → np.ndarray (float32, metres)
# =============================================================================

import cv2
import numpy as np
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


# ---------------------------------------------------------------------------
# Load calibration — build rectification maps once at import time
# ---------------------------------------------------------------------------

def _load_calibration() -> dict:
    """
    Load stereo calibration from the .npz file produced by stereo_calibrate.py.
    Falls back to identity matrices (no distortion, parallel cameras) so the
    rest of the pipeline keeps running during development on a laptop.
    """
    npz_path = config.CALIB_FILE_NPZ

    if os.path.exists(npz_path):
        data = np.load(npz_path)
        print(f"[depth] Calibration loaded from {npz_path}")
        return {
            "K_L": data["K_L"], "D_L": data["D_L"],
            "K_R": data["K_R"], "D_R": data["D_R"],
            "R":   data["R"],   "T":   data["T"],
        }

    # ── Fallback: approximate values for IMX219 at 640×480 ─────────────────
    print("[depth] WARNING: calibration file not found — using approximate "
          "identity matrices.  Run camera/calibration/stereo_calibrate.py "
          "before deploying on Jetson.")
    f  = config.FOCAL_LENGTH_PX
    cx = config.CAMERA_WIDTH  / 2.0
    cy = config.CAMERA_HEIGHT / 2.0
    K  = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1]], dtype=np.float64)
    return {
        "K_L": K.copy(),  "D_L": np.zeros((5, 1)),
        "K_R": K.copy(),  "D_R": np.zeros((5, 1)),
        "R":   np.eye(3), "T":   np.array([-config.STEREO_BASELINE_M, 0, 0]),
    }


def _build_rectify_maps(calib: dict) -> tuple:
    """Compute undistort+rectify maps for both cameras (done once)."""
    size = (config.CAMERA_WIDTH, config.CAMERA_HEIGHT)
    R_L, R_R, P_L, P_R, Q, _, _ = cv2.stereoRectify(
        calib["K_L"], calib["D_L"],
        calib["K_R"], calib["D_R"],
        size, calib["R"], calib["T"],
        flags=cv2.CALIB_ZERO_DISPARITY, alpha=0
    )
    map_L1, map_L2 = cv2.initUndistortRectifyMap(
        calib["K_L"], calib["D_L"], R_L, P_L, size, cv2.CV_16SC2
    )
    map_R1, map_R2 = cv2.initUndistortRectifyMap(
        calib["K_R"], calib["D_R"], R_R, P_R, size, cv2.CV_16SC2
    )
    return map_L1, map_L2, map_R1, map_R2


def _build_matcher():
    """Create StereoSGBM and optional WLS filter."""
    bs = config.STEREO_BLOCK_SIZE
    matcher = cv2.StereoSGBM_create(
        minDisparity      = config.STEREO_MIN_DISP,
        numDisparities    = config.STEREO_NUM_DISP,
        blockSize         = bs,
        P1                = 8  * 3 * bs ** 2,
        P2                = 32 * 3 * bs ** 2,
        disp12MaxDiff     = 1,
        uniquenessRatio   = 10,
        speckleWindowSize = 100,
        speckleRange      = 32,
        preFilterCap      = 63,
        mode              = cv2.STEREO_SGBM_MODE_SGBM_3WAY,
    )

    wls = None
    if config.STEREO_USE_WLS:
        try:
            right_matcher = cv2.ximgproc.createRightMatcher(matcher)
            wls = cv2.ximgproc.createDisparityWLSFilter(matcher)
            wls.setLambda(config.STEREO_WLS_LAMBDA)
            wls.setSigmaColor(config.STEREO_WLS_SIGMA)
            return matcher, right_matcher, wls
        except AttributeError:
            print("[depth] WARNING: opencv-contrib not installed — "
                  "WLS filter disabled.  Install opencv-contrib-python.")

    return matcher, None, None


# ── Module-level initialisation ─────────────────────────────────────────────
_calib                       = _load_calibration()
_map_L1, _map_L2, _map_R1, _map_R2 = _build_rectify_maps(_calib)
_matcher, _right_matcher, _wls      = _build_matcher()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rectify(left: np.ndarray, right: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Apply undistortion + stereo rectification to a raw frame pair.
    Returns (left_rect, right_rect) — both uint8 BGR.
    This is exposed separately so object_detection can run on the rectified
    left frame without recomputing it.
    """
    left_rect  = cv2.remap(left,  _map_L1, _map_L2, cv2.INTER_LINEAR)
    right_rect = cv2.remap(right, _map_R1, _map_R2, cv2.INTER_LINEAR)
    return left_rect, right_rect


def estimate_depth(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """
    Compute a per-pixel depth map in metres from a raw stereo frame pair.

    Args:
        left:  Raw left  camera frame (BGR uint8).
        right: Raw right camera frame (BGR uint8).

    Returns:
        depth_map: float32 numpy array, same H×W as input frames.
                   Pixel value = depth in metres.
                   0.0 means depth is unknown / unreliable for that pixel.
    """
    left_rect, right_rect = rectify(left, right)

    gray_L = cv2.cvtColor(left_rect,  cv2.COLOR_BGR2GRAY)
    gray_R = cv2.cvtColor(right_rect, cv2.COLOR_BGR2GRAY)

    if _wls is not None and _right_matcher is not None:
        # WLS-filtered path — smoother, preferred for deployment
        disp_L = _matcher.compute(gray_L, gray_R).astype(np.float32) / 16.0
        disp_R = _right_matcher.compute(gray_R, gray_L).astype(np.float32) / 16.0
        disp   = _wls.filter(disp_L, gray_L, disparity_map_right=disp_R)
    else:
        # Plain SGBM — used when opencv-contrib is absent
        disp = _matcher.compute(gray_L, gray_R).astype(np.float32) / 16.0

    # depth (m) = focal_length (px) × baseline (m) / disparity (px)
    with np.errstate(divide="ignore", invalid="ignore"):
        depth = np.where(
            disp > 0,
            (config.FOCAL_LENGTH_PX * config.STEREO_BASELINE_M) / disp,
            0.0,
        ).astype(np.float32)

    return depth


def sample_box_depth(depth_map: np.ndarray, x1: int, y1: int,
                     x2: int, y2: int) -> float | None:
    """
    Return a robust depth estimate (metres) for a bounding box region.
    Uses the configured percentile to suppress noisy background pixels.

    Returns None if there are too few valid pixels to trust the reading.
    """
    h, w = depth_map.shape[:2]
    x1, y1 = max(x1, 0), max(y1, 0)
    x2, y2 = min(x2, w - 1), min(y2, h - 1)

    roi   = depth_map[y1:y2, x1:x2]
    valid = roi[(roi >= config.DEPTH_MIN_M) & (roi <= config.DEPTH_MAX_M)]

    if valid.size < config.DEPTH_MIN_VALID_PIXELS:
        return None

    return float(np.percentile(valid, config.DEPTH_SAMPLE_PERCENTILE))