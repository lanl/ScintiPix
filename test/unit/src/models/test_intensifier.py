"""Comprehensive unit tests for intensifier configuration models."""

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

from src.models.intensifier import Intensifier, IntensifierInputScreen


# ============================================================================
# IntensifierInputScreen Tests
# ============================================================================


class TestIntensifierInputScreen:
    """Tests for intensifier input screen active area definition."""

    def test_valid_screen_creation(self) -> None:
        """Valid screen with required fields should validate."""
        screen = IntensifierInputScreen(image_circle_diameter_mm=18.0)
        assert screen.image_circle_diameter_mm == 18.0
        assert screen.center_mm == (0.0, 0.0)
        assert screen.magnification == 1.0
        assert screen.coordinate_frame == "intensifier_input_plane"

    def test_image_circle_diameter_mm_alias_handling(self) -> None:
        """camelCase imageCircleDiameterMm alias should map to image_circle_diameter_mm."""
        screen = IntensifierInputScreen.model_validate(
            {"imageCircleDiameterMm": 25.0}
        )
        assert screen.image_circle_diameter_mm == 25.0

    def test_center_mm_default(self) -> None:
        """center_mm should default to (0.0, 0.0)."""
        screen = IntensifierInputScreen(image_circle_diameter_mm=18.0)
        assert screen.center_mm == (0.0, 0.0)

    def test_center_mm_from_tuple(self) -> None:
        """center_mm should accept tuple input."""
        screen = IntensifierInputScreen(
            image_circle_diameter_mm=18.0,
            center_mm=(5.0, 10.0),
        )
        assert screen.center_mm == (5.0, 10.0)

    def test_center_mm_from_list(self) -> None:
        """center_mm should accept list input."""
        screen = IntensifierInputScreen.model_validate(
            {
                "image_circle_diameter_mm": 18.0,
                "center_mm": [3.0, 7.0],
            }
        )
        assert screen.center_mm == (3.0, 7.0)

    def test_center_mm_from_dict_with_x_mm_y_mm(self) -> None:
        """center_mm should accept dict with x_mm, y_mm keys."""
        screen = IntensifierInputScreen.model_validate(
            {
                "image_circle_diameter_mm": 18.0,
                "center_mm": {"x_mm": 2.0, "y_mm": 4.0},
            }
        )
        assert screen.center_mm == (2.0, 4.0)

    def test_center_mm_from_dict_with_x_y(self) -> None:
        """center_mm should accept dict with x, y keys."""
        screen = IntensifierInputScreen.model_validate(
            {
                "imageCircleDiameterMm": 18.0,
                "centerMm": {"x": 1.5, "y": 2.5},
            }
        )
        assert screen.center_mm == (1.5, 2.5)

    def test_center_mm_alias_handling(self) -> None:
        """camelCase centerMm alias should map to center_mm."""
        screen = IntensifierInputScreen.model_validate(
            {
                "imageCircleDiameterMm": 18.0,
                "centerMm": [1.0, 2.0],
            }
        )
        assert screen.center_mm == (1.0, 2.0)

    def test_center_mm_wrong_length_rejected(self) -> None:
        """center_mm with wrong length should be rejected."""
        with pytest.raises(ValidationError, match="exactly two values"):
            IntensifierInputScreen.model_validate(
                {
                    "image_circle_diameter_mm": 18.0,
                    "center_mm": [1.0, 2.0, 3.0],
                }
            )

    def test_center_mm_invalid_format_rejected(self) -> None:
        """center_mm with invalid format should be rejected."""
        with pytest.raises(ValidationError, match="center_mm"):
            IntensifierInputScreen.model_validate(
                {
                    "image_circle_diameter_mm": 18.0,
                    "center_mm": "invalid",
                }
            )

    def test_center_mm_none_becomes_default(self) -> None:
        """center_mm None should become default (0.0, 0.0)."""
        screen = IntensifierInputScreen.model_validate(
            {
                "image_circle_diameter_mm": 18.0,
                "center_mm": None,
            }
        )
        assert screen.center_mm == (0.0, 0.0)

    def test_magnification_default(self) -> None:
        """magnification should default to 1.0."""
        screen = IntensifierInputScreen(image_circle_diameter_mm=18.0)
        assert screen.magnification == 1.0

    def test_magnification_custom_value(self) -> None:
        """Custom magnification should be accepted."""
        screen = IntensifierInputScreen(
            image_circle_diameter_mm=18.0,
            magnification=1.5,
        )
        assert screen.magnification == 1.5

    def test_coordinate_frame_default(self) -> None:
        """coordinate_frame should default to 'intensifier_input_plane'."""
        screen = IntensifierInputScreen(image_circle_diameter_mm=18.0)
        assert screen.coordinate_frame == "intensifier_input_plane"

    def test_coordinate_frame_custom_value(self) -> None:
        """Custom coordinate_frame should be accepted."""
        screen = IntensifierInputScreen(
            image_circle_diameter_mm=18.0,
            coordinate_frame="custom_frame",
        )
        assert screen.coordinate_frame == "custom_frame"

    def test_coordinate_frame_alias_handling(self) -> None:
        """camelCase coordinateFrame alias should map to coordinate_frame."""
        screen = IntensifierInputScreen.model_validate(
            {
                "imageCircleDiameterMm": 18.0,
                "coordinateFrame": "test_frame",
            }
        )
        assert screen.coordinate_frame == "test_frame"

    def test_notes_field_optional(self) -> None:
        """notes field should be optional."""
        screen = IntensifierInputScreen(image_circle_diameter_mm=18.0)
        assert screen.notes is None

    def test_notes_field_accepts_string(self) -> None:
        """notes field should accept strings."""
        screen = IntensifierInputScreen(
            image_circle_diameter_mm=18.0,
            notes="Test notes",
        )
        assert screen.notes == "Test notes"

    def test_zero_image_circle_diameter_rejected(self) -> None:
        """Zero image_circle_diameter_mm should be rejected (gt=0)."""
        with pytest.raises(ValidationError, match="image_circle_diameter_mm"):
            IntensifierInputScreen(image_circle_diameter_mm=0.0)

    def test_negative_image_circle_diameter_rejected(self) -> None:
        """Negative image_circle_diameter_mm should be rejected."""
        with pytest.raises(ValidationError, match="image_circle_diameter_mm"):
            IntensifierInputScreen(image_circle_diameter_mm=-18.0)

    def test_zero_magnification_rejected(self) -> None:
        """Zero magnification should be rejected (gt=0)."""
        with pytest.raises(ValidationError, match="magnification"):
            IntensifierInputScreen(
                image_circle_diameter_mm=18.0,
                magnification=0.0,
            )

    def test_negative_magnification_rejected(self) -> None:
        """Negative magnification should be rejected."""
        with pytest.raises(ValidationError, match="magnification"):
            IntensifierInputScreen(
                image_circle_diameter_mm=18.0,
                magnification=-1.0,
            )

    def test_empty_coordinate_frame_rejected(self) -> None:
        """Empty coordinate_frame should be rejected (min_length=1)."""
        with pytest.raises(ValidationError, match="coordinate_frame"):
            IntensifierInputScreen(
                image_circle_diameter_mm=18.0,
                coordinate_frame="",
            )

    def test_negative_center_coordinates_accepted(self) -> None:
        """Negative center coordinates should be accepted."""
        screen = IntensifierInputScreen(
            image_circle_diameter_mm=18.0,
            center_mm=(-5.0, -10.0),
        )
        assert screen.center_mm == (-5.0, -10.0)

    def test_serialization_uses_snake_case(self) -> None:
        """Serialized output should use snake_case aliases."""
        screen = IntensifierInputScreen(
            image_circle_diameter_mm=18.0,
            center_mm=(1.0, 2.0),
            coordinate_frame="test",
        )
        dumped = screen.model_dump(by_alias=True)
        assert "image_circle_diameter_mm" in dumped
        assert "center_mm" in dumped
        assert "coordinate_frame" in dumped


