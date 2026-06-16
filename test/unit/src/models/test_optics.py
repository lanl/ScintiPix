"""Comprehensive unit tests for optical models."""

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

from src.models.optics import (
    Lens,
    OpticalGeometry,
    OpticalTransportAssumptions,
    Optics,
    SensitiveDetector,
)


# ============================================================================
# Lens Tests
# ============================================================================


class TestLens:
    """Tests for individual lens descriptor."""

    def test_valid_lens_with_catalog_id(self) -> None:
        """Lens with catalog ID should validate."""
        lens = Lens(catalog_id="CanonEF50mmf1.0L", primary=True)
        assert lens.catalog_id == "CanonEF50mmf1.0L"
        assert lens.primary is True
        assert lens.name == "CanonEF50mmf1.0L"

    def test_valid_lens_with_zmx_file(self) -> None:
        """Lens with zmxFile should validate."""
        lens = Lens(zmx_file="lenses/custom_lens.zmx", primary=False)
        assert lens.zmx_file == "lenses/custom_lens.zmx"
        assert lens.primary is False
        assert lens.name == "custom_lens"

    def test_valid_lens_with_both_catalog_and_zmx(self) -> None:
        """Lens can specify both catalogId and zmxFile."""
        lens = Lens(
            catalog_id="TestLens",
            zmx_file="lenses/test.zmx",
            primary=True,
        )
        assert lens.catalog_id == "TestLens"
        assert lens.zmx_file == "lenses/test.zmx"
        assert lens.name == "TestLens"

    def test_catalog_id_alias_handling(self) -> None:
        """camelCase catalogId alias should map to catalog_id."""
        lens = Lens.model_validate({"catalogId": "TestLens"})
        assert lens.catalog_id == "TestLens"

    def test_zmx_file_alias_handling(self) -> None:
        """camelCase zmxFile alias should map to zmx_file."""
        lens = Lens.model_validate({"zmxFile": "test.zmx"})
        assert lens.zmx_file == "test.zmx"

    def test_smx_file_alias_handling(self) -> None:
        """camelCase smxFile alias should map to smx_file."""
        lens = Lens.model_validate(
            {"zmxFile": "test.zmx", "smxFile": "test.smx"}
        )
        assert lens.smx_file == "test.smx"

    def test_name_auto_generation_from_catalog_id(self) -> None:
        """Name should auto-generate from catalog_id if not provided."""
        lens = Lens(catalog_id="AutoNameLens")
        assert lens.name == "AutoNameLens"

    def test_name_auto_generation_from_zmx_file_stem(self) -> None:
        """Name should auto-generate from zmx file stem if catalog_id absent."""
        lens = Lens(zmx_file="path/to/my_lens.zmx")
        assert lens.name == "my_lens"

    def test_name_fallback_when_both_present(self) -> None:
        """Name should prefer catalog_id over zmx_file when both present."""
        lens = Lens(catalog_id="CatalogName", zmx_file="file_name.zmx")
        assert lens.name == "CatalogName"

    def test_explicit_name_preserved(self) -> None:
        """Explicitly provided name should be preserved."""
        lens = Lens(catalog_id="CatalogID", name="CustomName")
        assert lens.name == "CustomName"

    def test_description_field(self) -> None:
        """Description field should accept strings."""
        lens = Lens(
            catalog_id="TestLens",
            description="Test lens for validation",
        )
        assert lens.description == "Test lens for validation"

    def test_primary_defaults_to_false(self) -> None:
        """Primary should default to False."""
        lens = Lens(catalog_id="TestLens")
        assert lens.primary is False

    def test_missing_catalog_and_zmx_rejected(self) -> None:
        """Lens without catalogId or zmxFile should be rejected."""
        with pytest.raises(
            ValidationError,
            match="must provide `catalogId` and/or `zmxFile`",
        ):
            Lens(name="NoReference")

    def test_empty_catalog_id_rejected(self) -> None:
        """Empty catalog_id should be rejected due to min_length constraint."""
        with pytest.raises(ValidationError, match="catalog_id"):
            Lens(catalog_id="")

    def test_empty_zmx_file_rejected(self) -> None:
        """Empty zmx_file should be rejected due to min_length constraint."""
        with pytest.raises(ValidationError, match="zmx_file"):
            Lens(zmx_file="")

    def test_whitespace_name_triggers_auto_generation(self) -> None:
        """Whitespace-only name should trigger auto-generation."""
        lens = Lens(catalog_id="AutoGen", name="   ")
        assert lens.name == "AutoGen"

    def test_serialization_uses_aliases(self) -> None:
        """Serialized output should use camelCase aliases."""
        lens = Lens(
            catalog_id="TestLens",
            zmx_file="test.zmx",
            smx_file="test.smx",
        )
        dumped = lens.model_dump(by_alias=True)
        assert "catalogId" in dumped
        assert "zmxFile" in dumped
        assert "smxFile" in dumped


