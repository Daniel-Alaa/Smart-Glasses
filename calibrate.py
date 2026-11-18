# camera/calibration/calibrate.py
# Stereo calibration — AUTO-CAPTURE mode.
# Captures pairs automatically when the board is detected and held still.
# No need to press SPACE or Q — just hold the board and move it around.
#
# Usage:
#   python camera/calibration/calibrate.py
#
# Controls:
#   ESC = quit without calibrating
#   Q   = stop early and run calibration with pairs collected so far
#
# Workflow:
#   1. Run the script — two camera windows open side by side.
#   2. Hold the checkerboard in front of both cameras.
#   3. When both cameras detect the board, a green progress bar fills up.
#   4. Hold still for 1.5 seconds — auto-captures the pair.
#   5. Move to a new position/angle and repeat.
#   6. After 20 pairs, calibration runs automatically.

import cv2
import numpy as np
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import config

# ─── Checkerboard setup ──────────────────────────────────────────────────────
INNER_COLS = config.CHECKERBOARD_COLS   # 8 inner corner columns
INNER_ROWS = config.CHECKERBOARD_ROWS   # 6 inner corner rows
SQUARE_MM  = config.SQUARE_SIZE_MM      # 35.0 mm

TARGET_PAIRS   = 20      # auto-stop after this many pairs
STABLE_SECONDS = 1.5     # seconds board must be held still before auto-capture
MIN_MOVE_PX    = 10      # pixels corners must move to reset stability timer

CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-6)

# 3-D object points (Z=0 flat board), units = mm
objp = np.zeros((INNER_ROWS * INNER_COLS, 3), np.float32)
objp[:, :2] = np.mgrid[0:INNER_COLS, 0:INNER_ROWS].T.reshape(-1, 2) * SQUARE_MM

# ─── Storage ─────────────────────────────────────────────────────────────────
obj_points   = []
img_points_l = []
img_points_r = []

SAVE_DIR = os.path.join(os.path.dirname(__file__), "captured_pairs")
os.makedirs(SAVE_DIR, exist_ok=True)

# ─── Coverage tracking ───────────────────────────────────────────────────────
_coverage_cells = set()
GRID_COLS = 4
GRID_ROWS = 3


def _update_coverage(corners, img_w, img_h):
    for pt in corners.reshape(-1, 2):
        cx = int(pt[0] / img_w * GRID_COLS)
        cy = int(pt[1] / img_h * GRID_ROWS)
        _coverage_cells.add((min(cx, GRID_COLS - 1), min(cy, GRID_ROWS - 1)))


def _coverage_pct():
    return len(_coverage_cells) / (GRID_COLS * GRID_ROWS) * 100


# ─── GStreamer pipeline ───────────────────────────────────────────────────────

def _gst_pipeline(sensor_id):
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=1280, height=720, "
        f"format=NV12, framerate=30/1 ! "
        f"nvvidconv ! "
        f"video/x-raw, width={config.CAMERA_WIDTH}, "
        f"height={config.CAMERA_HEIGHT}, format=BGRx ! "
        f"videoconvert ! "
        f"video/x-raw, format=BGR ! "
        f"appsink drop=1"
    )


def open_cameras():
    def _gst_pipeline(sensor_id):
        return (
            f"nvarguscamerasrc sensor-id={sensor_id} ! "
            f"video/x-raw(memory:NVMM), width=1280, height=720, "
            f"format=NV12, framerate=30/1 ! "
            f"nvvidconv ! "
            f"video/x-raw, width=640, height=480, format=BGRx ! "
            f"videoconvert ! "
            f"video/x-raw, format=BGR ! "
            f"appsink drop=1 max-buffers=1 sync=false"
        )

    print("[CAMERA] Opening left camera (sensor-id=0)...")
    cap_l = cv2.VideoCapture(_gst_pipeline(config.LEFT_SENSOR_ID), cv2.CAP_GSTREAMER)
    print(f"[CAMERA] Left opened: {cap_l.isOpened()}")

    print("[CAMERA] Opening right camera (sensor-id=1)...")
    cap_r = cv2.VideoCapture(_gst_pipeline(config.RIGHT_SENSOR_ID), cv2.CAP_GSTREAMER)
    print(f"[CAMERA] Right opened: {cap_r.isOpened()}")

    return cap_l, cap_r


# ─── Corner detection ────────────────────────────────────────────────────────

def find_corners(gray):
    found, corners = cv2.findChessboardCorners(
        gray,
        (INNER_COLS, INNER_ROWS),
        cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
    )
    if found:
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), CRITERIA)
    return found, corners


def _corners_moved(prev, curr):
    if prev is None or curr is None:
        return True
    diff = np.linalg.norm(prev - curr, axis=2).mean()
    return diff > MIN_MOVE_PX


