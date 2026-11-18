# Smart Glasses — Assistive Navigation System
### Mechatronics Engineering Graduation Project — GIU

A wearable assistive system for visually impaired users built on the NVIDIA Jetson Orin Nano.
The glasses provide real-time voice-guided campus navigation, obstacle detection, stair awareness, and OCR text reading using stereo cameras and AI models.

---

## System Architecture

```
Stereo Cameras
      ↓
camera/capture.py  →  vision/depth.py  →  vision/object_detection.py
                                       →  vision/stair_detection.py
                                       →  vision/ocr.py
                                               ↓
                                       decision/logic.py
                                               ↓
                                         audio/tts.py
                                               ↑
navigation_system/navigator.py  ───────────────┘
```

---

## Project Structure

```
smart_glasses/
│
├── main.py                          # Full system entry point — wires all modules together
├── config.py                        # Single source of truth for all parameters and thresholds
├── requirements.txt                 # Laptop/dev dependencies
├── requirements_jetson.txt          # Jetson Orin Nano dependencies
│
├── navigation_system/               # Voice-guided campus navigation module
│   ├── navigator.py                 # Core Navigator class — manages the full guidance loop
│   ├── nav_main.py                  # Standalone navigation entry point (testing without camera)
│   ├── routes.py                    # Campus graph — nodes, edges, and route resolution
│   ├── imu.py                       # IMU interface — step counting and distance tracking
│   ├── kml_loader.py                # Loads GIU campus map from KML/KMZ files
│   ├── speech.py                    # Voice I/O — pyttsx3 TTS + Faster-Whisper STT
│   └── maps/
│       ├── new_GIU_map_withBorder.kml   # GIU campus map (KML format)
│       ├── new_GIU_map_withBorder.pgm   # GIU campus map (image format)
│       └── UPDATED_GIU_map.kmz          # Latest campus map (KMZ format)
│
├── vision/                          # All AI perception modules
│   ├── object_detection.py          # YOLO-based detection — returns list of nearby object labels
│   ├── stair_detection.py           # Stair direction detection — wraps object_detection
│   ├── depth.py                     # Stereo depth estimation — produces per-pixel depth map in metres
│   └── ocr.py                       # Text recognition — reads signs, labels, and displays
│
├── camera/                          # Camera hardware interface
│   ├── capture.py                   # Opens stereo cameras, returns synchronised left/right frames
│   └── calibration/
│       ├── calibrate.py             # Stereo calibration script — run once to generate stereo_map.xml
│       └── stereo_map.xml           # Calibration output used by depth.py for rectification
│
├── decision/                        # Central decision and priority layer
│   └── logic.py                     # process_frame() — prioritises what to announce each frame
│                                    # Priority: stairs > obstacles > navigation > OCR text
│                                    # Manages cooldowns to avoid repeated announcements
│
├── audio/                           # Audio output module
│   ├── tts.py                       # Non-blocking TTS via espeak-ng — queued background worker
│   └── clips/                       # Pre-recorded audio clips for instant playback
│       ├── arrived.wav              # Played on destination arrival
│       ├── obstacle.wav             # Generic obstacle warning sound
│       ├── stairs_up.wav            # Stair ascending alert
│       ├── stairs_down.wav          # Stair descending alert
│       ├── turn_left.wav            # Navigation turn instruction
│       └── turn_right.wav           # Navigation turn instruction
│
├── input/                           # Physical input handling
│   └── buttons.py                   # GPIO button interface for mode switching on Jetson
│
└── tests/                           # Module-level test scripts
    ├── test_navigation.py           # Tests Navigator, routes, IMU, and speech independently
    ├── test_camera.py               # Tests stereo camera capture and frame sync
    ├── test_detection.py            # Tests YOLO object detection on a sample frame
    ├── test_audio.py                # Tests TTS output and audio clip playback
    ├── test_imu.py                  # Tests step simulation and distance tracking
    └── test_ocr.py                  # Tests OCR text recognition on a sample image
```

---

## Setup

### Laptop / Development Machine

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Jetson Orin Nano

```bash
source venv/bin/activate
pip install -r requirements_jetson.txt
sudo apt install espeak-ng portaudio19-dev
```

