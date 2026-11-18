import math
import time

# ─────────────────────────────────────────────
# IMU - Inertial Measurement Unit
# ─────────────────────────────────────────────
# Currently SIMULATED — no real hardware needed.
# When the real IMU sensor arrives (e.g. MPU6050),
# replace the simulate_steps() function with real
# sensor readings. Everything else stays the same.
# ─────────────────────────────────────────────

# Average step length in meters (adult average)
STEP_LENGTH_METERS = 0.75

# How many steps per second a normal walking person takes
STEPS_PER_SECOND = 1.8


class IMU:
    def __init__(self):
        self.total_steps = 0
        self.distance_covered = 0.0  # in meters
        self.is_walking = False

    def reset(self):
        """Reset step count and distance for a new route segment."""
        self.total_steps = 0
        self.distance_covered = 0.0
        self.is_walking = False

    def simulate_steps(self, target_distance_meters):
        """
        SIMULATED: Pretends the student is walking until target distance is covered.
        Prints progress so you can see what's happening during testing.

        In real hardware: replace this with actual accelerometer readings.
        """
        self.reset()
        steps_needed = math.ceil(target_distance_meters / STEP_LENGTH_METERS)

        print(f"[IMU] Starting walk — target: {target_distance_meters}m ({steps_needed} steps)")
        self.is_walking = True

        for step in range(1, steps_needed + 1):
            time.sleep(1 / STEPS_PER_SECOND)  # Simulate walking pace
            self.total_steps = step
            self.distance_covered = step * STEP_LENGTH_METERS

            # Print progress every 10 steps
            if step % 10 == 0 or step == steps_needed:
                print(f"[IMU] Steps: {step}/{steps_needed} | Distance: {self.distance_covered:.1f}m")

        self.is_walking = False
        print(f"[IMU] Target reached! Total steps: {self.total_steps}")
        return True

    def wait_for_turn(self, direction):
        """
        SIMULATED: Waits a moment to simulate the student making a turn.
        direction: 'left' or 'right'

        In real hardware: replace with gyroscope reading to detect actual turn.
        """
        print(f"[IMU] Waiting for student to turn {direction}...")
        time.sleep(3)  # Simulate time taken to turn
        print(f"[IMU] Turn {direction} detected!")
        return True

    def get_distance(self):
        """Return distance covered so far in meters."""
        return self.distance_covered

    def get_steps(self):
        """Return total steps taken so far."""
        return self.total_steps


# ─────────────────────────────────────────────
# INTERFACE CONTRACT
# ─────────────────────────────────────────────

def get_heading() -> float:
    """
    Returns current compass heading in degrees (0.0–360.0).
    Currently returns 0.0 — replace with real IMU sensor reading
    when hardware (e.g. MPU6050) is connected via I2C.
    """
    return 0.0
    
# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    imu = IMU()
    print("=== IMU Simulation Test ===")
    print("Simulating walk of 50 meters...\n")
    imu.simulate_steps(50)
    print(f"\nFinal distance: {imu.get_distance()}m")
    print(f"Final steps: {imu.get_steps()}")