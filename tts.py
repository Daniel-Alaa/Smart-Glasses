# =============================================================================
# audio/tts.py
# Responsibility: Non-blocking text-to-speech output via espeak-ng.
# Interface:
#   speak(text: str) -> None   — queue a message (non-blocking)
#   stop()           -> None   — clear the queue and stop current speech
# =============================================================================

import queue
import subprocess
import threading
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_tts_queue: queue.Queue = queue.Queue()
_stop_event: threading.Event = threading.Event()
_current_proc = None  # type: subprocess.Popen | None
_proc_lock = threading.Lock()


def _say_blocking(text: str) -> None:
    """
    Synthesise and play `text` synchronously using espeak-ng.
    Runs inside the worker thread — never call from the main thread.
    """
    global _current_proc
    try:
        cmd = ["espeak-ng",
               "-v", config.TTS_VOICE,
               "-s", str(config.TTS_SPEED),
               text]
        with _proc_lock:
            _current_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        _current_proc.wait()
    except FileNotFoundError:
        # espeak-ng not installed — log and continue so the rest of the
        # system keeps running (useful on a dev laptop without audio)
        print(f"[tts] espeak-ng not found. Would have said: '{text}'")
    except Exception as e:
        print(f"[tts] ERROR: {e}")
    finally:
        with _proc_lock:
            _current_proc = None


def _worker() -> None:
    """Background thread: drain the queue and speak each message."""
    while not _stop_event.is_set():
        try:
            text = _tts_queue.get(timeout=0.2)
        except queue.Empty:
            continue
        _say_blocking(text)
        _tts_queue.task_done()


# Start the worker thread as a daemon so it dies with the main process
_worker_thread = threading.Thread(target=_worker, daemon=True, name="tts-worker")
_worker_thread.start()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def speak(text: str) -> None:
    """
    Queue `text` for speech output (non-blocking).

    Rules applied before queuing:
      1. Duplicate suppression — if this exact message is already waiting in
         the queue it is not added again.
      2. Queue cap — if the queue already has TTS_MAX_QUEUE messages waiting,
         the oldest message is dropped to make room.  This prevents a backlog
         of stale warnings building up when the system is busy.

    Args:
        text: The message to speak. Should be short and plain English.
    """
    if not text or not text.strip():
        return

    # Duplicate check
    current_queue = list(_tts_queue.queue)
    if text in current_queue:
        return

    # Queue-cap enforcement — drop the oldest item if at capacity
    while _tts_queue.qsize() >= config.TTS_MAX_QUEUE:
        try:
            dropped = _tts_queue.get_nowait()
            _tts_queue.task_done()
            print(f"[tts] Queue full — dropped stale message: '{dropped}'")
        except queue.Empty:
            break

    _tts_queue.put(text)
    print(f"[tts] Queued: '{text}'")


def stop() -> None:
    """
    Immediately clear the TTS queue and kill any in-progress speech.
    Useful when the user switches mode (e.g. navigation → reading).
    """
    # Drain queue
    while not _tts_queue.empty():
        try:
            _tts_queue.get_nowait()
            _tts_queue.task_done()
        except queue.Empty:
            break

    # Kill current subprocess
    with _proc_lock:
        if _current_proc is not None:
            try:
                _current_proc.terminate()
            except Exception:
                pass

    print("[tts] Stopped and queue cleared.")


def queue_size() -> int:
    """Return the number of messages currently waiting in the TTS queue."""
    return _tts_queue.qsize()