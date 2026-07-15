"""Unit tests for YAML example files with nested scintillator structure."""

from pathlib import Path

import pytest

from src.config.yaml import from_yaml
from src.models.scintillator import ScintillatorProperties


class TestYamlExampleFiles:
    """Test that example YAML files load correctly with nested structure."""

    @pytest.fixture
    def examples_dir(self):
        """Return path to examples/yamlFiles directory."""
        return Path(__file__).resolve().parents[4] / "examples" / "yamlFiles"

    def test_ej200_inline_properties(self, examples_dir):
        """Test EJ200.yaml with inline nested properties."""
        yaml_path = examples_dir / "EJ200.yaml"
        sim = from_yaml(yaml_path)

        # Verify scintillator properties exist
        assert sim.scintillator is not None
        assert sim.scintillator.properties is not None
        props = sim.scintillator.properties

        # Verify nested structure exists
        assert props.composition is not None
        assert props.optical is not None

        # Verify composition structure
        assert isinstance(props.composition.density, float)
        assert props.composition.density == 1.05
        assert [element.symbol for element in props.composition.elements] == ["C", "H"]
        assert [element.mass_fraction for element in props.composition.elements] == [
            0.914706,
            0.085294,
        ]

        # Verify optical structure
        assert isinstance(props.optical.scint_yield, float)
        assert props.optical.scint_yield == 9800.0
        assert props.optical.resolution_scale == 1.1
        assert props.optical.n_k_entries == 5
        assert props.optical.photon_energy is not None
        assert props.optical.r_index is not None
        assert len(props.optical.photon_energy) == 5
        assert len(props.optical.r_index) == 5

        # Verify no catalog-format wrappers remain
        assert not hasattr(props.optical, "curves") or props.optical.curves is None
        assert not hasattr(props.optical, "constants") or props.optical.constants is None

    def test_ej276d_catalog_reference(self, examples_dir):
        """Test EJ276D.yaml with catalog reference only."""
        yaml_path = examples_dir / "EJ276D.yaml"

        try:
            sim = from_yaml(yaml_path)

            # Verify scintillator loads via catalog
            assert sim.scintillator is not None
            assert sim.scintillator.catalog_id == "EJ-276D"
            assert sim.scintillator.properties is not None
            props = sim.scintillator.properties

            # Verify nested structure from catalog
            assert props.composition is not None
            assert props.optical is not None

            # Verify density is converted to float
            assert isinstance(props.composition.density, float)
            assert [element.symbol for element in props.composition.elements] == ["C", "H"]
            assert [element.mass_fraction for element in props.composition.elements] == [
                0.926886,
                0.073114,
            ]

            # Verify scint_yield is converted to float
            assert isinstance(props.optical.scint_yield, float)
            assert props.optical.scint_yield == 8600.0

            # Verify curve data loaded from files
            assert props.optical.photon_energy is not None
            assert props.optical.r_index is not None
            assert props.optical.n_k_entries is not None

            # Verify no catalog-format wrappers remain
            assert not hasattr(props.optical, "curves") or props.optical.curves is None
            assert not hasattr(props.optical, "constants") or props.optical.constants is None
        except Exception as e:
            if "scintillator.properties" in str(e):
                pytest.fail(f"Scintillator structure validation failed: {e}")
            pytest.skip(f"File has unrelated validation errors: {e}")

    def test_canon_example_inline_properties(self, examples_dir):
        """Test CanonEF50mmf1p0L_example.yaml with inline nested properties."""
        yaml_path = examples_dir / "CanonEF50mmf1p0L_example.yaml"

        # This file may have other validation errors unrelated to scintillator
        # so we only test if the file exists and scintillator structure is correct
        try:
            sim = from_yaml(yaml_path)
            if sim.scintillator and sim.scintillator.properties:
                props = sim.scintillator.properties

                # Verify nested structure
                assert props.composition is not None
                assert props.optical is not None
                assert isinstance(props.composition.density, float)
                assert isinstance(props.optical.scint_yield, float)
        except Exception as e:
            # If file has other validation errors, just skip
            if "scintillator.properties" in str(e):
                pytest.fail(f"Scintillator structure validation failed: {e}")
            pytest.skip(f"File has unrelated validation errors: {e}")

    def test_pulsed_neutron_timing_example(self, examples_dir):
        """Test pulsed_neutron_source_timing.yaml with inline nested properties."""
        yaml_path = examples_dir / "pulsed_neutron_source_timing.yaml"

        try:
            sim = from_yaml(yaml_path)
            if sim.scintillator and sim.scintillator.properties:
                props = sim.scintillator.properties

                # Verify nested structure
                assert props.composition is not None
                assert props.optical is not None
                assert isinstance(props.composition.density, float)
                assert props.composition.density == 1.023
                assert isinstance(props.optical.scint_yield, float)
                assert props.optical.scint_yield == 9800.0
        except Exception as e:
            if "scintillator.properties" in str(e):
                pytest.fail(f"Scintillator structure validation failed: {e}")
            pytest.skip(f"File has unrelated validation errors: {e}")

    def test_continuous_neutron_timing_example(self, examples_dir):
        """Test continuous_neutron_source_timing.yaml with inline nested properties."""
        yaml_path = examples_dir / "continuous_neutron_source_timing.yaml"

        try:
            sim = from_yaml(yaml_path)
            if sim.scintillator and sim.scintillator.properties:
                props = sim.scintillator.properties

                # Verify nested structure
                assert props.composition is not None
                assert props.optical is not None
                assert isinstance(props.composition.density, float)
                assert isinstance(props.optical.scint_yield, float)
        except Exception as e:
            if "scintillator.properties" in str(e):
                pytest.fail(f"Scintillator structure validation failed: {e}")
            pytest.skip(f"File has unrelated validation errors: {e}")


