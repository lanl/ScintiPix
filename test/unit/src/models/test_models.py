from __future__ import annotations

from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "src").is_dir() and (parent / "pixi.toml").is_file():
            return parent
    raise RuntimeError("Could not resolve repository root from test path.")


sys.path.insert(0, str(_repo_root()))

from src.models.geant4runtime import Geant4RunTime, Geant4RuntimeControls
from src.models.intensifier import Intensifier, IntensifierInputScreen
from src.models.scintillator import (
    ScintillationTimeComponentsByExcitation,
    ScintillatorProperties,
)
from src.models.sensor import Sensor
from src.models.source import SourceTiming


def _scintillator_payload() -> dict[str, object]:
    return {
        "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
        "dimension_mm": {"x_mm": 50.0, "y_mm": 50.0, "z_mm": 10.0},
        "properties": {
            "name": "TestScintillator",
            "photonEnergy": [2.0, 2.4, 2.8],
            "rIndex": [1.58, 1.58, 1.58],
            "nKEntries": 3,
            "timeComponents": {
                "default": [
                    {"timeConstant": 2.1, "yieldFraction": 1.0},
                    {"timeConstant": 0.0, "yieldFraction": 0.0},
                    {"timeConstant": 0.0, "yieldFraction": 0.0},
                ]
            },
        },
    }


def _intensifier_payload() -> dict[str, object]:
    return {
        "model": "Cricket2",
        "input_screen": {
            "image_circle_diameter_mm": 18.0,
            "center_mm": [0.0, 0.0],
        },
    }


def _sensor_payload() -> dict[str, object]:
    return {
        "model": "Timepix3",
        "timepix": {
            "pixels_x": 256,
            "pixels_y": 256,
            "pixel_pitch_mm": 0.055,
            "max_tot_ns": 25550.0,
            "dead_time_ns": 475.0,
        },
    }


def test_models_module_imports() -> None:
    import src.models.base
    import src.models.geant4runtime
    import src.models.intensifier
    import src.models.metadata
    import src.models.optics
    import src.models.scintillator
    import src.models.sensor
    import src.models.simulation
    import src.models.source


def test_source_timing_requires_mode_payload() -> None:
    SourceTiming(mode="continuous", particle_flux=1.0)

    with pytest.raises(ValidationError, match="particle_flux"):
        SourceTiming(mode="continuous")

    with pytest.raises(ValidationError, match="pulse_period_ns"):
        SourceTiming(mode="pulsed", particle_flux=1.0)


def test_scintillator_profile_and_table_validation() -> None:
    profile = ScintillationTimeComponentsByExcitation.model_validate(
        _scintillator_payload()["properties"]["timeComponents"]
    )
    assert profile.resolve_for_particle("neutron")[0] == "default"

    invalid_payload = _scintillator_payload()["properties"] | {
        "rIndex": [1.58, 1.58],
    }
    with pytest.raises(ValidationError, match="rIndex"):
        ScintillatorProperties.model_validate(invalid_payload)


def test_intensifier_aliases_and_qe_table_validation() -> None:
    screen = IntensifierInputScreen.model_validate(
        {"imageCircleDiameterMm": 18.0, "centerMm": {"x": 1.0, "y": 2.0}}
    )
    assert screen.center_mm == (1.0, 2.0)

    with pytest.raises(ValidationError, match="same length"):
        Intensifier.model_validate(
            _intensifier_payload()
            | {
                "photocathode": {
                    "qe_wavelength_nm": [350.0, 500.0],
                    "qe_values": [0.2],
                }
            }
        )


def test_sensor_rejects_blank_model_name() -> None:
    with pytest.raises(ValidationError, match="sensor.model"):
        Sensor.model_validate(_sensor_payload() | {"model": "   "})


def test_geant4_runtime_requires_simulation_command_payload() -> None:
    runtime = Geant4RunTime.model_validate({"numberOfParticles": 10})
    assert runtime.number_of_particles == 10

    with pytest.raises(ValidationError, match="numberOfParticles"):
        Geant4RunTime.model_validate({})

    with pytest.raises(ValidationError, match="at least one control"):
        Geant4RuntimeControls.model_validate({})