# ─── HUD drawing ─────────────────────────────────────────────────────────────

def _draw_hud(img, label, found, pair_count, coverage, stable_pct):
    h, w = img.shape[:2]
    out = img.copy()

    # Top bar
    cv2.rectangle(out, (0, 0), (w, 52), (20, 20, 20), -1)
    cv2.putText(out, label, (8, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2)

    # Board detection indicator
    color = (0, 220, 0) if found else (0, 0, 220)
    text  = "BOARD FOUND" if found else "NO BOARD"
    cv2.circle(out, (w - 185, 26), 11, color, -1)
    cv2.putText(out, text, (w - 165, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

    # Stability progress bar
    if stable_pct > 0:
        bar_w = int((w - 20) * stable_pct)
        cv2.rectangle(out, (10, 54), (w - 10, 62), (60, 60, 60), -1)
        cv2.rectangle(out, (10, 54), (10 + bar_w, 62), (0, 220, 0), -1)

    # Bottom bar
    cv2.rectangle(out, (0, h - 48), (w, h), (20, 20, 20), -1)
    cv2.putText(out, f"Pairs: {pair_count}/{TARGET_PAIRS}  Coverage: {coverage:.0f}%",
                (8, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 0), 2)
    cv2.putText(out, "Q=Calibrate now  ESC=Quit",
                (w - 310, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1)

    return out


def _draw_coverage_grid(img):
    h, w = img.shape[:2]
    cell_w = w // GRID_COLS
    cell_h = (h - 110) // GRID_ROWS
    for col in range(GRID_COLS):
        for row in range(GRID_ROWS):
            x0 = col * cell_w + 2
            y0 = 65 + row * cell_h
            x1 = x0 + cell_w - 4
            y1 = y0 + cell_h - 4
            if (col, row) in _coverage_cells:
                cv2.rectangle(img, (x0, y0), (x1, y1), (0, 100, 0), 2)
            else:
                cv2.rectangle(img, (x0, y0), (x1, y1), (50, 50, 50), 1)


# ─── Calibration ─────────────────────────────────────────────────────────────

def run_calibration(img_size):
    print("\n[CALIBRATION] Running stereoCalibrate — please wait...")

    _, K1, D1, _, _ = cv2.calibrateCamera(
        obj_points, img_points_l, img_size, None, None)
    _, K2, D2, _, _ = cv2.calibrateCamera(
        obj_points, img_points_r, img_size, None, None)

    flags = cv2.CALIB_FIX_INTRINSIC
    ret, K1, D1, K2, D2, R, T, E, F = cv2.stereoCalibrate(
        obj_points, img_points_l, img_points_r,
        K1, D1, K2, D2,
        img_size, criteria=CRITERIA, flags=flags
    )

    print(f"[CALIBRATION] RMS reprojection error: {ret:.4f} px")
    if ret < 0.5:
        print("  Excellent calibration!")
    elif ret < 1.0:
        print("  Good calibration (acceptable).")
    else:
        print("  RMS > 1.0 — consider recapturing with more varied poses.")

    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(
        K1, D1, K2, D2, img_size, R, T,
        flags=cv2.CALIB_ZERO_DISPARITY, alpha=0
    )

    out_path = os.path.join(os.path.dirname(__file__), "stereo_calib.npz")
    np.savez(
        out_path,
        K1=K1, D1=D1, K2=K2, D2=D2,
        R=R, T=T, E=E, F=F,
        R1=R1, R2=R2, P1=P1, P2=P2, Q=Q,
        img_size=np.array(img_size),
        rms=ret
    )
    print(f"[CALIBRATION] Saved → {out_path}")
    print(f"  Focal length (left) : {P1[0, 0]:.1f} px")
    print(f"  Baseline            : {np.linalg.norm(T):.1f} mm")
    return out_path


# ─── Main loop ───────────────────────────────────────────────────────────────

def main():
    cap_l, cap_r = open_cameras()
    if not cap_l.isOpened() or not cap_r.isOpened():
        print("[FATAL] Could not open one or both cameras. Exiting.")
        return

    pair_count     = 0
    img_size       = None
    stable_since   = time.time()
    prev_corners_l = None
    blocked        = False   # True right after a capture, until board moves

    cv2.namedWindow("Left Camera",  cv2.WINDOW_NORMAL)
    cv2.namedWindow("Right Camera", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Left Camera",  640, 480)
    cv2.resizeWindow("Right Camera", 640, 480)
    cv2.moveWindow("Left Camera",    0,  50)
    cv2.moveWindow("Right Camera", 660,  50)

    print("=" * 60)
    print("STEREO CALIBRATION — AUTO-CAPTURE MODE")
    print(f"  Board  : {INNER_COLS+1} x {INNER_ROWS+1} squares "
          f"({INNER_COLS} x {INNER_ROWS} inner corners)")
    print(f"  Square : {SQUARE_MM} mm")
    print(f"  Target : {TARGET_PAIRS} pairs")
    print("-" * 60)
    print("  Hold board still in front of BOTH cameras.")
    print("  Green bar fills — auto-captures after 1.5 seconds.")
    print("  Move board to a new angle after each capture.")
    print("  Q = calibrate now  |  ESC = quit")
    print("=" * 60)

    while True:
        ret_l, frame_l = cap_l.read()
        ret_r, frame_r = cap_r.read()
        if not ret_l or not ret_r:
            print("[ERROR] Camera read failed.")
            break

        gray_l = cv2.cvtColor(frame_l, cv2.COLOR_BGR2GRAY)
        gray_r = cv2.cvtColor(frame_r, cv2.COLOR_BGR2GRAY)

        found_l, corners_l = find_corners(gray_l)
        found_r, corners_r = find_corners(gray_r)

        both_found = found_l and found_r
        now        = time.time()
        stable_pct = 0.0

        if both_found:
            moved = _corners_moved(prev_corners_l, corners_l)

            if moved:
                stable_since = now
                blocked      = False   # board moved — unblock next capture

            prev_corners_l = corners_l.copy()

            if not blocked:
                elapsed    = now - stable_since
                stable_pct = min(elapsed / STABLE_SECONDS, 1.0)

                if elapsed >= STABLE_SECONDS:
                    # ── AUTO CAPTURE ──
                    if img_size is None:
                        img_size = (gray_l.shape[1], gray_l.shape[0])

                    obj_points.append(objp)
                    img_points_l.append(corners_l)
                    img_points_r.append(corners_r)
                    _update_coverage(corners_l, gray_l.shape[1], gray_l.shape[0])

                    pair_count += 1
                    cv2.imwrite(
                        os.path.join(SAVE_DIR, f"left_{pair_count:03d}.jpg"), frame_l)
                    cv2.imwrite(
                        os.path.join(SAVE_DIR, f"right_{pair_count:03d}.jpg"), frame_r)

                    print(f"[CAPTURED] Pair #{pair_count}  "
                          f"coverage: {_coverage_pct():.0f}%  "
                          f"— move board to new position")

                    # White flash confirmation
                    flash = np.ones_like(frame_l) * 255
                    cv2.imshow("Left Camera",  flash)
                    cv2.imshow("Right Camera", flash)
                    cv2.waitKey(150)

                    blocked = True   # block until board moves away

                    if pair_count >= TARGET_PAIRS:
                        print(f"\n[DONE] {TARGET_PAIRS} pairs collected.")
                        break
        else:
            stable_since   = now
            prev_corners_l = None

        # ── Draw ──
        cov    = _coverage_pct()
        disp_l = frame_l.copy()
        disp_r = frame_r.copy()

        if found_l:
            cv2.drawChessboardCorners(
                disp_l, (INNER_COLS, INNER_ROWS), corners_l, found_l)
        if found_r:
            cv2.drawChessboardCorners(
                disp_r, (INNER_COLS, INNER_ROWS), corners_r, found_r)

        _draw_coverage_grid(disp_l)
        _draw_coverage_grid(disp_r)

        sp = stable_pct if (both_found and not blocked) else 0.0
        disp_l = _draw_hud(disp_l, "LEFT",  found_l, pair_count, cov, sp)
        disp_r = _draw_hud(disp_r, "RIGHT", found_r, pair_count, cov, sp)

        if both_found:
            h, w = disp_l.shape[:2]
            border_color = (0, 220, 0) if not blocked else (0, 165, 255)
            for d in (disp_l, disp_r):
                cv2.rectangle(d, (0, 0), (w - 1, h - 1), border_color, 6)

        cv2.imshow("Left Camera",  disp_l)
        cv2.imshow("Right Camera", disp_r)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            print("\n[QUIT] Exiting without calibration.")
            cap_l.release()
            cap_r.release()
            cv2.destroyAllWindows()
            return
        elif key in (ord('q'), ord('Q')):
            print(f"\n[EARLY STOP] {pair_count} pairs. Running calibration...")
            break

    cap_l.release()
    cap_r.release()
    cv2.destroyAllWindows()

    if pair_count < 10:
        print(f"\n  Only {pair_count} pairs — need at least 10.")
    if pair_count > 0:
        run_calibration(img_size)
    else:
        print("[ERROR] No pairs captured — calibration aborted.")


if __name__ == "__main__":
    main()
