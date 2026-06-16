"""Comprehensive unit tests for scintillator models."""

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

from src.models.scintillator import (
    Scintillator,
    ScintillationTimeComponent,
    ScintillationTimeComponentsByExcitation,
    ScintillatorProperties,
)


# ============================================================================
# ScintillationTimeComponent Tests
# ============================================================================


class TestScintillationTimeComponent:
    """Tests for individual scintillation time components."""

    def test_valid_component_creation(self) -> None:
        """Valid component should parse with both inline and alias keys."""
        component = ScintillationTimeComponent(
            time_constant=2.1,
            yield_fraction=1.0,
        )
        assert component.time_constant == 2.1
        assert component.yield_fraction == 1.0

    def test_alias_handling(self) -> None:
        """camelCase aliases should map to snake_case fields."""
        component = ScintillationTimeComponent.model_validate(
            {"timeConstant": 3.5, "yieldFraction": 0.75}
        )
        assert component.time_constant == 3.5
        assert component.yield_fraction == 0.75

    def test_negative_time_constant_rejected(self) -> None:
        """Negative time constants should be rejected."""
        with pytest.raises(ValidationError, match="time_constant"):
            ScintillationTimeComponent(time_constant=-1.0, yield_fraction=1.0)

    def test_negative_yield_fraction_rejected(self) -> None:
        """Negative yield fractions should be rejected."""
        with pytest.raises(ValidationError, match="yield_fraction"):
            ScintillationTimeComponent(time_constant=2.0, yield_fraction=-0.1)

    def test_zero_values_accepted(self) -> None:
        """Zero values should be accepted (inactive components)."""
        component = ScintillationTimeComponent(time_constant=0.0, yield_fraction=0.0)
        assert component.time_constant == 0.0
        assert component.yield_fraction == 0.0


# ============================================================================
# ScintillationTimeComponentsByExcitation Tests
# ============================================================================


