# =============================================================================
# config.py — Single source of truth for all tunable parameters
# Smart Glasses | Mechatronics Engineering Project
# =============================================================================
# RULE: No thresholds or paths live anywhere else in the codebase.
#       Every module imports what it needs from here.
# =============================================================================

import os
# -----------------------------------------------------------------------------
# CALIBRATION — CHECKERBOARD
# -----------------------------------------------------------------------------
CHECKERBOARD_COLS  = 8       # inner corners (9 squares wide  → 8 inner col corners)
CHECKERBOARD_ROWS  = 6       # inner corners (7 squares tall  → 6 inner row corners)
SQUARE_SIZE_MM     = 35.0    # ← MEASURE YOUR ACTUAL PRINTED SQUARES WITH A RULER

# -----------------------------------------------------------------------------
# HARDWARE — CAMERAS
# -----------------------------------------------------------------------------
# GStreamer sensor IDs for the dual IMX219 on Jetson Orin Nano
LEFT_SENSOR_ID  = 0
RIGHT_SENSOR_ID = 1

# Resolution and framerate sent to nvarguscamerasrc
CAMERA_WIDTH  = 640
CAMERA_HEIGHT = 480
CAMERA_FPS    = 60

# Set to True on Jetson (GStreamer/nvarguscamerasrc),
# False on laptop (plain cv2.VideoCapture index)
USE_GSTREAMER = os.environ.get("USE_GSTREAMER", "0") == "1"

# Laptop fallback camera indices (used when USE_GSTREAMER=0)
LEFT_CAMERA_INDEX  = 0
RIGHT_CAMERA_INDEX = 1
LAPTOP_CAM_INDEX   = 0 

# -----------------------------------------------------------------------------
# STEREO DEPTH
# -----------------------------------------------------------------------------
# Physical distance between the two IMX219 lenses in metres
# Waveshare IMX219-83 stereo hat = 65 mm
STEREO_BASELINE_M = 0.0609

# Focal length in pixels — replace with value from stereo calibration
FOCAL_LENGTH_PX = 978.0

# Depth validity range: discard values outside [MIN, MAX] metres
DEPTH_MIN_M = 0.1
DEPTH_MAX_M = 20.0

# Percentile used when sampling depth inside a bounding box
# 25th percentile is robust against noisy background pixels
DEPTH_SAMPLE_PERCENTILE = 25

# Minimum number of valid pixels required inside a bbox to trust the reading
DEPTH_MIN_VALID_PIXELS = 10

# StereoSGBM parameters
STEREO_MIN_DISP   = 0
STEREO_NUM_DISP   = 96   # must be divisible by 16
STEREO_BLOCK_SIZE = 7

# WLS filter — set to True for smoother depth at cost of ~5 ms
STEREO_USE_WLS    = True
STEREO_WLS_LAMBDA = 8000
STEREO_WLS_SIGMA  = 1.5

# Calibration matrix files (output of stereo_calibrate.py)
CALIB_DIR      = os.path.join(os.path.dirname(__file__), "camera", "calibration")
CALIB_FILE_NPZ = os.path.join(CALIB_DIR, "stereo_calib.npz")

# -----------------------------------------------------------------------------
# OBJECT DETECTION
# -----------------------------------------------------------------------------
# Path to YOLOv8 COCO model (nano)
COCO_MODEL_PATH   = os.path.join(os.path.dirname(__file__), "models", "yolov8n.pt")

# Path to your custom-trained model (doors, elevators, stairs, fire extinguisher…)
CUSTOM_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "best.pt")

# Minimum YOLO confidence to consider any detection
YOLO_CONF_THRESHOLD      = 0.40
DETECTION_CONFIDENCE     = 0.50   # used by navigation_system detection calls
STAIR_CONFIDENCE         = 0.60

# Higher confidence required for special landmarks (door / elevator / stairs)
LANDMARK_CONF_THRESHOLD  = 0.75

# COCO class names that are relevant to a visually-impaired user
ALLOWED_COCO_CLASSES = {"person", "chair", "bench", "potted plant",
                        "fire hydrant", "stop sign", "bicycle", "motorcycle",
                        "car", "bus", "truck", "traffic light"}

# Custom model label keywords for each landmark type
DDOOR_KEYWORDS     = ["door", "door_video"]
ELEVATOR_KEYWORDS = ["elevator"]
STAIR_KEYWORDS    = ["0", "1"]  # 0=stair_up, 1=stair_down in your dataset

# Distance threshold in metres — below this the object is announced as "close"
CLOSE_THRESHOLD_M = 0.5

# How many consecutive frames a landmark must appear before being announced
LANDMARK_CONFIRM_FRAMES = 5

# -----------------------------------------------------------------------------
# DECISION / LOGIC
# -----------------------------------------------------------------------------
# Per-label announcement cooldowns in seconds
COOLDOWN_DOOR_S     = 4.0
COOLDOWN_ELEVATOR_S = 4.0
COOLDOWN_STAIR_S    = 4.0
COOLDOWN_OBJECT_S   = 7.0

# Decision priority order (lower index = higher priority)
PRIORITY_ORDER = ["stairs", "obstacle", "navigation", "text"]

# -----------------------------------------------------------------------------
# NAVIGATION
# -----------------------------------------------------------------------------
NAVIGATION_SYSTEM_PATH = "navigation_system/"
STRAIGHT_TOLERANCE_DEG = 20
IMU_MOCK_HEADING       = 0.0
DEFAULT_STEP_DISTANCE  = 5      # metres per route segment

# -----------------------------------------------------------------------------
# AUDIO / TTS
# -----------------------------------------------------------------------------
# espeak-ng voice and speed
TTS_VOICE   = "en+f3"
TTS_SPEED   = 130       # words per minute (aligns both configs)
TTS_RATE    = 130       # alias used by navigation_system modules
TTS_MAX_QUEUE = 3       # max messages waiting in queue before dropping

AUDIO_VOLUME = 100      # percentage

# -----------------------------------------------------------------------------
# MODES
# -----------------------------------------------------------------------------
MODES = ["navigation", "reading", "awareness"]

# -----------------------------------------------------------------------------
# OCR
# -----------------------------------------------------------------------------
OCR_BLUR_KERNEL       = 5       # GaussianBlur kernel size (must be odd)
OCR_PADDING           = 30      # pixels of padding added before Tesseract
OCR_MIN_TEXT_LENGTH   = 3       # minimum chars to accept Tesseract result
OCR_TESSERACT_CONFIGS = [
    "--oem 3 --psm 6",   # uniform block of text
    "--oem 3 --psm 3",   # fully automatic
    "--oem 3 --psm 4",   # single column
]

# Google Gemini fallback (used when Tesseract finds nothing)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")   # set via env var
GEMINI_MODEL   = "gemini-2.5-flash"
