from routes import get_next_instruction, get_route, resolve_location
from imu import get_heading


def test_get_heading():
    heading = get_heading()
    assert isinstance(heading, float), "get_heading() must return a float"
    print(f"  get_heading() = {heading} ✓")


def test_get_next_instruction_normal():
    result = get_next_instruction("main gate", "food court", 0.0)
    assert isinstance(result, str), "must return a string"
    assert len(result) > 0, "must not return empty string"
    print(f"  main gate → food court: '{result}' ✓")


def test_get_next_instruction_same_location():
    result = get_next_instruction("cafeteria", "cafeteria", 0.0)
    assert "already" in result.lower(), "should say already there"
    print(f"  same location: '{result}' ✓")


def test_get_next_instruction_invalid():
    result = get_next_instruction("nowhere", "food court", 0.0)
    assert "no route" in result.lower(), "should say no route found"
    print(f"  invalid origin: '{result}' ✓")


def test_resolve_location_alias():
    assert resolve_location("gate") == "main gate"
    assert resolve_location("cafe") == "cafeteria"
    assert resolve_location("basketball") == "basketball court"
    print("  resolve_location aliases ✓")


if __name__ == "__main__":
    print("=== Navigator Tests ===\n")
    test_get_heading()
    test_get_next_instruction_normal()
    test_get_next_instruction_same_location()
    test_get_next_instruction_invalid()
    test_resolve_location_alias()
    print("\nAll tests passed ✅")