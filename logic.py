import time
 
# Cooldown per alert type (seconds) — prevents repeated announcements
COOLDOWNS = {
    "stairs":    3.0,
    "obstacle":  2.0,
    "navigation": 5.0,
    "text":      4.0,
}
 
_last_spoken = {}
 
def should_speak(alert_type: str) -> bool:
    """Returns True if enough time has passed since the last alert of this type."""
    now = time.time()
    last = _last_spoken.get(alert_type, 0)
    if now - last >= COOLDOWNS.get(alert_type, 2.0):
        _last_spoken[alert_type] = now
        return True
    return False
 
def decide(stairs, objects, text, nav_instruction) -> str | None:
    """
    Priority: stairs > obstacles > navigation > text
    Returns the highest-priority message to speak, or None.
    """
    if stairs and should_speak("stairs"):
        return f"Stairs {stairs}"
 
    if objects and should_speak("obstacle"):
        return f"Warning: {', '.join(objects)} ahead"
 
    if nav_instruction and should_speak("navigation"):
        return nav_instruction
 
    if text and should_speak("text"):
        return f"Text detected: {text}"
 
    return None
