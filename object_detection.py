# =============================================================================
# vision/object_detection.py
# Responsibility: Run YOLO detection on a single frame and return a list of
#                 plain-English label strings for objects that are close.
# Interface (FIXED — do not change signature):
#   detect_objects(frame: np.ndarray) -> list[str]
# =============================================================================
# Stair detection is merged here because:
#   • It uses the same YOLO inference pass (no extra model call).
#   • It naturally produces direction-aware labels ("stairs_up", "stairs_down")
#     which are passed straight through detect_objects → decision/logic.py.
#   • stair_detection.py then wraps detect_objects to honour its own contract.
# =============================================================================

import numpy as np
import os
import sys
from ultralytics import YOLO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
from vision.depth import sample_box_depth

# ---------------------------------------------------------------------------
# Load models once at import time
# ---------------------------------------------------------------------------
# Delay import errors until runtime so the rest of the codebase can be tested
# without models present.

def _load_model(path: str, label: str) -> YOLO | None:
    if not os.path.exists(path):
        print(f"[object_detection] WARNING: {label} model not found at {path}. "
              f"Detection will be skipped until the file is present.")
        return None
    model = YOLO(path)
    print(f"[object_detection] {label} model loaded from {path}")
    return model

_coco_model   = _load_model(config.COCO_MODEL_PATH,   "COCO")
_custom_model = _load_model(config.CUSTOM_MODEL_PATH, "Custom")


# ---------------------------------------------------------------------------
# Label classification helpers
# ---------------------------------------------------------------------------

def _classify(label: str) -> str:
    l = label.lower().strip()

    if l == "door" or l.startswith("door_") or l.endswith("_door"):
        return "door"

    if any(kw in l for kw in config.ELEVATOR_KEYWORDS):
        return "elevator"

    if l == "0":
        return "stair_up"
    if l == "1":
        return "stair_down"

    if any(kw in l for kw in config.STAIR_KEYWORDS):
        if "up"   in l: return "stair_up"
        if "down" in l: return "stair_down"
        return "stair"

    return "object"


# ---------------------------------------------------------------------------
# Internal per-box processor
# ---------------------------------------------------------------------------

def _process_box(box, names: dict, depth_map: np.ndarray | None,
                 min_conf: float) -> str | None:
    """
    Evaluate a single YOLO box.  Returns a label string if the object is
    close enough and confident enough, otherwise None.

    Label format:
      • Landmarks : "door" | "elevator" | "stair_up" | "stair_down" | "stair"
      • COCO objs : raw class name e.g. "person", "chair"
    """
    conf  = float(box.conf.item())
    label = names[int(box.cls.item())]
    kind  = _classify(label)

    # Confidence gate — landmarks need a higher bar
    required_conf = (config.LANDMARK_CONF_THRESHOLD
                     if kind != "object"
                     else config.YOLO_CONF_THRESHOLD)
    if conf < required_conf:
        return None

    # Proximity gate — use real depth when available, skip gate if not
    if depth_map is not None:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        depth = sample_box_depth(depth_map, x1, y1, x2, y2)
        if depth is not None and depth > config.CLOSE_THRESHOLD_M:
            return None          # object is present but not close
        # depth is None → stereo unreliable → allow the label through
        #                  so at least the user is warned

    # Return the canonical label
    return kind if kind != "object" else label


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_objects(frame: np.ndarray,
                   depth_map: np.ndarray | None = None) -> list[str]:
    """
    Run object detection on a single BGR frame and return the labels of
    objects that are within the configured CLOSE_THRESHOLD_M.

    Args:
        frame:     BGR uint8 numpy array (from camera/capture.py or rectified).
        depth_map: float32 depth map in metres from vision/depth.py.
                   Pass None during laptop development — proximity will not
                   be filtered by real depth (all detected objects are returned).

    Returns:
        List of label strings, may be empty.
        Possible values: "door", "elevator", "stair_up", "stair_down", "stair",
                         plus any COCO class name in config.ALLOWED_COCO_CLASSES.

    This function is stateless — frame counters and cooldowns live in
    decision/logic.py, not here.
    """
    results: list[str] = []

    # ── Custom model (doors, elevators, stairs, fire extinguisher…) ─────────
    if _custom_model is not None:
        custom_result = _custom_model(frame, conf=config.YOLO_CONF_THRESHOLD,
                                      verbose=False)[0]
        for box in custom_result.boxes:
            label = _process_box(box, custom_result.names, depth_map,
                                 config.YOLO_CONF_THRESHOLD)
            if label is not None:
                results.append(label)

    # ── COCO model (people, chairs, vehicles…) ───────────────────────────────
    if _coco_model is not None:
        coco_result = _coco_model(frame, conf=config.YOLO_CONF_THRESHOLD,
                                  verbose=False)[0]
        for box in coco_result.boxes:
            raw_label = coco_result.names[int(box.cls.item())]
            if raw_label not in config.ALLOWED_COCO_CLASSES:
                continue
            label = _process_box(box, coco_result.names, depth_map,
                                 config.YOLO_CONF_THRESHOLD)
            if label is not None:
                results.append(label)

    return results