# ============================================================================
# PhotocathodeStage Tests
# ============================================================================


class TestPhotocathodeStage:
    """Tests for photocathode response parameters."""

    def test_default_values(self) -> None:
        """Default QE curve and parameters should be set."""
        photocathode = Intensifier.PhotocathodeStage()
        assert photocathode.qe_wavelength_nm == [350.0, 500.0, 650.0]
        assert photocathode.qe_values == [0.15, 0.25, 0.05]
        assert photocathode.collection_efficiency == 1.0
        assert photocathode.tts_sigma_ns == 0.0

    def test_custom_qe_curve(self) -> None:
        """Custom QE wavelengths and values should be accepted."""
        photocathode = Intensifier.PhotocathodeStage(
            qe_wavelength_nm=[400.0, 500.0, 600.0],
            qe_values=[0.1, 0.3, 0.2],
        )
        assert photocathode.qe_wavelength_nm == [400.0, 500.0, 600.0]
        assert photocathode.qe_values == [0.1, 0.3, 0.2]

    def test_qe_wavelength_nm_alias_handling(self) -> None:
        """camelCase qeWavelengthNm alias should map to qe_wavelength_nm."""
        photocathode = Intensifier.PhotocathodeStage.model_validate(
            {
                "qeWavelengthNm": [350.0, 500.0],
                "qeValues": [0.2, 0.3],
            }
        )
        assert photocathode.qe_wavelength_nm == [350.0, 500.0]

    def test_qe_values_alias_handling(self) -> None:
        """camelCase qeValues alias should map to qe_values."""
        photocathode = Intensifier.PhotocathodeStage.model_validate(
            {
                "qe_wavelength_nm": [350.0, 500.0],
                "qeValues": [0.2, 0.3],
            }
        )
        assert photocathode.qe_values == [0.2, 0.3]

    def test_collection_efficiency_alias_handling(self) -> None:
        """camelCase collectionEfficiency alias should map to collection_efficiency."""
        photocathode = Intensifier.PhotocathodeStage.model_validate(
            {"collectionEfficiency": 0.8}
        )
        assert photocathode.collection_efficiency == 0.8

    def test_tts_sigma_ns_alias_handling(self) -> None:
        """camelCase ttsSigmaNs alias should map to tts_sigma_ns."""
        photocathode = Intensifier.PhotocathodeStage.model_validate(
            {"ttsSigmaNs": 0.5}
        )
        assert photocathode.tts_sigma_ns == 0.5

    def test_qe_tables_must_have_same_length(self) -> None:
        """qe_wavelength_nm and qe_values must have the same length."""
        with pytest.raises(ValidationError, match="same length"):
            Intensifier.PhotocathodeStage(
                qe_wavelength_nm=[350.0, 500.0, 650.0],
                qe_values=[0.1, 0.2],
            )

    def test_qe_wavelength_nm_must_be_monotonic_increasing(self) -> None:
        """qe_wavelength_nm must be monotonic increasing."""
        with pytest.raises(ValidationError, match="monotonic increasing"):
            Intensifier.PhotocathodeStage(
                qe_wavelength_nm=[500.0, 400.0, 600.0],
                qe_values=[0.1, 0.2, 0.3],
            )

    def test_qe_wavelength_nm_equal_consecutive_accepted(self) -> None:
        """Equal consecutive wavelengths are allowed (not strictly increasing)."""
        photocathode = Intensifier.PhotocathodeStage(
            qe_wavelength_nm=[400.0, 400.0, 500.0],
            qe_values=[0.1, 0.2, 0.3],
        )
        assert photocathode.qe_wavelength_nm == [400.0, 400.0, 500.0]

    def test_qe_values_must_be_in_range_0_to_1(self) -> None:
        """qe_values must lie in [0, 1]."""
        with pytest.raises(ValidationError, match="must lie in"):
            Intensifier.PhotocathodeStage(
                qe_wavelength_nm=[350.0, 500.0],
                qe_values=[0.1, 1.5],
            )

    def test_qe_values_negative_rejected(self) -> None:
        """Negative qe_values should be rejected."""
        with pytest.raises(ValidationError, match="must lie in"):
            Intensifier.PhotocathodeStage(
                qe_wavelength_nm=[350.0, 500.0],
                qe_values=[-0.1, 0.5],
            )

    def test_qe_values_boundary_values_accepted(self) -> None:
        """QE values of exactly 0.0 and 1.0 should be accepted."""
        photocathode = Intensifier.PhotocathodeStage(
            qe_wavelength_nm=[350.0, 500.0, 650.0],
            qe_values=[0.0, 1.0, 0.5],
        )
        assert photocathode.qe_values == [0.0, 1.0, 0.5]

    def test_collection_efficiency_range(self) -> None:
        """collection_efficiency must be in [0, 1]."""
        photocathode = Intensifier.PhotocathodeStage(collection_efficiency=0.5)
        assert photocathode.collection_efficiency == 0.5

        with pytest.raises(ValidationError, match="collection_efficiency"):
            Intensifier.PhotocathodeStage(collection_efficiency=-0.1)

        with pytest.raises(ValidationError, match="collection_efficiency"):
            Intensifier.PhotocathodeStage(collection_efficiency=1.5)

    def test_tts_sigma_ns_non_negative(self) -> None:
        """tts_sigma_ns must be non-negative (ge=0)."""
        photocathode = Intensifier.PhotocathodeStage(tts_sigma_ns=0.0)
        assert photocathode.tts_sigma_ns == 0.0

        photocathode2 = Intensifier.PhotocathodeStage(tts_sigma_ns=1.5)
        assert photocathode2.tts_sigma_ns == 1.5

        with pytest.raises(ValidationError, match="tts_sigma_ns"):
            Intensifier.PhotocathodeStage(tts_sigma_ns=-0.5)

    def test_empty_qe_tables_rejected(self) -> None:
        """Empty QE tables should be rejected (min_length=1)."""
        with pytest.raises(ValidationError, match="qe_wavelength_nm"):
            Intensifier.PhotocathodeStage(
                qe_wavelength_nm=[],
                qe_values=[],
            )

    def test_serialization_uses_snake_case(self) -> None:
        """Serialized output should use snake_case aliases."""
        photocathode = Intensifier.PhotocathodeStage()
        dumped = photocathode.model_dump(by_alias=True)
        assert "qe_wavelength_nm" in dumped
        assert "qe_values" in dumped
        assert "collection_efficiency" in dumped
        assert "tts_sigma_ns" in dumped


