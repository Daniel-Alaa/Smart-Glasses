# Modes available in the system
MODES = ["navigation", "reading", "awareness"]
_current_mode_index = 0
 
def get_current_mode() -> str:
    """Returns the currently active mode."""
    return MODES[_current_mode_index]
 
def next_mode():
    """Cycles to the next mode (called on button press)."""
    global _current_mode_index
    _current_mode_index = (_current_mode_index + 1) % len(MODES)
    print(f"[INPUT] Mode switched to: {get_current_mode()}")
 
# TODO: wire this to GPIO pins or Arduino serial input