class TestScintillationTimeComponentsByExcitation:
    """Tests for particle-keyed scintillation profiles."""

    @staticmethod
    def _valid_profile() -> list[dict[str, float]]:
        """Helper to create a valid 3-component profile."""
        return [
            {"timeConstant": 2.1, "yieldFraction": 1.0},
            {"timeConstant": 0.0, "yieldFraction": 0.0},
            {"timeConstant": 0.0, "yieldFraction": 0.0},
        ]

    @staticmethod
    def _multi_component_profile() -> list[dict[str, float]]:
        """Helper to create a valid multi-component profile."""
        return [
            {"timeConstant": 2.1, "yieldFraction": 0.7},
            {"timeConstant": 10.0, "yieldFraction": 0.2},
            {"timeConstant": 45.0, "yieldFraction": 0.1},
        ]

    def test_valid_default_profile(self) -> None:
        """Single default profile should validate."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {"default": self._valid_profile()}
        )
        assert profiles.default is not None
        assert len(profiles.default) == 3
        assert profiles.neutron is None
        assert profiles.gamma is None

    def test_valid_neutron_and_gamma_profiles(self) -> None:
        """Multiple profiles should validate."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {
                "neutron": self._multi_component_profile(),
                "gamma": self._valid_profile(),
            }
        )
        assert profiles.neutron is not None
        assert profiles.gamma is not None
        assert profiles.default is None

    def test_all_three_profiles(self) -> None:
        """All three profiles can be provided simultaneously."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {
                "default": self._valid_profile(),
                "neutron": self._multi_component_profile(),
                "gamma": self._valid_profile(),
            }
        )
        assert profiles.default is not None
        assert profiles.neutron is not None
        assert profiles.gamma is not None

    def test_empty_profiles_rejected(self) -> None:
        """At least one profile must be provided."""
        with pytest.raises(ValidationError, match="at least one profile"):
            ScintillationTimeComponentsByExcitation.model_validate({})

    def test_profile_requires_exactly_three_components(self) -> None:
        """Profiles with != 3 components should be rejected."""
        with pytest.raises(ValidationError, match="exactly 3 components"):
            ScintillationTimeComponentsByExcitation.model_validate(
                {
                    "default": [
                        {"timeConstant": 2.1, "yieldFraction": 1.0},
                        {"timeConstant": 0.0, "yieldFraction": 0.0},
                    ]
                }
            )

    def test_yield_fractions_must_sum_to_one(self) -> None:
        """Yield fractions must sum to ~1.0."""
        with pytest.raises(ValidationError, match="sum to ~1.0"):
            ScintillationTimeComponentsByExcitation.model_validate(
                {
                    "default": [
                        {"timeConstant": 2.1, "yieldFraction": 0.5},
                        {"timeConstant": 0.0, "yieldFraction": 0.0},
                        {"timeConstant": 0.0, "yieldFraction": 0.0},
                    ]
                }
            )

    def test_at_least_one_active_component_required(self) -> None:
        """At least one component must be active (yield > 0 and time > 0)."""
        with pytest.raises(ValidationError, match="at least one active"):
            ScintillationTimeComponentsByExcitation.model_validate(
                {
                    "default": [
                        {"timeConstant": 0.0, "yieldFraction": 1.0},
                        {"timeConstant": 0.0, "yieldFraction": 0.0},
                        {"timeConstant": 0.0, "yieldFraction": 0.0},
                    ]
                }
            )

    def test_resolve_for_particle_neutron_direct_match(self) -> None:
        """Neutron particle should match neutron profile."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {
                "neutron": self._multi_component_profile(),
                "gamma": self._valid_profile(),
            }
        )
        profile_name, components = profiles.resolve_for_particle("neutron")
        assert profile_name == "neutron"
        assert len(components) == 3
        assert components[0].time_constant == 2.1

    def test_resolve_for_particle_neutron_alias(self) -> None:
        """'n' should match neutron profile."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {"neutron": self._valid_profile()}
        )
        profile_name, components = profiles.resolve_for_particle("n")
        assert profile_name == "neutron"

    def test_resolve_for_particle_gamma_direct_match(self) -> None:
        """Gamma particle should match gamma profile."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {
                "neutron": self._multi_component_profile(),
                "gamma": self._valid_profile(),
            }
        )
        profile_name, components = profiles.resolve_for_particle("gamma")
        assert profile_name == "gamma"
        assert len(components) == 3

    def test_resolve_for_particle_gamma_alias(self) -> None:
        """'g' should match gamma profile."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {"gamma": self._valid_profile()}
        )
        profile_name, components = profiles.resolve_for_particle("g")
        assert profile_name == "gamma"

    def test_resolve_for_particle_case_insensitive(self) -> None:
        """Particle names should be case-insensitive."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {"neutron": self._valid_profile()}
        )
        profile_name, _ = profiles.resolve_for_particle("NEUTRON")
        assert profile_name == "neutron"

        profile_name, _ = profiles.resolve_for_particle("N")
        assert profile_name == "neutron"

    def test_resolve_for_particle_whitespace_trimmed(self) -> None:
        """Particle names should have whitespace trimmed."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {"gamma": self._valid_profile()}
        )
        profile_name, _ = profiles.resolve_for_particle("  gamma  ")
        assert profile_name == "gamma"

    def test_resolve_for_particle_fallback_to_default(self) -> None:
        """Unknown particle should fall back to default profile."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {
                "default": self._valid_profile(),
                "neutron": self._multi_component_profile(),
            }
        )
        profile_name, components = profiles.resolve_for_particle("alpha")
        assert profile_name == "default"

    def test_resolve_for_particle_single_profile_fallback(self) -> None:
        """With no default and one profile, should fall back to that profile."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {"neutron": self._valid_profile()}
        )
        profile_name, components = profiles.resolve_for_particle("gamma")
        assert profile_name == "neutron"

    def test_resolve_for_particle_no_match_multiple_profiles_raises(self) -> None:
        """Unknown particle with multiple profiles and no default should raise."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {
                "neutron": self._valid_profile(),
                "gamma": self._valid_profile(),
            }
        )
        with pytest.raises(ValueError, match="Could not resolve"):
            profiles.resolve_for_particle("alpha")

    def test_resolve_for_particle_neutron_prefers_neutron_over_default(self) -> None:
        """Neutron particle should prefer neutron profile over default."""
        profiles = ScintillationTimeComponentsByExcitation.model_validate(
            {
                "default": self._valid_profile(),
                "neutron": self._multi_component_profile(),
            }
        )
        profile_name, components = profiles.resolve_for_particle("neutron")
        assert profile_name == "neutron"
        assert components[0].time_constant == 2.1  # multi_component profile


# ============================================================================
# ScintillatorProperties Tests
# ============================================================================