# ============================================================================
# McpStage Tests
# ============================================================================


class TestMcpStage:
    """Tests for MCP (microchannel plate) parameters."""

    def test_default_values(self) -> None:
        """Default MCP parameters should be set."""
        mcp = Intensifier.McpStage()
        assert mcp.stage1_mean_gain == 8.0
        assert mcp.stage1_gain_shape == 2.0
        assert mcp.stage2_mean_gain == 800.0
        assert mcp.stage2_gain_shape == 2.0
        assert mcp.gain_ref == 1000.0
        assert mcp.spread_sigma0_mm == 0.03
        assert mcp.spread_gain_exponent == 0.4

    def test_custom_values(self) -> None:
        """Custom MCP parameters should be accepted."""
        mcp = Intensifier.McpStage(
            stage1_mean_gain=10.0,
            stage1_gain_shape=3.0,
            stage2_mean_gain=1000.0,
            stage2_gain_shape=4.0,
            gain_ref=1200.0,
            spread_sigma0_mm=0.05,
            spread_gain_exponent=0.5,
        )
        assert mcp.stage1_mean_gain == 10.0
        assert mcp.stage2_mean_gain == 1000.0
        assert mcp.spread_gain_exponent == 0.5

    def test_stage1_mean_gain_alias_handling(self) -> None:
        """camelCase stage1MeanGain alias should map to stage1_mean_gain."""
        mcp = Intensifier.McpStage.model_validate({"stage1MeanGain": 12.0})
        assert mcp.stage1_mean_gain == 12.0

    def test_stage2_gain_shape_alias_handling(self) -> None:
        """camelCase stage2GainShape alias should map to stage2_gain_shape."""
        mcp = Intensifier.McpStage.model_validate({"stage2GainShape": 5.0})
        assert mcp.stage2_gain_shape == 5.0

    def test_gain_ref_alias_handling(self) -> None:
        """camelCase gainRef alias should map to gain_ref."""
        mcp = Intensifier.McpStage.model_validate({"gainRef": 1500.0})
        assert mcp.gain_ref == 1500.0

    def test_spread_sigma0_mm_alias_handling(self) -> None:
        """camelCase spreadSigma0Mm alias should map to spread_sigma0_mm."""
        mcp = Intensifier.McpStage.model_validate({"spreadSigma0Mm": 0.04})
        assert mcp.spread_sigma0_mm == 0.04

    def test_spread_gain_exponent_alias_handling(self) -> None:
        """camelCase spreadGainExponent alias should map to spread_gain_exponent."""
        mcp = Intensifier.McpStage.model_validate({"spreadGainExponent": 0.6})
        assert mcp.spread_gain_exponent == 0.6

    def test_positive_gain_constraints(self) -> None:
        """All gain parameters must be positive (gt=0)."""
        with pytest.raises(ValidationError, match="stage1_mean_gain"):
            Intensifier.McpStage(stage1_mean_gain=0.0)

        with pytest.raises(ValidationError, match="stage1_gain_shape"):
            Intensifier.McpStage(stage1_gain_shape=-1.0)

        with pytest.raises(ValidationError, match="stage2_mean_gain"):
            Intensifier.McpStage(stage2_mean_gain=0.0)

        with pytest.raises(ValidationError, match="stage2_gain_shape"):
            Intensifier.McpStage(stage2_gain_shape=-1.0)

        with pytest.raises(ValidationError, match="gain_ref"):
            Intensifier.McpStage(gain_ref=0.0)

    def test_spread_sigma0_mm_non_negative(self) -> None:
        """spread_sigma0_mm must be non-negative (ge=0)."""
        mcp = Intensifier.McpStage(spread_sigma0_mm=0.0)
        assert mcp.spread_sigma0_mm == 0.0

        with pytest.raises(ValidationError, match="spread_sigma0_mm"):
            Intensifier.McpStage(spread_sigma0_mm=-0.01)

    def test_spread_gain_exponent_accepts_negative(self) -> None:
        """spread_gain_exponent should accept negative values."""
        mcp = Intensifier.McpStage(spread_gain_exponent=-0.5)
        assert mcp.spread_gain_exponent == -0.5

    def test_serialization_uses_snake_case(self) -> None:
        """Serialized output should use snake_case aliases."""
        mcp = Intensifier.McpStage()
        dumped = mcp.model_dump(by_alias=True)
        assert "stage1_mean_gain" in dumped
        assert "stage1_gain_shape" in dumped
        assert "stage2_mean_gain" in dumped
        assert "stage2_gain_shape" in dumped
        assert "gain_ref" in dumped
        assert "spread_sigma0_mm" in dumped
        assert "spread_gain_exponent" in dumped