# ============================================================================
# OpticalGeometry Tests
# ============================================================================


class TestOpticalGeometry:
    """Tests for optical envelope dimensions."""

    def test_valid_geometry_creation(self) -> None:
        """Valid geometry with positive dimensions should validate."""
        geometry = OpticalGeometry(
            entrance_diameter=60.5,
            sensor_max_width=36.0,
        )
        assert geometry.entrance_diameter == 60.5
        assert geometry.sensor_max_width == 36.0

    def test_alias_handling(self) -> None:
        """camelCase aliases should map to snake_case fields."""
        geometry = OpticalGeometry.model_validate(
            {
                "entranceDiameter": 50.0,
                "sensorMaxWidth": 24.0,
            }
        )
        assert geometry.entrance_diameter == 50.0
        assert geometry.sensor_max_width == 24.0

    def test_zero_entrance_diameter_rejected(self) -> None:
        """Zero entrance_diameter should be rejected (gt=0 constraint)."""
        with pytest.raises(ValidationError, match="entrance_diameter"):
            OpticalGeometry(entrance_diameter=0.0, sensor_max_width=36.0)

    def test_negative_entrance_diameter_rejected(self) -> None:
        """Negative entrance_diameter should be rejected."""
        with pytest.raises(ValidationError, match="entrance_diameter"):
            OpticalGeometry(entrance_diameter=-10.0, sensor_max_width=36.0)

    def test_zero_sensor_max_width_rejected(self) -> None:
        """Zero sensor_max_width should be rejected (gt=0 constraint)."""
        with pytest.raises(ValidationError, match="sensor_max_width"):
            OpticalGeometry(entrance_diameter=60.0, sensor_max_width=0.0)

    def test_negative_sensor_max_width_rejected(self) -> None:
        """Negative sensor_max_width should be rejected."""
        with pytest.raises(ValidationError, match="sensor_max_width"):
            OpticalGeometry(entrance_diameter=60.0, sensor_max_width=-5.0)

    def test_very_small_positive_values_accepted(self) -> None:
        """Very small but positive values should be accepted."""
        geometry = OpticalGeometry(
            entrance_diameter=0.001,
            sensor_max_width=0.001,
        )
        assert geometry.entrance_diameter == 0.001
        assert geometry.sensor_max_width == 0.001

    def test_serialization_uses_aliases(self) -> None:
        """Serialized output should use camelCase aliases."""
        geometry = OpticalGeometry(
            entrance_diameter=60.5,
            sensor_max_width=36.0,
        )
        dumped = geometry.model_dump(by_alias=True)
        assert "entranceDiameter" in dumped
        assert "sensorMaxWidth" in dumped


# ============================================================================
# SensitiveDetector Tests
# ============================================================================