class TestScintillatorProperties:
    """Tests for scintillator optical properties."""

    @staticmethod
    def _valid_time_components() -> dict[str, object]:
        """Helper for valid time components."""
        return {
            "default": [
                {"timeConstant": 2.1, "yieldFraction": 1.0},
                {"timeConstant": 0.0, "yieldFraction": 0.0},
                {"timeConstant": 0.0, "yieldFraction": 0.0},
            ]
        }

    def test_valid_inline_optical_curves(self) -> None:
        """Inline optical curves with shared photonEnergy grid should validate."""
        props = ScintillatorProperties.model_validate(
            {
                "name": "TestScint",
                "photonEnergy": [2.0, 2.4, 2.8],
                "rIndex": [1.58, 1.58, 1.58],
                "absLength": [100.0, 100.0, 100.0],
                "scintSpectrum": [0.1, 0.8, 0.1],
                "nKEntries": 3,
                "timeComponents": self._valid_time_components(),
            }
        )
        assert props.name == "TestScint"
        assert props.photon_energy == [2.0, 2.4, 2.8]
        assert props.r_index == [1.58, 1.58, 1.58]
        assert props.abs_length == [100.0, 100.0, 100.0]
        assert props.scint_spectrum == [0.1, 0.8, 0.1]
        assert props.n_k_entries == 3

    def test_valid_file_backed_curves(self) -> None:
        """File-backed curves without inline arrays should validate."""
        props = ScintillatorProperties.model_validate(
            {
                "name": "TestScint",
                "rIndexFile": "curves/test/rindex.csv",
                "absLengthFile": "curves/test/abs.csv",
                "scintSpectrumFile": "curves/test/scint.csv",
                "timeComponents": self._valid_time_components(),
            }
        )
        assert props.r_index_file == "curves/test/rindex.csv"
        assert props.abs_length_file == "curves/test/abs.csv"
        assert props.scint_spectrum_file == "curves/test/scint.csv"
        assert props.photon_energy is None
        assert props.n_k_entries is None

    def test_rindex_and_rindex_file_mutually_exclusive(self) -> None:
        """Cannot provide both rIndex and rIndexFile."""
        with pytest.raises(ValidationError, match="rIndex.*rIndexFile"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "photonEnergy": [2.0, 2.4, 2.8],
                    "rIndex": [1.58, 1.58, 1.58],
                    "rIndexFile": "curves/test/rindex.csv",
                    "nKEntries": 3,
                    "timeComponents": self._valid_time_components(),
                }
            )

    def test_abs_length_and_abs_length_file_mutually_exclusive(self) -> None:
        """Cannot provide both absLength and absLengthFile."""
        with pytest.raises(ValidationError, match="absLength.*absLengthFile"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "photonEnergy": [2.0, 2.4, 2.8],
                    "rIndex": [1.58, 1.58, 1.58],
                    "absLength": [100.0, 100.0, 100.0],
                    "absLengthFile": "curves/test/abs.csv",
                    "nKEntries": 3,
                    "timeComponents": self._valid_time_components(),
                }
            )

    def test_scint_spectrum_and_scint_spectrum_file_mutually_exclusive(self) -> None:
        """Cannot provide both scintSpectrum and scintSpectrumFile."""
        with pytest.raises(ValidationError, match="scintSpectrum.*scintSpectrumFile"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "photonEnergy": [2.0, 2.4, 2.8],
                    "rIndex": [1.58, 1.58, 1.58],
                    "scintSpectrum": [0.1, 0.8, 0.1],
                    "scintSpectrumFile": "curves/test/scint.csv",
                    "nKEntries": 3,
                    "timeComponents": self._valid_time_components(),
                }
            )

    def test_missing_rindex_and_rindex_file_raises(self) -> None:
        """Must provide either rIndex or rIndexFile."""
        with pytest.raises(ValidationError, match="rIndex.*rIndexFile.*must be provided"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "timeComponents": self._valid_time_components(),
                }
            )

    def test_inline_curves_require_photon_energy(self) -> None:
        """Inline curves require photonEnergy to be provided."""
        with pytest.raises(ValidationError, match="photonEnergy.*required"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "rIndex": [1.58, 1.58, 1.58],
                    "nKEntries": 3,
                    "timeComponents": self._valid_time_components(),
                }
            )

    def test_inline_curves_require_nk_entries(self) -> None:
        """Inline curves require nKEntries to be provided."""
        with pytest.raises(ValidationError, match="nKEntries.*required"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "photonEnergy": [2.0, 2.4, 2.8],
                    "rIndex": [1.58, 1.58, 1.58],
                    "timeComponents": self._valid_time_components(),
                }
            )

    def test_photon_energy_length_must_match_nk_entries(self) -> None:
        """photonEnergy length must equal nKEntries."""
        with pytest.raises(ValidationError, match="photonEnergy.*must match"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "photonEnergy": [2.0, 2.4],
                    "rIndex": [1.58, 1.58, 1.58],
                    "nKEntries": 3,
                    "timeComponents": self._valid_time_components(),
                }
            )

    def test_rindex_length_must_match_nk_entries(self) -> None:
        """rIndex length must equal nKEntries."""
        with pytest.raises(ValidationError, match="rIndex.*must match"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "photonEnergy": [2.0, 2.4, 2.8],
                    "rIndex": [1.58, 1.58],
                    "nKEntries": 3,
                    "timeComponents": self._valid_time_components(),
                }
            )

    def test_abs_length_length_must_match_nk_entries(self) -> None:
        """absLength length must equal nKEntries."""
        with pytest.raises(ValidationError, match="absLength.*must match"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "photonEnergy": [2.0, 2.4, 2.8],
                    "rIndex": [1.58, 1.58, 1.58],
                    "absLength": [100.0, 100.0],
                    "nKEntries": 3,
                    "timeComponents": self._valid_time_components(),
                }
            )

    def test_scint_spectrum_length_must_match_nk_entries(self) -> None:
        """scintSpectrum length must equal nKEntries."""
        with pytest.raises(ValidationError, match="scintSpectrum.*must match"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "photonEnergy": [2.0, 2.4, 2.8],
                    "rIndex": [1.58, 1.58, 1.58],
                    "scintSpectrum": [0.1, 0.8],
                    "nKEntries": 3,
                    "timeComponents": self._valid_time_components(),
                }
            )

    def test_optional_field_density_positive(self) -> None:
        """density must be > 0 if provided."""
        with pytest.raises(ValidationError, match="density"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "rIndexFile": "curves/test/rindex.csv",
                    "timeComponents": self._valid_time_components(),
                    "density": -1.0,
                }
            )

    def test_optional_field_carbon_atoms_positive(self) -> None:
        """carbonAtoms must be > 0 if provided."""
        with pytest.raises(ValidationError, match="carbonAtoms"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "rIndexFile": "curves/test/rindex.csv",
                    "timeComponents": self._valid_time_components(),
                    "carbonAtoms": -5,
                }
            )

    def test_optional_field_hydrogen_atoms_positive(self) -> None:
        """hydrogenAtoms must be > 0 if provided."""
        with pytest.raises(ValidationError, match="hydrogenAtoms"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "rIndexFile": "curves/test/rindex.csv",
                    "timeComponents": self._valid_time_components(),
                    "hydrogenAtoms": 0,
                }
            )

    def test_optional_field_scint_yield_positive(self) -> None:
        """scintYield must be > 0 if provided."""
        with pytest.raises(ValidationError, match="scintYield"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "rIndexFile": "curves/test/rindex.csv",
                    "timeComponents": self._valid_time_components(),
                    "scintYield": 0.0,
                }
            )

    def test_optional_field_resolution_scale_positive(self) -> None:
        """resolutionScale must be > 0 if provided."""
        with pytest.raises(ValidationError, match="resolutionScale"):
            ScintillatorProperties.model_validate(
                {
                    "name": "TestScint",
                    "rIndexFile": "curves/test/rindex.csv",
                    "timeComponents": self._valid_time_components(),
                    "resolutionScale": -0.5,
                }
            )

    def test_optional_fields_accepted_when_valid(self) -> None:
        """Optional fields should be accepted when valid."""
        props = ScintillatorProperties.model_validate(
            {
                "name": "TestScint",
                "rIndexFile": "curves/test/rindex.csv",
                "timeComponents": self._valid_time_components(),
                "density": 1.032,
                "carbonAtoms": 9,
                "hydrogenAtoms": 10,
                "scintYield": 10000.0,
                "resolutionScale": 1.0,
            }
        )
        assert props.density == 1.032
        assert props.carbon_atoms == 9
        assert props.hydrogen_atoms == 10
        assert props.scint_yield == 10000.0
        assert props.resolution_scale == 1.0


