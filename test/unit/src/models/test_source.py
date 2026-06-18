"""Comprehensive unit tests for primary source models."""

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

from src.models.source import (
    GpsAngular,
    GpsEnergy,
    GpsPosition,
    Source,
    SourceGps,
    SourceTiming,
)


# ============================================================================
# GpsPosition Tests
# ============================================================================


class TestGpsPosition:
    """Tests for GPS position distribution."""

    def test_valid_position_creation(self) -> None:
        """Valid position with all required fields should validate."""
        position = GpsPosition(
            type="Plane",
            shape="Circle",
            center_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": -20.0},
            radius_mm=5.0,
        )
        assert position.type == "Plane"
        assert position.shape == "Circle"
        assert position.center_mm.x_mm == 0.0
        assert position.center_mm.y_mm == 0.0
        assert position.center_mm.z_mm == -20.0
        assert position.radius_mm == 5.0

    def test_default_type_and_shape(self) -> None:
        """Default type and shape should be Plane and Circle."""
        position = GpsPosition(
            center_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
            radius_mm=1.0,
        )
        assert position.type == "Plane"
        assert position.shape == "Circle"

    def test_center_mm_alias_handling(self) -> None:
        """camelCase centerMm alias should map to center_mm."""
        position = GpsPosition.model_validate(
            {
                "centerMm": {"x_mm": 1.0, "y_mm": 2.0, "z_mm": 3.0},
                "radiusMm": 10.0,
            }
        )
        assert position.center_mm.x_mm == 1.0
        assert position.center_mm.y_mm == 2.0
        assert position.center_mm.z_mm == 3.0

    def test_radius_mm_alias_handling(self) -> None:
        """camelCase radiusMm alias should map to radius_mm."""
        position = GpsPosition.model_validate(
            {
                "centerMm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                "radiusMm": 15.5,
            }
        )
        assert position.radius_mm == 15.5

    def test_various_type_strings_accepted(self) -> None:
        """Various position type strings should be accepted."""
        types = ["Plane", "Volume", "Surface", "Point"]
        for pos_type in types:
            position = GpsPosition(
                type=pos_type,
                center_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                radius_mm=1.0,
            )
            assert position.type == pos_type

    def test_various_shape_strings_accepted(self) -> None:
        """Various shape strings should be accepted."""
        shapes = ["Circle", "Square", "Rectangle", "Sphere", "Cylinder"]
        for shape in shapes:
            position = GpsPosition(
                shape=shape,
                center_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                radius_mm=1.0,
            )
            assert position.shape == shape

    def test_empty_type_rejected(self) -> None:
        """Empty type string should be rejected (min_length=1)."""
        with pytest.raises(ValidationError, match="type"):
            GpsPosition(
                type="",
                center_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                radius_mm=1.0,
            )

    def test_empty_shape_rejected(self) -> None:
        """Empty shape string should be rejected (min_length=1)."""
        with pytest.raises(ValidationError, match="shape"):
            GpsPosition(
                shape="",
                center_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                radius_mm=1.0,
            )

    def test_zero_radius_rejected(self) -> None:
        """Zero radius should be rejected (gt=0)."""
        with pytest.raises(ValidationError, match="radius_mm"):
            GpsPosition(
                center_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                radius_mm=0.0,
            )

    def test_negative_radius_rejected(self) -> None:
        """Negative radius should be rejected."""
        with pytest.raises(ValidationError, match="radius_mm"):
            GpsPosition(
                center_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                radius_mm=-5.0,
            )

    def test_very_small_positive_radius_accepted(self) -> None:
        """Very small but positive radius should be accepted."""
        position = GpsPosition(
            center_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
            radius_mm=0.001,
        )
        assert position.radius_mm == 0.001

    def test_negative_center_coordinates_accepted(self) -> None:
        """Negative center coordinates should be accepted."""
        position = GpsPosition(
            center_mm={"x_mm": -10.0, "y_mm": -20.0, "z_mm": -30.0},
            radius_mm=5.0,
        )
        assert position.center_mm.x_mm == -10.0
        assert position.center_mm.y_mm == -20.0
        assert position.center_mm.z_mm == -30.0

    def test_serialization_uses_aliases(self) -> None:
        """Serialized output should use camelCase aliases."""
        position = GpsPosition(
            center_mm={"x_mm": 1.0, "y_mm": 2.0, "z_mm": 3.0},
            radius_mm=10.0,
        )
        dumped = position.model_dump(by_alias=True)
        assert "centerMm" in dumped
        assert "radiusMm" in dumped


