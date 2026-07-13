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
