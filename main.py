# =============================================================================
# main.py  —  GIU Smart Glasses  —  Full System Orchestrator
# =============================================================================
# Wires together:
#   • Camera loop  (runs in background thread)
#   • Object detection  (runs in camera thread, results shared safely)
#   • Navigation loop   (runs in main thread, reads latest detections)
#   • ask_continue()    (multi-trip loop)
# =============================================================================

import threading
import time

# ── Vision pipeline ──────────────────────────────────────────────────────────
from camera.capture          import open_cameras, get_frames, release_cameras
from vision.depth            import estimate_depth
from vision.object_detection import detect_objects

# ── Navigation ───────────────────────────────────────────────────────────────
from navigation.navigator import Navigator

# ── Audio (use teammate's non-blocking TTS for the whole system) ─────────────
from audio.tts import speak

# ── STT (your Whisper-based listener) ────────────────────────────────────────
from speech import listen


# =============================================================================
# SHARED STATE  —  camera thread writes, navigation thread reads
# =============================================================================

_latest_detections: list[str] = []
_detections_lock               = threading.Lock()
_camera_running                = False


# =============================================================================
# CAMERA THREAD
# Continuously captures frames, runs depth + detection, stores results.
# Runs as a daemon so it dies automatically when main thread exits.
# =============================================================================

def _camera_loop():
    global _latest_detections, _camera_running

    print("[Main] Opening cameras...")
    open_cameras()
    _camera_running = True
    print("[Main] Camera loop started.")

    try:
        while _camera_running:
            left_frame, right_frame = get_frames()

            if left_frame is None:
                time.sleep(0.05)
                continue

            # Estimate depth from stereo pair
            depth_map = estimate_depth(left_frame, right_frame)

            # Run YOLO detection — returns list[str] e.g. ["person", "chair"]
            detections = detect_objects(left_frame, depth_map)

            # Write result safely
            with _detections_lock:
                _latest_detections = detections

            time.sleep(0.05)   # ~20 fps

    except Exception as e:
        print(f"[Camera] Error in camera loop: {e}")

    finally:
        release_cameras()
        print("[Main] Cameras released.")


def _get_latest_detections() -> list[str]:
    """Thread-safe getter — called by Navigator on every walking step."""
    with _detections_lock:
        return list(_latest_detections)


# =============================================================================
# ASK CONTINUE  —  after each trip
# =============================================================================

def _ask_continue() -> bool:
    speak("Do you want to go somewhere else?")

    while True:
        response = listen()
        if response is None:
            continue

        response = response.lower()

        if any(w in response for w in ["yes", "yeah", "yep", "sure", "okay"]):
            return True

        if any(w in response for w in ["no", "nope", "thank", "thanks"]):
            return False

        speak("Please say yes or no.")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    speak("Starting G I U Smart Glasses Navigation.")

    # ── Start camera + detection in background ───────────────────────────────
    cam_thread = threading.Thread(target=_camera_loop, daemon=True, name="CameraThread")
    cam_thread.start()

    # Give camera time to open and warm up before navigation starts
    print("[Main] Waiting for camera to warm up...")
    time.sleep(2.0)

    # ── Navigation loop ──────────────────────────────────────────────────────
    nav       = Navigator()
    first_run = True

    try:
        while True:
            nav.start(
                reuse_last_location = not first_run,
                get_detections_fn   = _get_latest_detections,   # inject here
            )
            first_run = False

            if not _ask_continue():
                speak("Okay. Have a nice day. Shutting down navigation.")
                break

    except KeyboardInterrupt:
        speak("Navigation interrupted. Shutting down.")

    finally:
        _camera_running = False          # signal camera thread to stop
        cam_thread.join(timeout=3.0)
        print("[Main] Shutdown complete.")