# ============================================================================
# GpsAngular Tests
# ============================================================================


class TestGpsAngular:
    """Tests for GPS angular distribution."""

    def test_default_values(self) -> None:
        """Default values should be set correctly."""
        angular = GpsAngular()
        assert angular.type == "beam2d"
        assert angular.rot1.x == 1.0
        assert angular.rot1.y == 0.0
        assert angular.rot1.z == 0.0
        assert angular.rot2.x == 0.0
        assert angular.rot2.y == 1.0
        assert angular.rot2.z == 0.0
        assert angular.direction.x == 0.0
        assert angular.direction.y == 0.0
        assert angular.direction.z == 1.0

    def test_custom_type(self) -> None:
        """Custom angular type should be accepted."""
        angular = GpsAngular(type="iso")
        assert angular.type == "iso"

    def test_custom_rot1_vector(self) -> None:
        """Custom rot1 vector should be accepted."""
        angular = GpsAngular(rot1={"x": 0.0, "y": 1.0, "z": 0.0})
        assert angular.rot1.x == 0.0
        assert angular.rot1.y == 1.0
        assert angular.rot1.z == 0.0

    def test_custom_rot2_vector(self) -> None:
        """Custom rot2 vector should be accepted."""
        angular = GpsAngular(rot2={"x": 0.0, "y": 0.0, "z": 1.0})
        assert angular.rot2.x == 0.0
        assert angular.rot2.y == 0.0
        assert angular.rot2.z == 1.0

    def test_custom_direction_vector(self) -> None:
        """Custom direction vector should be accepted."""
        angular = GpsAngular(direction={"x": 1.0, "y": 0.0, "z": 0.0})
        assert angular.direction.x == 1.0
        assert angular.direction.y == 0.0
        assert angular.direction.z == 0.0

    def test_various_angular_types_accepted(self) -> None:
        """Various angular type strings should be accepted."""
        types = ["beam2d", "iso", "cos", "planar", "focused"]
        for ang_type in types:
            angular = GpsAngular(type=ang_type)
            assert angular.type == ang_type

    def test_empty_type_rejected(self) -> None:
        """Empty type string should be rejected (min_length=1)."""
        with pytest.raises(ValidationError, match="type"):
            GpsAngular(type="")

    def test_negative_vector_components_accepted(self) -> None:
        """Negative vector components should be accepted."""
        angular = GpsAngular(
            rot1={"x": -1.0, "y": 0.0, "z": 0.0},
            rot2={"x": 0.0, "y": -1.0, "z": 0.0},
            direction={"x": 0.0, "y": 0.0, "z": -1.0},
        )
        assert angular.rot1.x == -1.0
        assert angular.rot2.y == -1.0
        assert angular.direction.z == -1.0

    def test_fractional_vector_components_accepted(self) -> None:
        """Fractional vector components should be accepted (for normalized vectors)."""
        angular = GpsAngular(
            direction={"x": 0.577, "y": 0.577, "z": 0.577}
        )
        assert angular.direction.x == 0.577
        assert angular.direction.y == 0.577
        assert angular.direction.z == 0.577


# ============================================================================
# GpsEnergy Tests
# ============================================================================


