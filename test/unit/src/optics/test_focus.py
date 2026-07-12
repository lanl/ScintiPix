"""Tests for bounded pre-Geant4 autofocus."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config.LensCatalog import load_lens
from src.config.yaml import from_yaml
from src.optics.focus import auto_focus_lens


@pytest.mark.parametrize(
    "lens_id",
    [
        "CanonEF50mmf1.0L",
        "Nikkor80-200mmf2.8D",
        "NikkorZ58mmf0.95",
    ],
)
def test_catalog_autofocus_lenses_load(lens_id: str) -> None:
    """Each autofocus catalog entry should resolve its prescription and gaps."""

    lens = load_lens(lens_id)
    assert lens.zmx_file is not None
    assert Path(lens.zmx_file).is_file()
    assert lens.focus_gaps


def test_autofocus_requires_working_distance_bounds() -> None:
    """Autofocus must not invent a working-distance search interval."""

    config = from_yaml("examples/yamlFiles/CanonEF50mmf1p0L_example.yaml")
    lens = config.optical.lenses[0]
    lens.back_focus_mm = 38.65

    with pytest.raises(ValueError, match="workingDistanceBoundsMm"):
        auto_focus_lens(config)


@pytest.mark.parametrize(
    (
        "lens_id",
        "initial_working_distance_mm",
        "working_bounds_mm",
        "focus_bounds_mm",
        "initial_back_focus_mm",
        "back_focus_bounds_mm",
    ),
    [
        (
            "CanonEF50mmf1.0L",
            200.05,
            (150.0, 1000.0),
            (-2.0, 2.0),
            38.65,
            (30.0, 60.0),
        ),
        (
            "Nikkor80-200mmf2.8D",
            700.0,
            (150.0, 1200.0),
            (-0.15, 0.15),
            57.01947,
            (40.0, 80.0),
        ),
        (
            "NikkorZ58mmf0.95",
            320.994,
            (250.0, 600.0),
            (-5.0, 5.0),
            1.0,
            (0.5, 30.0),
        ),
    ],
)
def test_autofocus_traces_catalog_lens_with_computational_bounds(
    lens_id: str,
    initial_working_distance_mm: float,
    working_bounds_mm: tuple[float, float],
    focus_bounds_mm: tuple[float, float],
    initial_back_focus_mm: float,
    back_focus_bounds_mm: tuple[float, float],
) -> None:
    """Each catalog prescription should produce a bounded finite-FOV solution.

    These bounds exercise the optimizer. They are not validated mount or adapter
    limits and must not be copied into production configurations as such.
    """

    config = from_yaml("examples/yamlFiles/CanonEF50mmf1p0L_example.yaml")
    lens = load_lens(lens_id)
    lens.primary = True
    lens.focus_adjustment_bounds_mm = focus_bounds_mm
    lens.back_focus_bounds_mm = back_focus_bounds_mm
    lens.back_focus_mm = initial_back_focus_mm
    config.optical.lenses = [lens]

    scintillator_back_z_mm = (
        config.scintillator.position_mm.z_mm
        + config.scintillator.dimension_mm.z_mm / 2.0
    )
    config.optical.interface.position_mm.z_mm = (
        scintillator_back_z_mm + initial_working_distance_mm
    )
    config.optical.interface.working_distance_bounds_mm = working_bounds_mm

    original_fov = config.scintillator.field_of_view.model_copy()
    auto_focus_lens(config)

    optimized_working_distance_mm = (
        config.optical.interface.position_mm.z_mm - scintillator_back_z_mm
    )
    assert working_bounds_mm[0] <= optimized_working_distance_mm <= working_bounds_mm[1]
    assert lens.focus_adjustment_mm is not None
    assert focus_bounds_mm[0] <= lens.focus_adjustment_mm <= focus_bounds_mm[1]
    assert lens.back_focus_mm is not None
    assert back_focus_bounds_mm[0] <= lens.back_focus_mm <= back_focus_bounds_mm[1]
    assert config.scintillator.field_of_view == original_fov
