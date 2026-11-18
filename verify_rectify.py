# =============================================================================
# camera/calibration/verify_rectify.py
# One-time visual sanity check after calibrate.py.
# Loads a stereo pair, applies rectification maps, draws horizontal lines.
# After good rectification, every feature in the left image sits on the
# SAME horizontal line as its match in the right image.
# If lines don't align → calibration failed → recapture and recalibrate.
# =============================================================================

import cv2
import numpy as np
import os
import sys
import glob

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LEFT_DIR   = os.path.join(SCRIPT_DIR, "data", "left")
RIGHT_DIR  = os.path.join(SCRIPT_DIR, "data", "right")
MAPS_FILE  = os.path.join(SCRIPT_DIR, "data", "stereo_maps.npz")

NUM_LINES  = 20   # number of horizontal epipolar lines to draw


def load_maps():
    if not os.path.exists(MAPS_FILE):
        print(f"[verify] ERROR: Maps file not found: {MAPS_FILE}")
        print("[verify] Run calibrate.py first.")
        sys.exit(1)

    data = np.load(MAPS_FILE)
    print(f"[verify] Loaded rectification maps from {MAPS_FILE}")
    return data["map1_l"], data["map2_l"], data["map1_r"], data["map2_r"]


def pick_pair():
    left_imgs  = sorted(glob.glob(os.path.join(LEFT_DIR,  "*.png")))
    right_imgs = sorted(glob.glob(os.path.join(RIGHT_DIR, "*.png")))

    if not left_imgs:
        print(f"[verify] ERROR: No images found in {LEFT_DIR}")
        print("[verify] Run capture_pairs.py first.")
        sys.exit(1)

    # Use the middle pair for a representative check
    idx    = len(left_imgs) // 2
    img_l  = cv2.imread(left_imgs[idx])
    img_r  = cv2.imread(right_imgs[idx])

    if img_l is None or img_r is None:
        print("[verify] ERROR: Could not read image pair.")
        sys.exit(1)

    print(f"[verify] Using pair: {os.path.basename(left_imgs[idx])}")
    return img_l, img_r


def draw_epipolar_lines(img_l, img_r, num_lines=NUM_LINES):
    """Draw evenly spaced horizontal lines across both images."""
    h = img_l.shape[0]
    step = h // (num_lines + 1)
    combined = cv2.hconcat([img_l, img_r])

    for i in range(1, num_lines + 1):
        y = i * step
        cv2.line(combined, (0, y), (combined.shape[1], y), (0, 255, 0), 1)

    return combined


def main():
    map1_l, map2_l, map1_r, map2_r = load_maps()
    img_l, img_r = pick_pair()

    # Rectify
    rect_l = cv2.remap(img_l, map1_l, map2_l, cv2.INTER_LINEAR)
    rect_r = cv2.remap(img_r, map1_r, map2_r, cv2.INTER_LINEAR)

    # Draw lines on both raw and rectified for comparison
    raw_view  = draw_epipolar_lines(img_l.copy(),  img_r.copy())
    rect_view = draw_epipolar_lines(rect_l.copy(), rect_r.copy())

    # Labels
    for view, label in [(raw_view, "RAW (before rectify)"),
                        (rect_view, "RECTIFIED (after rectify)")]:
        cv2.putText(view, label, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    print("\n[verify] ── What to look for ──────────────────────────────────")
    print("[verify] PASS: Features in left and right sit on the SAME green line.")
    print("[verify] FAIL: Features are on different lines → recapture + recalibrate.")
    print("[verify] Press any key to toggle Raw ↔ Rectified. Press Q to quit.")
    print("─" * 60)

    views   = [raw_view, rect_view]
    titles  = ["RAW — before rectify", "RECTIFIED — after rectify"]
    current = 1   # start on rectified

    while True:
        cv2.imshow("Rectification Verify", views[current])
        key = cv2.waitKey(0) & 0xFF
        if key == ord('q'):
            break
        else:
            current = 1 - current   # toggle

    cv2.destroyAllWindows()
    print("[verify] Done.")


if __name__ == "__main__":
    main()