class TestGpsEnergy:
    """Tests for GPS energy distribution."""

    def test_default_type_mono(self) -> None:
        """Default energy type should be Mono."""
        energy = GpsEnergy(mono_mev=2.45)
        assert energy.type == "Mono"

    def test_mono_energy_with_value(self) -> None:
        """Mono energy with value should validate."""
        energy = GpsEnergy(type="Mono", mono_mev=14.1)
        assert energy.type == "Mono"
        assert energy.mono_mev == 14.1

    def test_mono_mev_alias_handling(self) -> None:
        """camelCase monoMeV alias should map to mono_mev."""
        energy = GpsEnergy.model_validate({"type": "Mono", "monoMeV": 5.5})
        assert energy.mono_mev == 5.5

    def test_mono_type_requires_mono_mev(self) -> None:
        """Mono type requires mono_mev value."""
        with pytest.raises(
            ValidationError,
            match="monoMeV.*is required when type is 'Mono'",
        ):
            GpsEnergy(type="Mono")

    def test_mono_type_case_insensitive(self) -> None:
        """Mono type validation should be case-insensitive."""
        with pytest.raises(ValidationError, match="monoMeV"):
            GpsEnergy(type="mono")

        with pytest.raises(ValidationError, match="monoMeV"):
            GpsEnergy(type="MONO")

    def test_non_mono_type_without_mono_mev(self) -> None:
        """Non-Mono types should not require mono_mev."""
        energy = GpsEnergy(type="Lin")
        assert energy.type == "Lin"
        assert energy.mono_mev is None

    def test_various_energy_types_accepted(self) -> None:
        """Various energy type strings should be accepted."""
        types = ["Lin", "Pow", "Exp", "Gauss", "Arb", "Epn"]
        for energy_type in types:
            energy = GpsEnergy(type=energy_type)
            assert energy.type == energy_type

    def test_empty_type_rejected(self) -> None:
        """Empty type string should be rejected (min_length=1)."""
        with pytest.raises(ValidationError, match="type"):
            GpsEnergy(type="")

    def test_zero_mono_mev_rejected(self) -> None:
        """Zero mono_mev should be rejected (gt=0)."""
        with pytest.raises(ValidationError, match="mono_mev"):
            GpsEnergy(type="Mono", mono_mev=0.0)

    def test_negative_mono_mev_rejected(self) -> None:
        """Negative mono_mev should be rejected."""
        with pytest.raises(ValidationError, match="mono_mev"):
            GpsEnergy(type="Mono", mono_mev=-2.45)

    def test_very_small_positive_mono_mev_accepted(self) -> None:
        """Very small but positive mono_mev should be accepted."""
        energy = GpsEnergy(type="Mono", mono_mev=0.001)
        assert energy.mono_mev == 0.001

    def test_large_mono_mev_values_accepted(self) -> None:
        """Large mono_mev values should be accepted."""
        energy = GpsEnergy(type="Mono", mono_mev=1000.0)
        assert energy.mono_mev == 1000.0

    def test_serialization_uses_aliases(self) -> None:
        """Serialized output should use camelCase alias."""
        energy = GpsEnergy(type="Mono", mono_mev=2.45)
        dumped = energy.model_dump(by_alias=True)
        assert "monoMeV" in dumped


# ============================================================================
# SourceGps Tests
# ============================================================================


class TestSourceGps:
    """Tests for explicit GPS command payload."""

    @staticmethod
    def _minimal_gps_payload() -> dict:
        """Helper to create minimal valid GPS payload."""
        return {
            "particle": "neutron",
            "position": {
                "centerMm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": -20.0},
                "radiusMm": 5.0,
            },
            "energy": {"type": "Mono", "monoMeV": 2.45},
        }

    def test_valid_minimal_gps(self) -> None:
        """Minimal valid GPS configuration should validate."""
        gps = SourceGps.model_validate(self._minimal_gps_payload())
        assert gps.particle == "neutron"
        assert gps.position.type == "Plane"
        assert gps.position.shape == "Circle"
        assert gps.energy.mono_mev == 2.45

    def test_angular_default_factory(self) -> None:
        """angular should use default factory if not provided."""
        gps = SourceGps.model_validate(self._minimal_gps_payload())
        assert gps.angular.type == "beam2d"
        assert gps.angular.direction.z == 1.0

    def test_explicit_angular_configuration(self) -> None:
        """Explicit angular configuration should be accepted."""
        payload = self._minimal_gps_payload()
        payload["angular"] = {
            "type": "iso",
            "direction": {"x": 1.0, "y": 0.0, "z": 0.0},
        }
        gps = SourceGps.model_validate(payload)
        assert gps.angular.type == "iso"
        assert gps.angular.direction.x == 1.0

    def test_various_particle_types_accepted(self) -> None:
        """Various particle types should be accepted."""
        particles = ["neutron", "gamma", "proton", "electron", "alpha"]
        for particle in particles:
            payload = self._minimal_gps_payload()
            payload["particle"] = particle
            gps = SourceGps.model_validate(payload)
            assert gps.particle == particle

    def test_empty_particle_rejected(self) -> None:
        """Empty particle string should be rejected (min_length=1)."""
        payload = self._minimal_gps_payload()
        payload["particle"] = ""
        with pytest.raises(ValidationError, match="particle"):
            SourceGps.model_validate(payload)

    def test_complete_gps_configuration(self) -> None:
        """Complete GPS with all fields should validate."""
        gps = SourceGps.model_validate(
            {
                "particle": "proton",
                "position": {
                    "type": "Surface",
                    "shape": "Sphere",
                    "centerMm": {"x_mm": 10.0, "y_mm": 20.0, "z_mm": 30.0},
                    "radiusMm": 15.0,
                },
                "angular": {
                    "type": "cos",
                    "rot1": {"x": 0.0, "y": 1.0, "z": 0.0},
                    "rot2": {"x": 0.0, "y": 0.0, "z": 1.0},
                    "direction": {"x": 1.0, "y": 0.0, "z": 0.0},
                },
                "energy": {"type": "Mono", "monoMeV": 10.0},
            }
        )
        assert gps.particle == "proton"
        assert gps.position.shape == "Sphere"
        assert gps.angular.type == "cos"
        assert gps.energy.mono_mev == 10.0


