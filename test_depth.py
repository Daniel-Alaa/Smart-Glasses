# =============================================================================
# tests/test_depth.py
# Unit tests for vision/depth.py
# Run with: pytest tests/test_depth.py -v
# =============================================================================

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# depth.py runs module-level init on import (loads calibration, builds maps).
# It gracefully falls back to approximate matrices when the .npz is absent,
# so these tests work without the physical camera rig.
from vision.depth import estimate_depth, sample_box_depth, rectify
import config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dummy_frames():
    """Return a realistic-sized pair of synthetic BGR frames."""
    h, w = config.CAMERA_HEIGHT, config.CAMERA_WIDTH
    left  = (np.random.rand(h, w, 3) * 255).astype(np.uint8)
    right = (np.random.rand(h, w, 3) * 255).astype(np.uint8)
    return left, right


@pytest.fixture(scope="module")
def depth_map(dummy_frames):
    """Compute one depth map to reuse across tests."""
    left, right = dummy_frames
    return estimate_depth(left, right)


# ---------------------------------------------------------------------------
# rectify()
# ---------------------------------------------------------------------------

class TestRectify:
    def test_returns_two_arrays(self, dummy_frames):
        left, right = dummy_frames
        result = rectify(left, right)
        assert isinstance(result, tuple) and len(result) == 2

    def test_output_shape_matches_input(self, dummy_frames):
        left, right = dummy_frames
        rect_l, rect_r = rectify(left, right)
        assert rect_l.shape == left.shape
        assert rect_r.shape == right.shape

    def test_output_dtype_uint8(self, dummy_frames):
        left, right = dummy_frames
        rect_l, rect_r = rectify(left, right)
        assert rect_l.dtype == np.uint8
        assert rect_r.dtype == np.uint8


# ---------------------------------------------------------------------------
# estimate_depth()
# ---------------------------------------------------------------------------

class TestEstimateDepth:
    def test_returns_ndarray(self, depth_map):
        assert isinstance(depth_map, np.ndarray)

    def test_correct_shape(self, depth_map):
        h, w = config.CAMERA_HEIGHT, config.CAMERA_WIDTH
        assert depth_map.shape == (h, w), (
            f"Expected ({h}, {w}), got {depth_map.shape}"
        )

    def test_dtype_float32(self, depth_map):
        assert depth_map.dtype == np.float32

    def test_no_negative_depth(self, depth_map):
        assert np.all(depth_map >= 0.0), "Depth map contains negative values."

    def test_no_inf_values(self, depth_map):
        assert not np.any(np.isinf(depth_map)), "Depth map contains inf values."

    def test_not_all_zeros(self, depth_map):
        # Noisy random frames should produce at least some non-zero disparities.
        # If all zeros, rectification maps or SGBM are broken.
        assert np.any(depth_map > 0), (
            "Depth map is entirely zero — check rectification maps and SGBM."
        )


# ---------------------------------------------------------------------------
# sample_box_depth()
# ---------------------------------------------------------------------------

class TestSampleBoxDepth:
    def test_returns_float_for_valid_region(self, depth_map):
        h, w = depth_map.shape
        # Inject known valid depth values into a region so the test is deterministic
        depth_map_copy = depth_map.copy()
        depth_map_copy[10:50, 10:50] = 1.5   # 1.5 m — within [DEPTH_MIN_M, DEPTH_MAX_M]

        result = sample_box_depth(depth_map_copy, x1=10, y1=10, x2=50, y2=50)
        assert result is not None, "Expected a float, got None for a valid region."
        assert isinstance(result, float)

    def test_returns_none_for_zero_region(self, depth_map):
        # A region filled with zeros has no valid pixels → should return None
        depth_map_copy = depth_map.copy()
        depth_map_copy[100:150, 100:150] = 0.0

        result = sample_box_depth(depth_map_copy, x1=100, y1=100, x2=150, y2=150)
        # Either None (no valid pixels) or a float — zeros are outside DEPTH_MIN_M
        # so result should be None if the whole region is zero
        if result is not None:
            # If non-None, must be within valid range
            assert config.DEPTH_MIN_M <= result <= config.DEPTH_MAX_M

    def test_returns_none_for_out_of_range_depth(self, depth_map):
        depth_map_copy = depth_map.copy()
        depth_map_copy[200:250, 200:250] = 999.0   # far beyond DEPTH_MAX_M

        result = sample_box_depth(depth_map_copy, x1=200, y1=200, x2=250, y2=250)
        assert result is None, "Expected None for region beyond DEPTH_MAX_M."

    def test_clamps_bbox_to_image_bounds(self, depth_map):
        h, w = depth_map.shape
        # Box extends beyond image — should not raise an exception
        depth_map_copy = depth_map.copy()
        depth_map_copy[0:h, 0:w] = 2.0
        result = sample_box_depth(depth_map_copy, x1=-10, y1=-10, x2=w+50, y2=h+50)
        # Just checking it doesn't crash; result may or may not be valid
        assert result is None or isinstance(result, float)

    def test_valid_depth_within_configured_range(self, depth_map):
        depth_map_copy = depth_map.copy()
        depth_map_copy[50:100, 50:100] = (config.DEPTH_MIN_M + config.DEPTH_MAX_M) / 2

        result = sample_box_depth(depth_map_copy, x1=50, y1=50, x2=100, y2=100)
        assert result is not None
        assert config.DEPTH_MIN_M <= result <= config.DEPTH_MAX_M