# ============================================================================
# PhosphorStage Tests
# ============================================================================


class TestPhosphorStage:
    """Tests for phosphor response parameters."""

    def test_default_values(self) -> None:
        """Default phosphor parameters should be set."""
        phosphor = Intensifier.PhosphorStage()
        assert phosphor.phosphor_gain == 1.0
        assert phosphor.decay_fast_ns == 70.0
        assert phosphor.decay_slow_ns == 200.0
        assert phosphor.fast_fraction == 0.9
        assert phosphor.psf_sigma_mm == 0.04

    def test_custom_values(self) -> None:
        """Custom phosphor parameters should be accepted."""
        phosphor = Intensifier.PhosphorStage(
            phosphor_gain=2.0,
            decay_fast_ns=50.0,
            decay_slow_ns=150.0,
            fast_fraction=0.8,
            psf_sigma_mm=0.05,
        )
        assert phosphor.phosphor_gain == 2.0
        assert phosphor.decay_fast_ns == 50.0
        assert phosphor.fast_fraction == 0.8

    def test_phosphor_gain_alias_handling(self) -> None:
        """camelCase phosphorGain alias should map to phosphor_gain."""
        phosphor = Intensifier.PhosphorStage.model_validate({"phosphorGain": 1.5})
        assert phosphor.phosphor_gain == 1.5

    def test_decay_fast_ns_alias_handling(self) -> None:
        """camelCase decayFastNs alias should map to decay_fast_ns."""
        phosphor = Intensifier.PhosphorStage.model_validate({"decayFastNs": 60.0})
        assert phosphor.decay_fast_ns == 60.0

    def test_decay_slow_ns_alias_handling(self) -> None:
        """camelCase decaySlowNs alias should map to decay_slow_ns."""
        phosphor = Intensifier.PhosphorStage.model_validate({"decaySlowNs": 180.0})
        assert phosphor.decay_slow_ns == 180.0

    def test_fast_fraction_alias_handling(self) -> None:
        """camelCase fastFraction alias should map to fast_fraction."""
        phosphor = Intensifier.PhosphorStage.model_validate({"fastFraction": 0.85})
        assert phosphor.fast_fraction == 0.85

    def test_psf_sigma_mm_alias_handling(self) -> None:
        """camelCase psfSigmaMm alias should map to psf_sigma_mm."""
        phosphor = Intensifier.PhosphorStage.model_validate({"psfSigmaMm": 0.06})
        assert phosphor.psf_sigma_mm == 0.06

    def test_phosphor_gain_positive(self) -> None:
        """phosphor_gain must be positive (gt=0)."""
        with pytest.raises(ValidationError, match="phosphor_gain"):
            Intensifier.PhosphorStage(phosphor_gain=0.0)

        with pytest.raises(ValidationError, match="phosphor_gain"):
            Intensifier.PhosphorStage(phosphor_gain=-1.0)

    def test_decay_times_non_negative(self) -> None:
        """Decay times must be non-negative (ge=0)."""
        phosphor = Intensifier.PhosphorStage(decay_fast_ns=0.0, decay_slow_ns=0.0)
        assert phosphor.decay_fast_ns == 0.0
        assert phosphor.decay_slow_ns == 0.0

        with pytest.raises(ValidationError, match="decay_fast_ns"):
            Intensifier.PhosphorStage(decay_fast_ns=-10.0)

        with pytest.raises(ValidationError, match="decay_slow_ns"):
            Intensifier.PhosphorStage(decay_slow_ns=-50.0)

    def test_fast_fraction_range(self) -> None:
        """fast_fraction must be in [0, 1]."""
        phosphor = Intensifier.PhosphorStage(fast_fraction=0.0)
        assert phosphor.fast_fraction == 0.0

        phosphor2 = Intensifier.PhosphorStage(fast_fraction=1.0)
        assert phosphor2.fast_fraction == 1.0

        with pytest.raises(ValidationError, match="fast_fraction"):
            Intensifier.PhosphorStage(fast_fraction=-0.1)

        with pytest.raises(ValidationError, match="fast_fraction"):
            Intensifier.PhosphorStage(fast_fraction=1.5)

    def test_psf_sigma_mm_non_negative(self) -> None:
        """psf_sigma_mm must be non-negative (ge=0)."""
        phosphor = Intensifier.PhosphorStage(psf_sigma_mm=0.0)
        assert phosphor.psf_sigma_mm == 0.0

        with pytest.raises(ValidationError, match="psf_sigma_mm"):
            Intensifier.PhosphorStage(psf_sigma_mm=-0.01)

    def test_serialization_uses_snake_case(self) -> None:
        """Serialized output should use snake_case aliases."""
        phosphor = Intensifier.PhosphorStage()
        dumped = phosphor.model_dump(by_alias=True)
        assert "phosphor_gain" in dumped
        assert "decay_fast_ns" in dumped
        assert "decay_slow_ns" in dumped
        assert "fast_fraction" in dumped
        assert "psf_sigma_mm" in dumped