# ============================================================================
# SourceTiming Tests
# ============================================================================


class TestSourceTiming:
    """Tests for source timing model."""

    def test_default_none_mode(self) -> None:
        """Default mode should be 'none'."""
        timing = SourceTiming()
        assert timing.mode == "none"
        assert timing.start_time_ns == 0.0
        assert timing.pulse_shape == "uniform"

    def test_none_mode_requires_no_additional_fields(self) -> None:
        """None mode should not require additional fields."""
        timing = SourceTiming(mode="none")
        assert timing.particle_flux is None
        assert timing.pulse_period_ns is None

    def test_continuous_mode_requires_particle_flux(self) -> None:
        """Continuous mode requires particle_flux."""
        with pytest.raises(
            ValidationError,
            match="particle_flux.*is required when timing mode is 'continuous'",
        ):
            SourceTiming(mode="continuous")

    def test_continuous_mode_with_particle_flux(self) -> None:
        """Continuous mode with particle_flux should validate."""
        timing = SourceTiming(mode="continuous", particle_flux=1e6)
        assert timing.mode == "continuous"
        assert timing.particle_flux == 1e6

    def test_pulsed_mode_requires_particle_flux(self) -> None:
        """Pulsed mode requires particle_flux."""
        with pytest.raises(
            ValidationError,
            match="particle_flux.*is required when timing mode is.*pulsed",
        ):
            SourceTiming(mode="pulsed")

    def test_pulsed_mode_requires_pulse_period_ns(self) -> None:
        """Pulsed mode requires pulse_period_ns."""
        with pytest.raises(
            ValidationError,
            match="pulse_period_ns.*required when.*mode.*is 'pulsed'",
        ):
            SourceTiming(mode="pulsed", particle_flux=1e6)

    def test_pulsed_mode_requires_pulse_time_width_ns(self) -> None:
        """Pulsed mode requires pulse_time_width_ns."""
        with pytest.raises(
            ValidationError,
            match="pulse_time_width_ns.*required when.*mode.*is 'pulsed'",
        ):
            SourceTiming(mode="pulsed", particle_flux=1e6, pulse_period_ns=100.0)

    def test_pulsed_mode_with_all_required_fields(self) -> None:
        """Pulsed mode with all required fields should validate."""
        timing = SourceTiming(
            mode="pulsed",
            particle_flux=1e6,
            pulse_period_ns=100.0,
            pulse_time_width_ns=10.0,
        )
        assert timing.mode == "pulsed"
        assert timing.particle_flux == 1e6
        assert timing.pulse_period_ns == 100.0
        assert timing.pulse_time_width_ns == 10.0

    def test_start_time_ns_alias_variations(self) -> None:
        """All start_time_ns aliases should be accepted."""
        timing1 = SourceTiming.model_validate({"start_time_ns": 100.0})
        assert timing1.start_time_ns == 100.0

        timing2 = SourceTiming.model_validate({"startTimeNs": 200.0})
        assert timing2.start_time_ns == 200.0

        timing3 = SourceTiming.model_validate({"startTime": 300.0})
        assert timing3.start_time_ns == 300.0

    def test_particle_flux_alias_variations(self) -> None:
        """Both particle_flux aliases should be accepted."""
        timing1 = SourceTiming.model_validate(
            {"mode": "continuous", "particle_flux": 1e5}
        )
        assert timing1.particle_flux == 1e5

        timing2 = SourceTiming.model_validate(
            {"mode": "continuous", "particleFlux": 2e5}
        )
        assert timing2.particle_flux == 2e5

    def test_pulse_period_ns_alias_variations(self) -> None:
        """All pulse_period_ns aliases should be accepted."""
        base = {"mode": "pulsed", "particle_flux": 1e6, "pulse_time_width_ns": 10.0}

        timing1 = SourceTiming.model_validate({**base, "pulse_period_ns": 100.0})
        assert timing1.pulse_period_ns == 100.0

        timing2 = SourceTiming.model_validate({**base, "pulsePeriodNs": 200.0})
        assert timing2.pulse_period_ns == 200.0

        timing3 = SourceTiming.model_validate({**base, "pulsePeriod": 300.0})
        assert timing3.pulse_period_ns == 300.0

    def test_pulse_time_offset_ns_alias_variations(self) -> None:
        """All pulse_time_offset_ns aliases should be accepted."""
        base = {
            "mode": "pulsed",
            "particle_flux": 1e6,
            "pulse_period_ns": 100.0,
            "pulse_time_width_ns": 10.0,
        }

        timing1 = SourceTiming.model_validate({**base, "pulse_time_offset_ns": 5.0})
        assert timing1.pulse_time_offset_ns == 5.0

        timing2 = SourceTiming.model_validate({**base, "pulseTimeOffsetNs": 10.0})
        assert timing2.pulse_time_offset_ns == 10.0

        timing3 = SourceTiming.model_validate({**base, "pulseTimeOffset": 15.0})
        assert timing3.pulse_time_offset_ns == 15.0

    def test_pulse_time_width_ns_alias_variations(self) -> None:
        """All pulse_time_width_ns aliases should be accepted."""
        base = {"mode": "pulsed", "particle_flux": 1e6, "pulse_period_ns": 100.0}

        timing1 = SourceTiming.model_validate({**base, "pulse_time_width_ns": 10.0})
        assert timing1.pulse_time_width_ns == 10.0

        timing2 = SourceTiming.model_validate({**base, "pulseTimeWidthNs": 20.0})
        assert timing2.pulse_time_width_ns == 20.0

        timing3 = SourceTiming.model_validate({**base, "pulseTimeWidth": 30.0})
        assert timing3.pulse_time_width_ns == 30.0

    def test_pulse_shape_alias_variations(self) -> None:
        """Both pulse_shape aliases should be accepted."""
        timing1 = SourceTiming.model_validate({"pulse_shape": "uniform"})
        assert timing1.pulse_shape == "uniform"

        timing2 = SourceTiming.model_validate({"pulseShape": "uniform"})
        assert timing2.pulse_shape == "uniform"

    def test_negative_start_time_ns_rejected(self) -> None:
        """Negative start_time_ns should be rejected (ge=0)."""
        with pytest.raises(ValidationError, match="start_time_ns"):
            SourceTiming(start_time_ns=-1.0)

    def test_zero_particle_flux_rejected(self) -> None:
        """Zero particle_flux should be rejected (gt=0)."""
        with pytest.raises(ValidationError, match="particle_flux"):
            SourceTiming(mode="continuous", particle_flux=0.0)

    def test_negative_particle_flux_rejected(self) -> None:
        """Negative particle_flux should be rejected."""
        with pytest.raises(ValidationError, match="particle_flux"):
            SourceTiming(mode="continuous", particle_flux=-1e6)

    def test_zero_pulse_period_ns_rejected(self) -> None:
        """Zero pulse_period_ns should be rejected (gt=0)."""
        with pytest.raises(ValidationError, match="pulse_period_ns"):
            SourceTiming(
                mode="pulsed",
                particle_flux=1e6,
                pulse_period_ns=0.0,
                pulse_time_width_ns=10.0,
            )

    def test_negative_pulse_time_offset_ns_rejected(self) -> None:
        """Negative pulse_time_offset_ns should be rejected (ge=0)."""
        with pytest.raises(ValidationError, match="pulse_time_offset_ns"):
            SourceTiming(
                mode="pulsed",
                particle_flux=1e6,
                pulse_period_ns=100.0,
                pulse_time_width_ns=10.0,
                pulse_time_offset_ns=-5.0,
            )

    def test_complete_pulsed_timing_configuration(self) -> None:
        """Complete pulsed timing with all fields should validate."""
        timing = SourceTiming(
            mode="pulsed",
            start_time_ns=50.0,
            particle_flux=5e6,
            pulse_period_ns=200.0,
            pulse_time_offset_ns=10.0,
            pulse_time_width_ns=20.0,
            pulse_shape="uniform",
        )
        assert timing.mode == "pulsed"
        assert timing.start_time_ns == 50.0
        assert timing.particle_flux == 5e6
        assert timing.pulse_period_ns == 200.0
        assert timing.pulse_time_offset_ns == 10.0
        assert timing.pulse_time_width_ns == 20.0
        assert timing.pulse_shape == "uniform"

    def test_serialization_uses_snake_case(self) -> None:
        """Serialized output should use snake_case (serialization_alias)."""
        timing = SourceTiming(mode="continuous", particle_flux=1e6)
        dumped = timing.model_dump(by_alias=True)
        assert "start_time_ns" in dumped
        assert "particle_flux" in dumped
        assert "pulse_shape" in dumped