class TestSensitiveDetector:
    """Tests for sensitive detector configuration."""

    def test_valid_detector_creation(self) -> None:
        """Valid detector with all required fields should validate."""
        detector = SensitiveDetector(
            position_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 210.0},
            shape="circle",
            diameter_rule="min(entranceDiameter,sensorMaxWidth)",
        )
        assert detector.position_mm.x_mm == 0.0
        assert detector.position_mm.y_mm == 0.0
        assert detector.position_mm.z_mm == 210.0
        assert detector.shape == "circle"
        assert detector.diameter_rule == "min(entranceDiameter,sensorMaxWidth)"

    def test_diameter_rule_alias_handling(self) -> None:
        """camelCase diameterRule alias should map to diameter_rule."""
        detector = SensitiveDetector.model_validate(
            {
                "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 200.0},
                "shape": "square",
                "diameterRule": "entranceDiameter * 0.9",
            }
        )
        assert detector.diameter_rule == "entranceDiameter * 0.9"

    def test_empty_shape_rejected(self) -> None:
        """Empty shape string should be rejected (min_length=1)."""
        with pytest.raises(ValidationError, match="shape"):
            SensitiveDetector(
                position_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 200.0},
                shape="",
                diameter_rule="test",
            )

    def test_empty_diameter_rule_rejected(self) -> None:
        """Empty diameter_rule should be rejected (min_length=1)."""
        with pytest.raises(ValidationError, match="diameter_rule"):
            SensitiveDetector(
                position_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 200.0},
                shape="circle",
                diameter_rule="",
            )

    def test_various_shape_strings_accepted(self) -> None:
        """Various shape strings should be accepted."""
        shapes = ["circle", "square", "rectangle", "custom_shape"]
        for shape in shapes:
            detector = SensitiveDetector(
                position_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 200.0},
                shape=shape,
                diameter_rule="test",
            )
            assert detector.shape == shape

    def test_complex_diameter_rules_accepted(self) -> None:
        """Complex diameter rule expressions should be accepted."""
        rules = [
            "entranceDiameter",
            "sensorMaxWidth",
            "min(entranceDiameter,sensorMaxWidth)",
            "entranceDiameter * 0.95",
            "sqrt(2) * sensorMaxWidth",
        ]
        for rule in rules:
            detector = SensitiveDetector(
                position_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 200.0},
                shape="circle",
                diameter_rule=rule,
            )
            assert detector.diameter_rule == rule

    def test_serialization_uses_aliases(self) -> None:
        """Serialized output should use camelCase alias for diameter_rule."""
        detector = SensitiveDetector(
            position_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 210.0},
            shape="circle",
            diameter_rule="test",
        )
        dumped = detector.model_dump(by_alias=True)
        assert "diameterRule" in dumped


# ============================================================================
# OpticalTransportAssumptions Tests
# ============================================================================


class TestOpticalTransportAssumptions:
    """Tests for optical transport physical assumptions."""

    def test_default_values(self) -> None:
        """Default values should be set correctly."""
        assumptions = OpticalTransportAssumptions()
        assert assumptions.object_plane == "scintillator_back_face"
        assert assumptions.optical_interface_represents == "lens_entrance_plane"

    def test_object_plane_alias_handling(self) -> None:
        """Both objectPlane and object_plane should be accepted."""
        assumptions1 = OpticalTransportAssumptions.model_validate(
            {"objectPlane": "scintillator_back_face"}
        )
        assert assumptions1.object_plane == "scintillator_back_face"

        assumptions2 = OpticalTransportAssumptions.model_validate(
            {"object_plane": "scintillator_back_face"}
        )
        assert assumptions2.object_plane == "scintillator_back_face"

    def test_optical_interface_alias_handling(self) -> None:
        """Both opticalInterfaceRepresents and optical_interface_represents should be accepted."""
        assumptions1 = OpticalTransportAssumptions.model_validate(
            {"opticalInterfaceRepresents": "lens_entrance_plane"}
        )
        assert assumptions1.optical_interface_represents == "lens_entrance_plane"

        assumptions2 = OpticalTransportAssumptions.model_validate(
            {"optical_interface_represents": "lens_entrance_plane"}
        )
        assert assumptions2.optical_interface_represents == "lens_entrance_plane"

    def test_serialization_uses_aliases(self) -> None:
        """Serialized output should use camelCase aliases."""
        assumptions = OpticalTransportAssumptions()
        dumped = assumptions.model_dump(by_alias=True)
        assert "objectPlane" in dumped
        assert "opticalInterfaceRepresents" in dumped

    def test_invalid_object_plane_value_rejected(self) -> None:
        """Invalid literal value for object_plane should be rejected."""
        with pytest.raises(ValidationError, match="object_plane"):
            OpticalTransportAssumptions.model_validate(
                {"object_plane": "invalid_plane"}
            )

    def test_invalid_optical_interface_value_rejected(self) -> None:
        """Invalid literal value for optical_interface_represents should be rejected."""
        with pytest.raises(ValidationError, match="optical_interface_represents"):
            OpticalTransportAssumptions.model_validate(
                {"optical_interface_represents": "invalid_interface"}
            )