---

## Running the System

### Full system (requires cameras)
```bash
PYTHONPATH=. python main.py
```

### Navigation only (no camera needed — for testing)
```bash
PYTHONPATH=. python navigation_system/nav_main.py
```

### On Jetson with GStreamer cameras
```bash
USE_GSTREAMER=1 PYTHONPATH=. python main.py
```

---

## Testing Individual Modules

```bash
PYTHONPATH=. python tests/test_navigation.py
PYTHONPATH=. python tests/test_camera.py
PYTHONPATH=. python tests/test_detection.py
PYTHONPATH=. python tests/test_audio.py
PYTHONPATH=. python tests/test_imu.py
PYTHONPATH=. python tests/test_ocr.py
```

---

## Key Configuration (`config.py`)

All tunable parameters live in `config.py`. Never hardcode values in modules.

| Parameter | Default | Description |
|---|---|---|
| `CLOSE_THRESHOLD_M` | `0.5` | Distance in metres below which an object is announced |
| `YOLO_CONF_THRESHOLD` | `0.40` | Minimum YOLO detection confidence |
| `LANDMARK_CONF_THRESHOLD` | `0.75` | Higher confidence required for doors/stairs/elevators |
| `TTS_SPEED` | `130` | espeak-ng speaking rate (words per minute) |
| `TTS_MAX_QUEUE` | `3` | Max queued TTS messages before dropping stale ones |
| `DEFAULT_STEP_DISTANCE` | `5` | Metres per navigation route segment |
| `USE_GSTREAMER` | `0` | Set to `1` on Jetson, `0` on laptop |
| `STEREO_BASELINE_M` | `0.065` | Physical distance between the two camera lenses |

---

## Navigation Flow

```
1. "Where are you right now?"  →  user speaks origin
2. "Where do you want to go?"  →  user speaks destination
3. System builds route and announces each step
4. IMU tracks walking distance between steps
5. Obstacle detection runs continuously during walking
6. On obstacle: voice alert → 2 second pause → resume walking
7. "You have arrived."
8. "Do you want to go somewhere else?"  →  yes loops, no shuts down
```

---

## Module Interface Contracts

These function signatures are fixed — do not change them without team agreement.

| Function | File | Returns |
|---|---|---|
| `detect_objects(frame, depth_map)` | `vision/object_detection.py` | `list[str]` |
| `detect_stairs(frame)` | `vision/stair_detection.py` | `"up"` \| `"down"` \| `None` |
| `estimate_depth(left, right)` | `vision/depth.py` | `np.ndarray` (float32, metres) |
| `get_frames()` | `camera/capture.py` | `(left_frame, right_frame)` |
| `speak(text)` | `audio/tts.py` | `None` (non-blocking) |
| `process_frame(...)` | `decision/logic.py` | `None` |
| `get_next_instruction(node, dest, heading)` | `navigation_system/routes.py` | `str` |
| `get_heading()` | `navigation_system/imu.py` | `float` (0.0–360.0) |

---

## Team

| Module | Owner |
|---|---|
| `camera/` | Person 1 |
| `vision/object_detection.py`, `stair_detection.py` | Person 2 |
| `vision/ocr.py`, `vision/depth.py` | Person 3 |
| `navigation_system/` | Maya |
| `audio/`, `input/` | Person 5 |
| `main.py`, `config.py`, `decision/` | Integrator |

---

## Models Required

These are not committed to the repo due to file size. Download and place them at these paths:

```
smart_glasses/models/yolov8n.pt                          # YOLOv8 nano — COCO model
smart_glasses/runs/detect/train/weights/best.pt          # Custom trained model (doors, stairs, elevators)
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `ultralytics` | YOLO object detection |
| `opencv-python` | Frame capture and image processing |
| `opencv-contrib-python` | WLS stereo depth filtering |
| `numpy` | Array operations |
| `faster-whisper` | On-device speech recognition (STT) |
| `pyttsx3` | Text-to-speech (navigation module) |
| `pyaudio` | Microphone audio capture |
| `networkx` | Campus route graph and pathfinding |
| `espeak-ng` | System TTS engine used by `audio/tts.py` |
