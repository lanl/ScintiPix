"""Tests for auto-focus optimization routines."""

from pathlib import Path

import pytest

# Step 1: Verify dependencies and load a lens model


def test_import_dependencies():
    """Verify all required dependencies can be imported."""
    try:
        import numpy as np
        import scipy.optimize
        from loguru import logger
        from rayoptics.optical.opticalmodel import OpticalModel
        from rayoptics.parax import firstorder
        from rayoptics.raytr import trace
        from rayoptics.seq.sequential import SequentialModel
        from rayoptics.zemax import zmxread

        assert True, "All dependencies imported successfully"
    except ImportError as e:
        pytest.fail(f"Missing dependency: {e}")


def test_import_focus_module():
    """Verify focus module can be imported."""
    try:
        from src.optics.focus import (
            auto_focus_lens,
            get_focus_gaps_as_tuples,
            apply_focus_adjustment,
            compute_image_distance_paraxial,
            compute_spot_size_rms,
            compute_focus_error_at_fixed_plane,
            optimize_focus_hybrid,
        )
        assert True, "Focus module imported successfully"
    except ImportError as e:
        pytest.fail(f"Could not import focus module: {e}")


def test_load_canon50mm_zmx():
    """Verify we can load the Canon 50mm ZMX file with rayoptics."""
    from rayoptics.zemax import zmxread

    zmx_path = Path("catalogs/lenses/mxFiles/CanonEF50mmf1.0L.zmx")

    if not zmx_path.exists():
        pytest.skip(f"ZMX file not found: {zmx_path}")

    opt_model = zmxread.read_lens_file(zmx_path, info=False)

    if isinstance(opt_model, tuple):
        opt_model = opt_model[0]

    assert opt_model is not None, "Optical model should be loaded"
    assert hasattr(opt_model, "seq_model"), "Optical model should have seq_model"

    seq_model = opt_model.seq_model
    assert hasattr(seq_model, "gaps"), "Sequential model should have gaps"
    assert len(seq_model.gaps) > 0, "Should have at least one gap"

    print(f"\nCanon 50mm loaded successfully:")
    print(f"  Number of gaps: {len(seq_model.gaps)}")


def test_load_nikkor_zmx():
    """Verify we can load the Nikkor 80-200mm ZMX file with rayoptics."""
    from rayoptics.zemax import zmxread

    zmx_path = Path("catalogs/lenses/mxFiles/Nikkor80-200mmf2.8D.zmx")

    if not zmx_path.exists():
        pytest.skip(f"ZMX file not found: {zmx_path}")

    opt_model = zmxread.read_lens_file(zmx_path, info=False)

    if isinstance(opt_model, tuple):
        opt_model = opt_model[0]

    assert opt_model is not None, "Optical model should be loaded"
    assert hasattr(opt_model, "seq_model"), "Optical model should have seq_model"

    seq_model = opt_model.seq_model
    assert hasattr(seq_model, "gaps"), "Sequential model should have gaps"
    assert len(seq_model.gaps) > 0, "Should have at least one gap"

    print(f"\nNikkor 80-200mm loaded successfully:")
    print(f"  Number of gaps: {len(seq_model.gaps)}")


def test_load_lens_from_catalog():
    """Verify we can load lens metadata from catalog including focus gaps."""
    from src.config.LensCatalog import load_lens

    lens = load_lens("CanonEF50mmf1.0L")

    assert lens is not None, "Lens should be loaded"
    assert lens.name == "CanonEF50mmf1.0L", "Lens name should match"
    assert lens.zmx_file is not None, "ZMX file path should be set"
    assert Path(lens.zmx_file).exists(), "ZMX file should exist"

    assert lens.focus_gaps is not None, "Focus gaps should be defined"
    assert len(lens.focus_gaps) > 0, "Should have at least one focus gap"

    print(f"\nLens catalog loaded successfully:")
    print(f"  Name: {lens.name}")
    print(f"  ZMX: {lens.zmx_file}")
    print(f"  Focus gaps: {len(lens.focus_gaps)}")
    for gap in lens.focus_gaps:
        print(f"    Gap {gap.gap_index}: default={gap.default_thickness_mm}mm, scale={gap.scaling_factor}")