# ============================================================================
# Optics Tests
# ============================================================================


class TestOptics:
    """Tests for complete optical subsystem definition."""

    @staticmethod
    def _minimal_optics_payload() -> dict:
        """Helper to create minimal valid optics payload."""
        return {
            "lenses": [{"catalogId": "CanonEF50mmf1.0L", "primary": True}],
            "geometry": {"entranceDiameter": 60.5, "sensorMaxWidth": 36.0},
            "sensitiveDetectorConfig": {
                "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 210.0},
                "shape": "circle",
                "diameterRule": "min(entranceDiameter,sensorMaxWidth)",
            },
        }

    def test_valid_minimal_optics(self) -> None:
        """Minimal valid optics configuration should validate."""
        optics = Optics.model_validate(self._minimal_optics_payload())
        assert len(optics.lenses) == 1
        assert optics.lenses[0].primary is True
        assert optics.geometry.entrance_diameter == 60.5
        assert optics.sensitive_detector_config.shape == "circle"

    def test_sensitive_detector_config_alias_variations(self) -> None:
        """All sensitive detector config aliases should be accepted."""
        base = self._minimal_optics_payload()

        # Test sensitiveDetectorConfig
        optics1 = Optics.model_validate(base)
        assert optics1.sensitive_detector_config.shape == "circle"

        # Test sensitiveDetector
        payload2 = base.copy()
        payload2["sensitiveDetector"] = payload2.pop("sensitiveDetectorConfig")
        optics2 = Optics.model_validate(payload2)
        assert optics2.sensitive_detector_config.shape == "circle"

        # Test sensitive_detector_config
        payload3 = base.copy()
        payload3["sensitive_detector_config"] = payload3.pop("sensitiveDetectorConfig")
        optics3 = Optics.model_validate(payload3)
        assert optics3.sensitive_detector_config.shape == "circle"

    def test_show_transport_progress_default(self) -> None:
        """show_transport_progress should default to True."""
        optics = Optics.model_validate(self._minimal_optics_payload())
        assert optics.show_transport_progress is True

    def test_show_transport_progress_explicit_false(self) -> None:
        """Explicitly setting show_transport_progress to False should work."""
        payload = self._minimal_optics_payload()
        payload["showTransportProgress"] = False
        optics = Optics.model_validate(payload)
        assert optics.show_transport_progress is False

    def test_show_transport_progress_alias_handling(self) -> None:
        """Both showTransportProgress and show_transport_progress should be accepted."""
        payload1 = self._minimal_optics_payload()
        payload1["showTransportProgress"] = False
        optics1 = Optics.model_validate(payload1)
        assert optics1.show_transport_progress is False

        payload2 = self._minimal_optics_payload()
        payload2["show_transport_progress"] = False
        optics2 = Optics.model_validate(payload2)
        assert optics2.show_transport_progress is False

    def test_transport_assumptions_default_factory(self) -> None:
        """transport_assumptions should use default factory if not provided."""
        optics = Optics.model_validate(self._minimal_optics_payload())
        assert optics.transport_assumptions.object_plane == "scintillator_back_face"
        assert (
            optics.transport_assumptions.optical_interface_represents
            == "lens_entrance_plane"
        )

    def test_transport_assumptions_explicit(self) -> None:
        """Explicit transport_assumptions should be accepted."""
        payload = self._minimal_optics_payload()
        payload["transportAssumptions"] = {
            "objectPlane": "scintillator_back_face",
            "opticalInterfaceRepresents": "lens_entrance_plane",
        }
        optics = Optics.model_validate(payload)
        assert optics.transport_assumptions.object_plane == "scintillator_back_face"

    def test_multiple_lenses_with_one_primary(self) -> None:
        """Multiple lenses with exactly one primary should validate."""
        payload = self._minimal_optics_payload()
        payload["lenses"] = [
            {"catalogId": "Lens1", "primary": True},
            {"catalogId": "Lens2", "primary": False},
            {"zmxFile": "lens3.zmx", "primary": False},
        ]
        optics = Optics.model_validate(payload)
        assert len(optics.lenses) == 3
        assert sum(1 for lens in optics.lenses if lens.primary) == 1

    def test_file_based_lens_specification(self) -> None:
        """Lens specified via zmxFile and smxFile should validate."""
        payload = self._minimal_optics_payload()
        payload["lenses"] = [
            {
                "zmxFile": "custom.zmx",
                "smxFile": "custom.smx",
                "primary": True,
                "description": "Custom lens design",
            }
        ]
        optics = Optics.model_validate(payload)
        assert optics.lenses[0].zmx_file == "custom.zmx"
        assert optics.lenses[0].smx_file == "custom.smx"

    def test_empty_lenses_list_rejected(self) -> None:
        """Empty lenses list should be rejected (min_length=1)."""
        payload = self._minimal_optics_payload()
        payload["lenses"] = []
        with pytest.raises(ValidationError, match="lenses"):
            Optics.model_validate(payload)

    def test_no_primary_lens_rejected(self) -> None:
        """Configuration without primary lens should be rejected."""
        payload = self._minimal_optics_payload()
        payload["lenses"] = [
            {"catalogId": "Lens1", "primary": False},
            {"catalogId": "Lens2", "primary": False},
        ]
        with pytest.raises(ValidationError, match="exactly one primary"):
            Optics.model_validate(payload)

    def test_multiple_primary_lenses_rejected(self) -> None:
        """Configuration with multiple primary lenses should be rejected."""
        payload = self._minimal_optics_payload()
        payload["lenses"] = [
            {"catalogId": "Lens1", "primary": True},
            {"catalogId": "Lens2", "primary": True},
        ]
        with pytest.raises(ValidationError, match="exactly one primary"):
            Optics.model_validate(payload)

    def test_serialization_uses_aliases(self) -> None:
        """Serialized output should use camelCase aliases."""
        optics = Optics.model_validate(self._minimal_optics_payload())
        dumped = optics.model_dump(by_alias=True)
        assert "sensitiveDetectorConfig" in dumped
        assert "showTransportProgress" in dumped
        assert "transportAssumptions" in dumped

    def test_complete_optics_configuration(self) -> None:
        """Complete optics configuration with all fields should validate."""
        payload = {
            "lenses": [
                {
                    "name": "Primary Lens",
                    "description": "Main imaging lens",
                    "catalogId": "CanonEF50mmf1.0L",
                    "primary": True,
                },
                {
                    "name": "Secondary Lens",
                    "description": "Field flattener",
                    "zmxFile": "flattener.zmx",
                    "smxFile": "flattener.smx",
                    "primary": False,
                },
            ],
            "geometry": {
                "entranceDiameter": 60.5,
                "sensorMaxWidth": 36.0,
            },
            "sensitiveDetectorConfig": {
                "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 210.05},
                "shape": "circle",
                "diameterRule": "min(entranceDiameter,sensorMaxWidth)",
            },
            "showTransportProgress": True,
            "transportAssumptions": {
                "objectPlane": "scintillator_back_face",
                "opticalInterfaceRepresents": "lens_entrance_plane",
            },
        }
        optics = Optics.model_validate(payload)
        assert len(optics.lenses) == 2
        assert optics.lenses[0].name == "Primary Lens"
        assert optics.lenses[1].zmx_file == "flattener.zmx"
        assert optics.geometry.entrance_diameter == 60.5
        assert optics.sensitive_detector_config.position_mm.x_mm == 0.0
        assert optics.sensitive_detector_config.position_mm.y_mm == 0.0
        assert optics.sensitive_detector_config.position_mm.z_mm == 210.05
        assert optics.show_transport_progress is True
        assert optics.transport_assumptions.object_plane == "scintillator_back_face"
