"""Pytest regression test: example YAML files must validate."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config.yaml import from_yaml


_REPO_ROOT = Path(__file__).resolve().parent


@pytest.mark.parametrize(
    "yaml_rel_path",
    [
        "examples/yamlFiles/EJ200.yaml",
        "examples/yamlFiles/CanonEF50mmf1p0L_example.yaml",
        "examples/yamlFiles/continuous_neutron_source_timing.yaml",
        "examples/yamlFiles/EJ276D.yaml",
        "examples/yamlFiles/three_component_timing_example.yaml",
        "examples/yamlFiles/pulsed_neutron_source_timing.yaml",
    ],
)
def test_example_yaml_validates_and_has_photon_culling_config(yaml_rel_path: str) -> None:
    config = from_yaml(_REPO_ROOT / yaml_rel_path)

    culling = config.geant4runner.photon_culling
    assert isinstance(culling.enabled, bool)
    assert 0.0 < culling.acceptance_angle_deg <= 180.0
