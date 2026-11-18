# =============================================================================
# navigation/speech.py
# Responsibility: Voice I/O for the navigation module.
#   speak() — routes through audio/tts.py (espeak, non-blocking queue)
#   listen() — Faster-Whisper STT, unchanged
# =============================================================================

import pyaudio
import wave
import tempfile
import os
import time
from faster_whisper import WhisperModel

# Routes all TTS through teammate's espeak queue — one engine, no conflicts
from audio.tts import speak as _tts_speak


# =============================================================================
# MODEL SETUP
# =============================================================================

print("[Speech] Loading Faster-Whisper model...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
print("[Speech] Model loaded successfully!")

WHISPER_PROMPT = (
    "GIU campus navigation. Locations: "
    "A building, S building, M building, C building, "
    "food court, cafeteria, panorama, boosters, supermarket, "
    "padel, basketball court, tennis court, football field, main gate."
)

SAMPLE_RATE = 16000
CHUNK       = 1024


# =============================================================================
# TEXT TO SPEECH
# Non-blocking — queued through audio/tts.py (espeak).
# =============================================================================

def speak(text: str) -> None:
    print(f"[Glasses]: {text}")
    _tts_speak(text)


# =============================================================================
# RECORD AUDIO
# =============================================================================

def _record_audio(max_seconds=8):
    p      = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print("[Listening...]")
    stream.start_stream()

    frames             = []
    silent_chunks      = 0
    heard_something    = False
    post_speech_silent = 0

    SILENCE_THRESHOLD  = 500
    MAX_SILENT_CHUNKS  = int(SAMPLE_RATE / CHUNK * max_seconds)
    POST_SPEECH_CHUNKS = 15

    try:
        for _ in range(int(SAMPLE_RATE / CHUNK * max_seconds)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

            amplitude = max(
                abs(int.from_bytes(data[i:i+2], 'little', signed=True))
                for i in range(0, min(len(data), 200), 2)
            )

            if amplitude > SILENCE_THRESHOLD:
                heard_something    = True
                post_speech_silent = 0
                print(f"[Hearing...] amplitude={amplitude}    ", end="\r")
            else:
                if heard_something:
                    post_speech_silent += 1
                    if post_speech_silent >= POST_SPEECH_CHUNKS:
                        break
                else:
                    silent_chunks += 1
                    if silent_chunks >= MAX_SILENT_CHUNKS:
                        break
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        time.sleep(0.1)

    return frames, p


# =============================================================================
# SPEECH TO TEXT — FASTER WHISPER
# =============================================================================

def listen(timeout=8) -> str | None:
    frames, p = _record_audio(max_seconds=timeout)

    if not frames:
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        wf = wave.open(tmp.name, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

        segments, _ = whisper_model.transcribe(
            tmp.name,
            language="en",
            initial_prompt=WHISPER_PROMPT,
            beam_size=3,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        text = " ".join(seg.text for seg in segments).strip().lower()
        text = text.replace(".", "").replace(",", "").replace("?", "").replace("!", "").strip()

    finally:
        try:
            os.unlink(tmp.name)
        except PermissionError:
            pass

    if text:
        print(f"\n[Student said]: {text}")
        return text

    return None


# =============================================================================
# CONFIRMATION LISTENER
# =============================================================================

def listen_for_confirmation() -> str | None:
    while True:
        response = listen()
        if response is None:
            continue
        if "next"   in response:
            return "next"
        if "repeat" in response:
            return "repeat"


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    speak("Hello. Say a location name.")
    result = listen()
    if result:
        speak(f"You said {result}")
    else:
        speak("Nothing detected.")