# ============================================================================
# Source Tests
# ============================================================================


class TestSource:
    """Tests for complete primary source block."""

    @staticmethod
    def _minimal_source_payload() -> dict:
        """Helper to create minimal valid source payload."""
        return {
            "gps": {
                "particle": "neutron",
                "position": {
                    "centerMm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": -20.0},
                    "radiusMm": 5.0,
                },
                "energy": {"type": "Mono", "monoMeV": 2.45},
            }
        }

    def test_valid_minimal_source(self) -> None:
        """Minimal valid source should validate."""
        source = Source.model_validate(self._minimal_source_payload())
        assert source.gps.particle == "neutron"
        assert source.gps.position.radius_mm == 5.0
        assert source.gps.energy.mono_mev == 2.45
        assert source.timing is None

    def test_source_with_none_timing(self) -> None:
        """Source with explicit none timing should validate."""
        payload = self._minimal_source_payload()
        payload["timing"] = {"mode": "none"}
        source = Source.model_validate(payload)
        assert source.timing.mode == "none"

    def test_source_with_continuous_timing(self) -> None:
        """Source with continuous timing should validate."""
        payload = self._minimal_source_payload()
        payload["timing"] = {"mode": "continuous", "particle_flux": 1e6}
        source = Source.model_validate(payload)
        assert source.timing.mode == "continuous"
        assert source.timing.particle_flux == 1e6

    def test_source_with_pulsed_timing(self) -> None:
        """Source with pulsed timing should validate."""
        payload = self._minimal_source_payload()
        payload["timing"] = {
            "mode": "pulsed",
            "particle_flux": 2e6,
            "pulse_period_ns": 150.0,
            "pulse_time_width_ns": 15.0,
        }
        source = Source.model_validate(payload)
        assert source.timing.mode == "pulsed"
        assert source.timing.pulse_period_ns == 150.0

    def test_complete_source_configuration(self) -> None:
        """Complete source with all fields should validate."""
        source = Source.model_validate(
            {
                "gps": {
                    "particle": "gamma",
                    "position": {
                        "type": "Volume",
                        "shape": "Cylinder",
                        "centerMm": {"x_mm": 5.0, "y_mm": 10.0, "z_mm": -15.0},
                        "radiusMm": 12.5,
                    },
                    "angular": {
                        "type": "iso",
                        "rot1": {"x": 1.0, "y": 0.0, "z": 0.0},
                        "rot2": {"x": 0.0, "y": 1.0, "z": 0.0},
                        "direction": {"x": 0.0, "y": 0.0, "z": 1.0},
                    },
                    "energy": {"type": "Mono", "monoMeV": 0.662},
                },
                "timing": {
                    "mode": "pulsed",
                    "start_time_ns": 100.0,
                    "particle_flux": 1e7,
                    "pulse_period_ns": 250.0,
                    "pulse_time_offset_ns": 20.0,
                    "pulse_time_width_ns": 30.0,
                    "pulse_shape": "uniform",
                },
            }
        )
        assert source.gps.particle == "gamma"
        assert source.gps.position.type == "Volume"
        assert source.gps.angular.type == "iso"
        assert source.gps.energy.mono_mev == 0.662
        assert source.timing.mode == "pulsed"
        assert source.timing.start_time_ns == 100.0

    def test_source_without_timing_field(self) -> None:
        """Source without timing field should have None timing."""
        source = Source.model_validate(self._minimal_source_payload())
        assert source.timing is None
