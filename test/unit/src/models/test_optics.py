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
    OpticalInterface,
    OpticalTransportAssumptions,
    Optics,
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
            back_focus_mm=24.3,
            back_focus_bounds_mm=(23.8, 24.8),
        )
        dumped = lens.model_dump(by_alias=True)
        assert "catalogId" in dumped
        assert "zmxFile" in dumped
        assert "smxFile" in dumped
        assert dumped["backFocusMm"] == 24.3
        assert dumped["backFocusBoundsMm"] == (23.8, 24.8)

    def test_back_focus_aliases_validate(self) -> None:
        """Back-focus values should accept their YAML aliases."""
        lens = Lens.model_validate(
            {
                "catalogId": "TestLens",
                "backFocusMm": 24.3,
                "backFocusBoundsMm": [23.8, 24.8],
            }
        )
        assert lens.back_focus_mm == 24.3
        assert lens.back_focus_bounds_mm == (23.8, 24.8)

    def test_back_focus_can_be_fixed(self) -> None:
        """A back-focus value without bounds represents fixed geometry."""
        lens = Lens(catalog_id="TestLens", back_focus_mm=24.3)
        assert lens.back_focus_mm == 24.3
        assert lens.back_focus_bounds_mm is None

    def test_back_focus_bounds_can_define_search_space(self) -> None:
        """Mechanical bounds may be supplied without an initial value."""
        lens = Lens(
            catalog_id="TestLens",
            back_focus_bounds_mm=(23.8, 24.8),
        )
        assert lens.back_focus_mm is None
        assert lens.back_focus_bounds_mm == (23.8, 24.8)

    @pytest.mark.parametrize(
        "bounds",
        [(-1.0, 20.0), (20.0, 0.0), (25.0, 20.0)],
    )
    def test_invalid_back_focus_bounds_rejected(
        self,
        bounds: tuple[float, float],
    ) -> None:
        """Back-focus bounds must be positive and ordered."""
        with pytest.raises(ValidationError, match="backFocusBoundsMm"):
            Lens(catalog_id="TestLens", back_focus_bounds_mm=bounds)

    def test_back_focus_outside_bounds_rejected(self) -> None:
        """The configured back focus must be mechanically attainable."""
        with pytest.raises(ValidationError, match="backFocusMm"):
            Lens(
                catalog_id="TestLens",
                back_focus_mm=25.0,
                back_focus_bounds_mm=(23.8, 24.8),
            )


# ============================================================================
# OpticalInterface Tests
# ============================================================================


class TestOpticalInterface:
    """Tests for optical interface (scoring plane) configuration."""

    def test_valid_interface_creation(self) -> None:
        """Valid interface with positive diameter and position should validate."""
        interface = OpticalInterface(
            diameter_mm=60.5,
            position_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 210.0},
        )
        assert interface.diameter_mm == 60.5
        assert interface.position_mm.x_mm == 0.0
        assert interface.position_mm.y_mm == 0.0
        assert interface.position_mm.z_mm == 210.0

    def test_alias_handling(self) -> None:
        """camelCase aliases should map to snake_case fields."""
        interface = OpticalInterface.model_validate(
            {
                "diameterMm": 50.0,
                "positionMm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 200.0},
            }
        )
        assert interface.diameter_mm == 50.0
        assert interface.position_mm.z_mm == 200.0

    def test_zero_diameter_rejected(self) -> None:
        """Zero diameter_mm should be rejected (gt=0 constraint)."""
        with pytest.raises(ValidationError, match="diameter_mm"):
            OpticalInterface(
                diameter_mm=0.0,
                position_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 210.0},
            )

    def test_negative_diameter_rejected(self) -> None:
        """Negative diameter_mm should be rejected."""
        with pytest.raises(ValidationError, match="diameter_mm"):
            OpticalInterface(
                diameter_mm=-10.0,
                position_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 210.0},
            )

    def test_very_small_positive_diameter_accepted(self) -> None:
        """Very small but positive diameter should be accepted."""
        interface = OpticalInterface(
            diameter_mm=0.001,
            position_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 210.0},
        )
        assert interface.diameter_mm == 0.001

    def test_serialization_uses_aliases(self) -> None:
        """Serialized output should use camelCase aliases."""
        interface = OpticalInterface(
            diameter_mm=60.5,
            position_mm={"x_mm": 0.0, "y_mm": 0.0, "z_mm": 210.0},
        )
        dumped = interface.model_dump(by_alias=True)
        assert "diameterMm" in dumped
        assert "positionMm" in dumped


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
            "interface": {
                "diameterMm": 60.5,
                "positionMm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 210.0},
            },
        }

    def test_valid_minimal_optics(self) -> None:
        """Minimal valid optics configuration should validate."""
        optics = Optics.model_validate(self._minimal_optics_payload())
        assert len(optics.lenses) == 1
        assert optics.lenses[0].primary is True
        assert optics.interface.diameter_mm == 60.5
        assert optics.interface.position_mm.z_mm == 210.0

    def test_optics_without_lenses_validates(self) -> None:
        """Optics without lenses (e.g., PMT-only setup) should validate."""
        payload = {
            "interface": {
                "diameterMm": 50.0,
                "positionMm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 100.0},
            },
        }
        optics = Optics.model_validate(payload)
        assert optics.lenses is None
        assert optics.interface.diameter_mm == 50.0

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

    def test_empty_lenses_list_treated_as_none(self) -> None:
        """Empty lenses list should be treated as None (no lenses)."""
        payload = self._minimal_optics_payload()
        payload["lenses"] = []
        optics = Optics.model_validate(payload)
        # Empty list is allowed now for PMT-only setups
        assert optics.lenses == []

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
        assert "interface" in dumped
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
            "interface": {
                "diameterMm": 60.5,
                "positionMm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 210.05},
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
        assert optics.interface.diameter_mm == 60.5
        assert optics.interface.position_mm.x_mm == 0.0
        assert optics.interface.position_mm.y_mm == 0.0
        assert optics.interface.position_mm.z_mm == 210.05
        assert optics.show_transport_progress is True
        assert optics.transport_assumptions.object_plane == "scintillator_back_face"
