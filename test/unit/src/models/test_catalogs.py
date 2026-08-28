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

from src.models.catalogs import (
    LensCatalogIndex,
    ScintillatorCatalogIndex,
    SourceCatalogEntry,
    SourceCatalogIndex,
)


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


# ============================================================================
# SourceCatalogEntry Tests
# ============================================================================


class TestSourceCatalogEntry:
    """Tests for a single source catalog entry."""

    @staticmethod
    def _minimal_entry_payload() -> dict:
        """Helper to create a minimal valid source entry payload."""
        return {
            "kind": "radioactive-source",
            "particle": "neutron",
            "energy": {"type": "AmBe"},
        }

    def test_valid_minimal_entry(self) -> None:
        """A minimal entry (kind, particle, energy) should validate."""
        entry = SourceCatalogEntry.model_validate(self._minimal_entry_payload())
        assert entry.kind == "radioactive-source"
        assert entry.particle == "neutron"
        assert entry.energy.type == "AmBe"
        assert entry.correlated_gamma is None

    def test_angular_default_factory(self) -> None:
        """Omitted angular should fall back to the beam2d default."""
        entry = SourceCatalogEntry.model_validate(self._minimal_entry_payload())
        assert entry.angular.type == "beam2d"

    def test_full_entry_with_aliases(self) -> None:
        """A full entry including camelCase correlatedGamma should validate."""
        entry = SourceCatalogEntry.model_validate(
            {
                "kind": "radioactive-source",
                "particle": "neutron",
                "angular": {"type": "iso"},
                "energy": {"type": "AmBe"},
                "correlatedGamma": {"probability": 0.582},
            }
        )
        assert entry.angular.type == "iso"
        assert entry.correlated_gamma is not None
        assert entry.correlated_gamma.probability == 0.582

    def test_empty_kind_rejected(self) -> None:
        """Empty kind string should be rejected (min_length=1)."""
        payload = self._minimal_entry_payload()
        payload["kind"] = ""
        with pytest.raises(ValidationError, match="kind"):
            SourceCatalogEntry.model_validate(payload)

    def test_empty_particle_rejected(self) -> None:
        """Empty particle string should be rejected (min_length=1)."""
        payload = self._minimal_entry_payload()
        payload["particle"] = ""
        with pytest.raises(ValidationError, match="particle"):
            SourceCatalogEntry.model_validate(payload)

    def test_energy_field_required(self) -> None:
        """Energy field is required."""
        payload = self._minimal_entry_payload()
        del payload["energy"]
        with pytest.raises(ValidationError, match="energy"):
            SourceCatalogEntry.model_validate(payload)

    def test_energy_validation_applied(self) -> None:
        """A Mono energy without monoMeV should be rejected by the entry."""
        payload = self._minimal_entry_payload()
        payload["energy"] = {"type": "Mono"}
        with pytest.raises(ValidationError, match="monoMeV"):
            SourceCatalogEntry.model_validate(payload)


# ============================================================================
# SourceCatalogIndex Tests
# ============================================================================


class TestSourceCatalogIndex:
    """Tests for the source catalog index model."""

    @staticmethod
    def _minimal_source_catalog_payload() -> dict:
        """Helper to create a minimal valid source catalog payload."""
        return {
            "version": 1,
            "default": "AmBe",
            "sources": {
                "AmBe": {
                    "kind": "radioactive-source",
                    "particle": "neutron",
                    "angular": {"type": "iso"},
                    "energy": {"type": "AmBe"},
                    "correlatedGamma": {"probability": 0.582},
                },
            },
        }

    def test_valid_minimal_catalog(self) -> None:
        """A minimal valid source catalog should validate."""
        catalog = SourceCatalogIndex.model_validate(
            self._minimal_source_catalog_payload()
        )
        assert catalog.version == 1
        assert catalog.default == "AmBe"
        assert "AmBe" in catalog.sources
        assert catalog.sources["AmBe"].particle == "neutron"

    def test_version_positive(self) -> None:
        """Version must be >= 1."""
        payload = self._minimal_source_catalog_payload()
        payload["version"] = 0
        with pytest.raises(ValidationError, match="version"):
            SourceCatalogIndex.model_validate(payload)

    def test_empty_default_rejected(self) -> None:
        """Empty default string should be rejected (min_length=1)."""
        payload = self._minimal_source_catalog_payload()
        payload["default"] = ""
        with pytest.raises(ValidationError, match="default"):
            SourceCatalogIndex.model_validate(payload)

    def test_empty_sources_dict_rejected(self) -> None:
        """Empty sources dict should be rejected (min_length=1)."""
        payload = self._minimal_source_catalog_payload()
        payload["sources"] = {}
        with pytest.raises(ValidationError, match="sources"):
            SourceCatalogIndex.model_validate(payload)

    def test_default_must_exist_in_sources(self) -> None:
        """Default key must exist in the sources mapping."""
        payload = self._minimal_source_catalog_payload()
        payload["default"] = "nonexistent_source"
        with pytest.raises(
            ValidationError,
            match="default 'nonexistent_source' not found in sources mapping",
        ):
            SourceCatalogIndex.model_validate(payload)

    def test_source_entry_validation_applied(self) -> None:
        """Entries in the catalog should be validated."""
        payload = self._minimal_source_catalog_payload()
        del payload["sources"]["AmBe"]["particle"]
        with pytest.raises(ValidationError, match="particle"):
            SourceCatalogIndex.model_validate(payload)

    def test_multiple_sources_in_catalog(self) -> None:
        """Multiple sources in the catalog should validate."""
        catalog = SourceCatalogIndex.model_validate(
            {
                "version": 1,
                "default": "AmBe",
                "sources": {
                    "AmBe": {
                        "kind": "radioactive-source",
                        "particle": "neutron",
                        "energy": {"type": "AmBe"},
                    },
                    "DTBeam": {
                        "kind": "beam",
                        "particle": "neutron",
                        "energy": {"type": "Mono", "monoMeV": 14.1},
                    },
                },
            }
        )
        assert len(catalog.sources) == 2
        assert catalog.sources["DTBeam"].kind == "beam"
        assert catalog.sources["DTBeam"].energy.mono_mev == 14.1

    def test_version_field_required(self) -> None:
        """Version field is required."""
        payload = self._minimal_source_catalog_payload()
        del payload["version"]
        with pytest.raises(ValidationError, match="version"):
            SourceCatalogIndex.model_validate(payload)

    def test_default_field_required(self) -> None:
        """Default field is required."""
        payload = self._minimal_source_catalog_payload()
        del payload["default"]
        with pytest.raises(ValidationError, match="default"):
            SourceCatalogIndex.model_validate(payload)

    def test_sources_field_required(self) -> None:
        """Sources field is required."""
        payload = self._minimal_source_catalog_payload()
        del payload["sources"]
        with pytest.raises(ValidationError, match="sources"):
            SourceCatalogIndex.model_validate(payload)
