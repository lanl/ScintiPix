"""Comprehensive unit tests for catalog index models."""

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

from src.models.catalogs import LensCatalogIndex, ScintillatorCatalogIndex


# ============================================================================
# LensCatalogIndex Tests
# ============================================================================


class TestLensCatalogIndex:
    """Tests for lens catalog index model."""

    @staticmethod
    def _minimal_lens_catalog_payload() -> dict:
        """Helper to create minimal valid lens catalog payload."""
        return {
            "version": 1,
            "default": "standard_lens",
            "lenses": {
                "standard_lens": {
                    "catalogId": "StandardLens",
                    "primary": True,
                },
            },
        }

    def test_valid_minimal_catalog(self) -> None:
        """Minimal valid lens catalog should validate."""
        catalog = LensCatalogIndex.model_validate(
            self._minimal_lens_catalog_payload()
        )
        assert catalog.version == 1
        assert catalog.default == "standard_lens"
        assert "standard_lens" in catalog.lenses

    def test_version_positive(self) -> None:
        """Version must be >= 1."""
        catalog = LensCatalogIndex.model_validate(
            self._minimal_lens_catalog_payload()
        )
        assert catalog.version == 1

        payload = self._minimal_lens_catalog_payload()
        payload["version"] = 10
        catalog2 = LensCatalogIndex.model_validate(payload)
        assert catalog2.version == 10

        with pytest.raises(ValidationError, match="version"):
            payload_invalid = self._minimal_lens_catalog_payload()
            payload_invalid["version"] = 0
            LensCatalogIndex.model_validate(payload_invalid)

    def test_empty_default_rejected(self) -> None:
        """Empty default string should be rejected (min_length=1)."""
        payload = self._minimal_lens_catalog_payload()
        payload["default"] = ""
        with pytest.raises(ValidationError, match="default"):
            LensCatalogIndex.model_validate(payload)

    def test_empty_lenses_dict_rejected(self) -> None:
        """Empty lenses dict should be rejected (min_length=1)."""
        payload = self._minimal_lens_catalog_payload()
        payload["lenses"] = {}
        with pytest.raises(ValidationError, match="lenses"):
            LensCatalogIndex.model_validate(payload)

    def test_default_must_exist_in_lenses(self) -> None:
        """Default key must exist in lenses mapping."""
        payload = self._minimal_lens_catalog_payload()
        payload["default"] = "nonexistent_lens"
        with pytest.raises(
            ValidationError,
            match="default 'nonexistent_lens' not found in lenses mapping",
        ):
            LensCatalogIndex.model_validate(payload)

    def test_multiple_lenses_in_catalog(self) -> None:
        """Multiple lenses in catalog should validate."""
        catalog = LensCatalogIndex.model_validate(
            {
                "version": 1,
                "default": "lens_a",
                "lenses": {
                    "lens_a": {"catalogId": "LensA", "primary": True},
                    "lens_b": {"catalogId": "LensB", "primary": False},
                    "lens_c": {"zmxFile": "lens_c.zmx", "primary": False},
                },
            }
        )
        assert len(catalog.lenses) == 3
        assert "lens_a" in catalog.lenses
        assert "lens_b" in catalog.lenses
        assert "lens_c" in catalog.lenses

    def test_lens_validation_applied(self) -> None:
        """Lens objects in catalog should be validated."""
        # Invalid lens (no catalogId or zmxFile)
        with pytest.raises(ValidationError, match="catalogId"):
            LensCatalogIndex.model_validate(
                {
                    "version": 1,
                    "default": "bad_lens",
                    "lenses": {
                        "bad_lens": {"primary": True},
                    },
                }
            )

    def test_lens_with_all_fields(self) -> None:
        """Lens with all fields should validate."""
        catalog = LensCatalogIndex.model_validate(
            {
                "version": 2,
                "default": "full_spec_lens",
                "lenses": {
                    "full_spec_lens": {
                        "name": "Full Specification Lens",
                        "description": "A lens with all fields",
                        "catalogId": "FullLens",
                        "zmxFile": "full.zmx",
                        "smxFile": "full.smx",
                        "primary": True,
                    },
                },
            }
        )
        lens = catalog.lenses["full_spec_lens"]
        assert lens.name == "Full Specification Lens"
        assert lens.description == "A lens with all fields"
        assert lens.catalog_id == "FullLens"

    def test_default_can_point_to_any_lens(self) -> None:
        """Default can point to any lens in the mapping."""
        # Default points to first lens
        catalog1 = LensCatalogIndex.model_validate(
            {
                "version": 1,
                "default": "lens_a",
                "lenses": {
                    "lens_a": {"catalogId": "LensA", "primary": True},
                    "lens_b": {"catalogId": "LensB", "primary": False},
                },
            }
        )
        assert catalog1.default == "lens_a"

        # Default points to second lens
        catalog2 = LensCatalogIndex.model_validate(
            {
                "version": 1,
                "default": "lens_b",
                "lenses": {
                    "lens_a": {"catalogId": "LensA", "primary": False},
                    "lens_b": {"catalogId": "LensB", "primary": True},
                },
            }
        )
        assert catalog2.default == "lens_b"

    def test_version_field_required(self) -> None:
        """Version field is required."""
        payload = self._minimal_lens_catalog_payload()
        del payload["version"]
        with pytest.raises(ValidationError, match="version"):
            LensCatalogIndex.model_validate(payload)

    def test_default_field_required(self) -> None:
        """Default field is required."""
        payload = self._minimal_lens_catalog_payload()
        del payload["default"]
        with pytest.raises(ValidationError, match="default"):
            LensCatalogIndex.model_validate(payload)

    def test_lenses_field_required(self) -> None:
        """Lenses field is required."""
        payload = self._minimal_lens_catalog_payload()
        del payload["lenses"]
        with pytest.raises(ValidationError, match="lenses"):
            LensCatalogIndex.model_validate(payload)


