# =============================================================================
# navigation/navigator.py
# Responsibility: Voice-guided step-by-step navigation.
#                 Walks the route, checks for obstacles each step,
#                 and pauses + alerts if something is in the way.
# =============================================================================

import time
import math
from speech import speak, listen
from routes import resolve_location, get_route
from imu import IMU

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

DEFAULT_STEP_DISTANCE = 5       # meters per route segment
OBSTACLE_COOLDOWN_SEC = 4       # seconds before re-alerting the same object
OBSTACLE_PAUSE_SEC    = 2       # seconds to pause after an alert so user can react
DETECTION_INTERVAL    = 0.15    # seconds between obstacle checks while walking

# Labels that are NOT treated as obstacles during navigation.
# Doors/elevators/stairs are handled by the vision layer separately.
_NON_OBSTACLE_LABELS = {"door", "elevator", "stair_up", "stair_down", "stair"}


class Navigator:
    def __init__(self):
        self.imu              = IMU()
        self.origin           = None
        self.destination      = None
        self.current_step     = 0
        self.route            = []
        self._get_detections  = None   # injected by main.py

    def reset(self):
        self.imu.reset()
        self.current_step = 0
        self.route        = []

    # ─────────────────────────────
    # ASK ORIGIN
    # ─────────────────────────────
    def ask_origin(self):
        speak("Where are you right now?")
        while True:
            response = listen()
            if response is None:
                continue
            location = resolve_location(response)
            if location:
                speak(f"Got it, you are at {location}.")
                return location
            speak("Sorry, I didn't catch that. Where are you?")

    # ─────────────────────────────
    # ASK DESTINATION
    # ─────────────────────────────
    def ask_destination(self):
        speak("Where do you want to go?")
        while True:
            response = listen()
            if response is None:
                continue
            location = resolve_location(response)
            if location:
                if location == self.origin:
                    speak("You are already there. Where do you want to go?")
                    continue
                speak(f"Okay, heading to {location}.")
                return location
            speak("I didn't catch that. Where do you want to go?")

    # ─────────────────────────────
    # WAIT FOR CHECKPOINT
    # ─────────────────────────────
    def wait_for_checkpoint(self, instruction):
        while True:
            speak("Say next when you are ready, or repeat to hear the instruction again.")
            response = listen()

            if response is None:
                speak("I am still here. Take your time. Say next when ready.")
                continue

            response = response.lower()

            if "next" in response:
                return

            if any(w in response for w in ["repeat", "again", "what", "not yet", "wait"]):
                speak(f"Sure. {instruction}")
                continue

            speak("Say next to continue, or repeat to hear the instruction again.")

    # ─────────────────────────────────────────────────────────────────────────
    # WALK WITH OBSTACLE CHECK
    # Replaces imu.simulate_steps() during real integration.
    # Walks the required distance while polling object detection every
    # DETECTION_INTERVAL seconds.  If an obstacle is seen it alerts the user,
    # waits OBSTACLE_PAUSE_SEC, then resumes — the walk timer keeps going so
    # the total distance covered stays correct.
    # ─────────────────────────────────────────────────────────────────────────
    def _walk_with_obstacle_check(self, distance_m):
        steps_needed   = math.ceil(distance_m / 0.75)   # 0.75 m per step (IMU constant)
        steps_done     = 0
        last_alerted   = {}                              # label → timestamp

        print(f"[Navigator] Walking {distance_m}m ({steps_needed} steps) with obstacle detection.")

        while steps_done < steps_needed:
            # ── Obstacle check ───────────────────────────────────────────────
            if self._get_detections is not None:
                detections = self._get_detections()
                obstacles  = [d for d in detections if d not in _NON_OBSTACLE_LABELS]

                for obj in obstacles:
                    now = time.time()
                    if now - last_alerted.get(obj, 0) > OBSTACLE_COOLDOWN_SEC:
                        speak(f"Warning. {obj} ahead.")
                        last_alerted[obj] = now
                        time.sleep(OBSTACLE_PAUSE_SEC)   # brief pause; loop continues after

            # ── Advance one step ─────────────────────────────────────────────
            steps_done += 1
            time.sleep(DETECTION_INTERVAL)

            if steps_done % 10 == 0 or steps_done == steps_needed:
                dist_so_far = steps_done * 0.75
                print(f"[Navigator] {steps_done}/{steps_needed} steps | {dist_so_far:.1f}m")

        print("[Navigator] Distance covered.")

    # ─────────────────────────────
    # GUIDANCE SYSTEM
    # ─────────────────────────────
    def guide(self):
        total_steps = len(self.route)

        for i, instruction in enumerate(self.route):
            self.current_step = i + 1

            speak(f"Step {self.current_step} of {total_steps}. {instruction}")

            # Last step — arrival, no walking needed
            if i == total_steps - 1:
                break

            speak("Start walking. I will let you know when you have covered the distance.")

            # Use real obstacle-aware walk if detection is available,
            # fall back to pure IMU simulation for standalone testing.
            if self._get_detections is not None:
                self._walk_with_obstacle_check(DEFAULT_STEP_DISTANCE)
            else:
                self.imu.simulate_steps(DEFAULT_STEP_DISTANCE)

            self.wait_for_checkpoint(instruction)

        speak(f"You have arrived at {self.destination}. Navigation complete.")
        self.origin = self.destination   # remember for next trip

    # ─────────────────────────────
    # START NAVIGATION
    # ─────────────────────────────
    def start(self, reuse_last_location=False, get_detections_fn=None):
        """
        Args:
            reuse_last_location: skip asking origin on subsequent trips.
            get_detections_fn:   callable () -> list[str], injected by main.py.
                                 Pass None to run in standalone / test mode.
        """
        self._get_detections = get_detections_fn
        self.reset()
        self.route = []

        if not reuse_last_location or self.origin is None:
            self.origin = self.ask_origin()
        else:
            speak(f"Continuing from {self.origin}.")

        self.destination = self.ask_destination()
        self.route       = get_route(self.origin, self.destination)

        if not self.route:
            speak(f"Sorry, I don't have a route from {self.origin} to {self.destination} yet.")
            return

        speak(
            f"I will guide you from {self.origin} to {self.destination}. "
            f"There are {len(self.route)} steps. Let's begin."
        )

        self.guide()


# ─────────────────────────────
# STANDALONE TEST (no camera)
# ─────────────────────────────
if __name__ == "__main__":
    nav = Navigator()
    nav.start()   # get_detections_fn=None → falls back to imu.simulate_steps()