# ============================================================================
# Scintillator Tests
# ============================================================================


class TestScintillator:
    """Tests for the top-level Scintillator model."""

    @staticmethod
    def _valid_properties() -> dict[str, object]:
        """Helper for valid inline properties."""
        return {
            "name": "TestScint",
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
        }

    def test_valid_with_catalog_id_only(self) -> None:
        """Scintillator with only catalogId should validate."""
        scint = Scintillator.model_validate(
            {
                "catalogId": "EJ200",
                "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                "dimension_mm": {"x_mm": 50.0, "y_mm": 50.0, "z_mm": 10.0},
            }
        )
        assert scint.catalog_id == "EJ200"
        assert scint.properties is None

    def test_valid_with_properties_only(self) -> None:
        """Scintillator with only properties should validate."""
        scint = Scintillator.model_validate(
            {
                "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                "dimension_mm": {"x_mm": 50.0, "y_mm": 50.0, "z_mm": 10.0},
                "properties": self._valid_properties(),
            }
        )
        assert scint.catalog_id is None
        assert scint.properties is not None
        assert scint.properties.name == "TestScint"

    def test_valid_with_both_catalog_id_and_properties(self) -> None:
        """Scintillator with both catalogId and properties should validate."""
        scint = Scintillator.model_validate(
            {
                "catalogId": "EJ200",
                "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                "dimension_mm": {"x_mm": 50.0, "y_mm": 50.0, "z_mm": 10.0},
                "properties": self._valid_properties(),
            }
        )
        assert scint.catalog_id == "EJ200"
        assert scint.properties is not None

    def test_missing_both_catalog_id_and_properties_raises(self) -> None:
        """Scintillator without catalogId or properties should be rejected."""
        with pytest.raises(
            ValidationError, match="properties.*catalogId"
        ):
            Scintillator.model_validate(
                {
                    "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                    "dimension_mm": {"x_mm": 50.0, "y_mm": 50.0, "z_mm": 10.0},
                }
            )

    def test_mask_radius_alias_maskRadius(self) -> None:
        """maskRadius alias should map to mask_radius_mm."""
        scint = Scintillator.model_validate(
            {
                "catalogId": "EJ200",
                "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                "dimension_mm": {"x_mm": 50.0, "y_mm": 50.0, "z_mm": 10.0},
                "maskRadius": 12.5,
            }
        )
        assert scint.mask_radius_mm == 12.5

    def test_mask_radius_alias_maskRadiusMm(self) -> None:
        """maskRadiusMm alias should map to mask_radius_mm."""
        scint = Scintillator.model_validate(
            {
                "catalogId": "EJ200",
                "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                "dimension_mm": {"x_mm": 50.0, "y_mm": 50.0, "z_mm": 10.0},
                "maskRadiusMm": 15.0,
            }
        )
        assert scint.mask_radius_mm == 15.0

    def test_mask_radius_negative_rejected(self) -> None:
        """Negative mask_radius_mm should be rejected."""
        with pytest.raises(ValidationError, match="maskRadius"):
            Scintillator.model_validate(
                {
                    "catalogId": "EJ200",
                    "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                    "dimension_mm": {"x_mm": 50.0, "y_mm": 50.0, "z_mm": 10.0},
                    "maskRadius": -5.0,
                }
            )

    def test_mask_radius_default_zero(self) -> None:
        """mask_radius_mm should default to 0.0."""
        scint = Scintillator.model_validate(
            {
                "catalogId": "EJ200",
                "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                "dimension_mm": {"x_mm": 50.0, "y_mm": 50.0, "z_mm": 10.0},
            }
        )
        assert scint.mask_radius_mm == 0.0

    def test_serialization_alias_maskRadius(self) -> None:
        """Serialization should use 'maskRadius' as the alias."""
        scint = Scintillator.model_validate(
            {
                "catalogId": "EJ200",
                "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                "dimension_mm": {"x_mm": 50.0, "y_mm": 50.0, "z_mm": 10.0},
                "maskRadius": 10.0,
            }
        )
        dumped = scint.model_dump(by_alias=True)
        assert "maskRadius" in dumped
        assert dumped["maskRadius"] == 10.0

    def test_catalog_id_min_length_validation(self) -> None:
        """catalogId must have at least one non-whitespace character."""
        with pytest.raises(ValidationError, match="catalogId"):
            Scintillator.model_validate(
                {
                    "catalogId": "",
                    "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
                    "dimension_mm": {"x_mm": 50.0, "y_mm": 50.0, "z_mm": 10.0},
                }
            )