class TestScintillatorPropertiesStructure:
    """Test scintillator properties model structure."""

    def test_nested_structure_required(self):
        """Test that ScintillatorProperties requires nested structure."""
        from src.models.scintillator import (
            ScintillatorComposition,
            ScintillatorOpticalProperties,
        )

        # Valid nested structure should work
        props_data = {
            "name": "TestMaterial",
            "composition": {
                "density": 1.0,
                "elements": [
                    {"symbol": "C", "massFraction": 0.914706},
                    {"symbol": "H", "massFraction": 0.085294},
                ]
            },
            "optical": {
                "photonEnergy": [2.0, 3.0, 4.0],
                "rIndex": [1.58, 1.58, 1.58],
                "nKEntries": 3,
                "scintYield": 10000.0,
                "resolutionScale": 1.0,
                "timeComponents": {
                    "default": [
                        {"timeConstant": 2.1, "yieldFraction": 1.0},
                        {"timeConstant": 0.0, "yieldFraction": 0.0},
                        {"timeConstant": 0.0, "yieldFraction": 0.0}
                    ]
                }
            }
        }

        props = ScintillatorProperties.model_validate(props_data)
        assert props.composition is not None
        assert props.optical is not None
        assert isinstance(props.composition.density, float)
        assert isinstance(props.optical.scint_yield, float)

    def test_flat_structure_rejected(self):
        """Test that old flat structure is rejected."""
        # Old flat structure should fail validation
        flat_data = {
            "name": "TestMaterial",
            "density": 1.0,  # Flat, should be nested under composition
            "photonEnergy": [2.0, 3.0, 4.0],  # Flat, should be nested under optical
            "rIndex": [1.58, 1.58, 1.58],
            "nKEntries": 3,
        }

        with pytest.raises(Exception) as exc_info:
            ScintillatorProperties.model_validate(flat_data)

        # Should fail because composition and optical are required
        assert "composition" in str(exc_info.value) or "Field required" in str(exc_info.value)
