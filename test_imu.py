from navigation.imu_fusion import get_heading, get_step_count
 
def test_imu():
    heading = get_heading()
    steps = get_step_count()
    assert 0 <= heading <= 360, "Heading out of range"
    print(f"Heading: {heading}°, Steps: {steps}")
 
if __name__ == "__main__":
    test_imu()