# ============================================================================
# Intensifier Integration Tests
# ============================================================================


class TestIntensifier:
    """Tests for complete intensifier model."""

    @staticmethod
    def _minimal_intensifier_payload() -> dict:
        """Helper to create minimal valid intensifier payload."""
        return {
            "model": "Cricket2",
            "input_screen": {
                "image_circle_diameter_mm": 18.0,
            },
        }

    def test_valid_minimal_intensifier(self) -> None:
        """Minimal valid intensifier should validate."""
        intensifier = Intensifier.model_validate(self._minimal_intensifier_payload())
        assert intensifier.model == "Cricket2"
        assert intensifier.input_screen.image_circle_diameter_mm == 18.0
        assert intensifier.write_output_hdf5 is False

    def test_default_stage_factories(self) -> None:
        """Photocathode, MCP, and phosphor should use default factories."""
        intensifier = Intensifier.model_validate(self._minimal_intensifier_payload())
        assert intensifier.photocathode.collection_efficiency == 1.0
        assert intensifier.mcp.gain_ref == 1000.0
        assert intensifier.phosphor.decay_fast_ns == 70.0

    def test_input_screen_alias_handling(self) -> None:
        """camelCase inputScreen alias should map to input_screen."""
        payload = self._minimal_intensifier_payload()
        payload["inputScreen"] = payload.pop("input_screen")
        intensifier = Intensifier.model_validate(payload)
        assert intensifier.input_screen.image_circle_diameter_mm == 18.0

    def test_write_output_hdf5_alias_handling(self) -> None:
        """camelCase writeOutputHdf5 alias should map to write_output_hdf5."""
        payload = self._minimal_intensifier_payload()
        payload["writeOutputHdf5"] = True
        intensifier = Intensifier.model_validate(payload)
        assert intensifier.write_output_hdf5 is True

    def test_write_output_hdf5_default_false(self) -> None:
        """write_output_hdf5 should default to False."""
        intensifier = Intensifier.model_validate(self._minimal_intensifier_payload())
        assert intensifier.write_output_hdf5 is False

    def test_empty_model_name_rejected(self) -> None:
        """Empty model name should be rejected (min_length=1)."""
        payload = self._minimal_intensifier_payload()
        payload["model"] = ""
        with pytest.raises(ValidationError, match="model"):
            Intensifier.model_validate(payload)

    def test_explicit_photocathode_configuration(self) -> None:
        """Explicit photocathode configuration should be accepted."""
        payload = self._minimal_intensifier_payload()
        payload["photocathode"] = {
            "qe_wavelength_nm": [400.0, 550.0],
            "qe_values": [0.2, 0.3],
            "collection_efficiency": 0.9,
            "tts_sigma_ns": 0.5,
        }
        intensifier = Intensifier.model_validate(payload)
        assert intensifier.photocathode.qe_wavelength_nm == [400.0, 550.0]
        assert intensifier.photocathode.collection_efficiency == 0.9

    def test_explicit_mcp_configuration(self) -> None:
        """Explicit MCP configuration should be accepted."""
        payload = self._minimal_intensifier_payload()
        payload["mcp"] = {
            "stage1_mean_gain": 10.0,
            "stage2_mean_gain": 1000.0,
            "gain_ref": 1200.0,
        }
        intensifier = Intensifier.model_validate(payload)
        assert intensifier.mcp.stage1_mean_gain == 10.0
        assert intensifier.mcp.stage2_mean_gain == 1000.0

    def test_explicit_phosphor_configuration(self) -> None:
        """Explicit phosphor configuration should be accepted."""
        payload = self._minimal_intensifier_payload()
        payload["phosphor"] = {
            "phosphor_gain": 2.0,
            "decay_fast_ns": 60.0,
            "decay_slow_ns": 180.0,
            "fast_fraction": 0.85,
        }
        intensifier = Intensifier.model_validate(payload)
        assert intensifier.phosphor.phosphor_gain == 2.0
        assert intensifier.phosphor.fast_fraction == 0.85

    def test_complete_intensifier_configuration(self) -> None:
        """Complete intensifier with all fields should validate."""
        intensifier = Intensifier.model_validate(
            {
                "model": "Custom-Gen3",
                "write_output_hdf5": True,
                "input_screen": {
                    "image_circle_diameter_mm": 25.0,
                    "center_mm": [2.0, 3.0],
                    "magnification": 1.2,
                    "coordinate_frame": "custom_frame",
                    "notes": "Custom configuration",
                },
                "photocathode": {
                    "qe_wavelength_nm": [300.0, 450.0, 600.0, 750.0],
                    "qe_values": [0.1, 0.3, 0.25, 0.05],
                    "collection_efficiency": 0.95,
                    "tts_sigma_ns": 0.3,
                },
                "mcp": {
                    "stage1_mean_gain": 12.0,
                    "stage1_gain_shape": 3.0,
                    "stage2_mean_gain": 1200.0,
                    "stage2_gain_shape": 4.0,
                    "gain_ref": 1500.0,
                    "spread_sigma0_mm": 0.04,
                    "spread_gain_exponent": 0.45,
                },
                "phosphor": {
                    "phosphor_gain": 1.5,
                    "decay_fast_ns": 50.0,
                    "decay_slow_ns": 150.0,
                    "fast_fraction": 0.8,
                    "psf_sigma_mm": 0.05,
                },
            }
        )
        assert intensifier.model == "Custom-Gen3"
        assert intensifier.write_output_hdf5 is True
        assert intensifier.input_screen.magnification == 1.2
        assert intensifier.photocathode.collection_efficiency == 0.95
        assert intensifier.mcp.gain_ref == 1500.0
        assert intensifier.phosphor.phosphor_gain == 1.5

    def test_serialization_uses_snake_case(self) -> None:
        """Serialized output should use snake_case aliases."""
        intensifier = Intensifier.model_validate(self._minimal_intensifier_payload())
        dumped = intensifier.model_dump(by_alias=True)
        assert "write_output_hdf5" in dumped
        assert "input_screen" in dumped