# ============================================================================
# ScintillatorCatalogIndex Tests
# ============================================================================


class TestScintillatorCatalogIndex:
    """Tests for scintillator catalog index model."""

    @staticmethod
    def _minimal_scintillator_catalog_payload() -> dict:
        """Helper to create minimal valid scintillator catalog payload."""
        return {
            "version": 1,
            "default": "basic_scintillator",
            "materials": {
                "basic_scintillator": {
                    "name": "BasicScintillator",
                    "photonEnergy": [2.0, 3.0, 4.0],
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
            },
        }

    def test_empty_default_rejected(self) -> None:
        """Empty default string should be rejected (min_length=1)."""
        payload = self._minimal_scintillator_catalog_payload()
        payload["default"] = ""
        with pytest.raises(ValidationError, match="default"):
            ScintillatorCatalogIndex.model_validate(payload)

    def test_empty_materials_dict_rejected(self) -> None:
        """Empty materials dict should be rejected (min_length=1)."""
        payload = self._minimal_scintillator_catalog_payload()
        payload["materials"] = {}
        with pytest.raises(ValidationError, match="materials"):
            ScintillatorCatalogIndex.model_validate(payload)

    def test_scintillator_properties_validation_applied(self) -> None:
        """ScintillatorProperties objects in catalog should be validated."""
        # Invalid properties (mismatched array lengths)
        with pytest.raises(ValidationError, match="nKEntries"):
            ScintillatorCatalogIndex.model_validate(
                {
                    "version": 1,
                    "default": "bad_material",
                    "materials": {
                        "bad_material": {
                            "name": "BadMaterial",
                            "photonEnergy": [2.0, 3.0, 4.0],
                            "rIndex": [1.5, 1.5],  # Wrong length
                            "nKEntries": 3,
                            "timeComponents": {
                                "default": [
                                    {"timeConstant": 1.0, "yieldFraction": 1.0},
                                    {"timeConstant": 0.0, "yieldFraction": 0.0},
                                    {"timeConstant": 0.0, "yieldFraction": 0.0},
                                ]
                            },
                        },
                    },
                }
            )

    def test_version_field_required(self) -> None:
        """Version field is required."""
        payload = self._minimal_scintillator_catalog_payload()
        del payload["version"]
        with pytest.raises(ValidationError, match="version"):
            ScintillatorCatalogIndex.model_validate(payload)

    def test_default_field_required(self) -> None:
        """Default field is required."""
        payload = self._minimal_scintillator_catalog_payload()
        del payload["default"]
        with pytest.raises(ValidationError, match="default"):
            ScintillatorCatalogIndex.model_validate(payload)

    def test_materials_field_required(self) -> None:
        """Materials field is required."""
        payload = self._minimal_scintillator_catalog_payload()
        del payload["materials"]
        with pytest.raises(ValidationError, match="materials"):
            ScintillatorCatalogIndex.model_validate(payload)