# Step 2: Test helper functions with a simple lens


def test_get_focus_gaps_as_tuples():
    """Test converting FocusGap objects to tuples."""
    from src.config.LensCatalog import load_lens
    from src.optics.focus import get_focus_gaps_as_tuples

    lens = load_lens("CanonEF50mmf1.0L")
    focus_gaps = get_focus_gaps_as_tuples(lens)

    assert isinstance(focus_gaps, list), "Should return a list"
    assert len(focus_gaps) == 1, "Canon 50mm should have 1 focus gap"

    gap_idx, default_thi, scale = focus_gaps[0]
    assert gap_idx == 10, "Focus gap should be at index 10"
    assert default_thi == 10.229, "Default thickness should match catalog"
    assert scale == 1.0, "Scaling factor should be 1.0"

    print(f"\nFocus gaps converted to tuples:")
    for idx, thi, scl in focus_gaps:
        print(f"  Gap {idx}: default={thi}mm, scale={scl}")


def test_apply_focus_adjustment():
    """Test applying focus adjustment to lens gaps."""
    from pathlib import Path
    from rayoptics.zemax import zmxread
    from src.optics.focus import apply_focus_adjustment

    zmx_path = Path("catalogs/lenses/mxFiles/CanonEF50mmf1.0L.zmx")
    if not zmx_path.exists():
        pytest.skip(f"ZMX file not found: {zmx_path}")

    opt_model = zmxread.read_lens_file(zmx_path, info=False)
    if isinstance(opt_model, tuple):
        opt_model = opt_model[0]

    seq_model = opt_model.seq_model

    # Gap 10 has default thickness 10.229mm
    focus_gaps = [(10, 10.229, 1.0)]
    original_thickness = seq_model.gaps[10].thi

    # Apply +2mm adjustment
    zfine = 2.0
    apply_focus_adjustment(seq_model, focus_gaps, zfine)

    new_thickness = seq_model.gaps[10].thi
    expected_thickness = 10.229 + (2.0 * 1.0)

    assert abs(new_thickness - expected_thickness) < 0.001, \
        f"Gap thickness should be {expected_thickness}, got {new_thickness}"

    print(f"\nFocus adjustment test:")
    print(f"  Original gap 10 thickness: {original_thickness:.3f}mm")
    print(f"  Applied zfine: {zfine:+.3f}mm")
    print(f"  New gap 10 thickness: {new_thickness:.3f}mm")
    print(f"  Expected: {expected_thickness:.3f}mm")


def test_compute_image_distance_paraxial():
    """Test paraxial image distance calculation."""
    from pathlib import Path
    import numpy as np
    from rayoptics.zemax import zmxread
    from src.optics.focus import compute_image_distance_paraxial

    zmx_path = Path("catalogs/lenses/mxFiles/CanonEF50mmf1.0L.zmx")
    if not zmx_path.exists():
        pytest.skip(f"ZMX file not found: {zmx_path}")

    opt_model = zmxread.read_lens_file(zmx_path, info=False)
    if isinstance(opt_model, tuple):
        opt_model = opt_model[0]

    # Use the model as loaded (don't modify gaps to avoid ray tracing issues in tests)
    image_dist = compute_image_distance_paraxial(opt_model)

    assert np.isfinite(image_dist), "Image distance should be finite"
    assert image_dist != 0, "Image distance should be non-zero"

    print(f"\nParaxial image distance test:")
    print(f"  Image distance (as loaded): {image_dist:.3f}mm")


def test_compute_spot_size_rms():
    """Test RMS spot size calculation with ray tracing."""
    # This test is moved to Step 3 (integration test) to avoid complex setup
    pytest.skip("Skipped - full ray tracing tested in Step 3 integration tests")


def test_compute_focus_error_at_fixed_plane():
    """Test focus error measurement at fixed image plane."""
    # This test is moved to Step 3 (integration test) to avoid complex setup
    pytest.skip("Skipped - full ray tracing tested in Step 3 integration tests")


def test_optimize_focus_hybrid():
    """Test the two-stage hybrid focus optimization."""
    # This test is moved to Step 3 (integration test on real configuration)
    pytest.skip("Skipped - full optimization tested in Step 3 with realistic config")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
