"""Regression checks for simulation-side scintillation material setup."""

from __future__ import annotations

from pathlib import Path
import unittest


def _repo_root() -> Path:
    """Resolve repository root by searching parent directories."""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (
            (parent / "pixi.toml").is_file()
            and (parent / "sim").is_dir()
            and (parent / "src").is_dir()
        ):
            return parent
    raise RuntimeError("Could not resolve repository root from test path.")


class DetectorConstructionSourceTests(unittest.TestCase):
    """Guard against dropping configured scintillation components in Geant4 setup."""

    def test_detector_construction_sets_all_scintillation_components(self) -> None:
        """Detector construction should forward all three timing components."""

        source = (_repo_root() / "sim" / "src" / "DetectorConstruction.cc").read_text(
            encoding="utf-8"
        )

        required_tokens = [
            '"SCINTILLATIONCOMPONENT1"',
            '"SCINTILLATIONCOMPONENT2"',
            '"SCINTILLATIONCOMPONENT3"',
            '"SCINTILLATIONTIMECONSTANT1"',
            '"SCINTILLATIONTIMECONSTANT2"',
            '"SCINTILLATIONTIMECONSTANT3"',
            '"SCINTILLATIONYIELD1"',
            '"SCINTILLATIONYIELD2"',
            '"SCINTILLATIONYIELD3"',
            "config->GetScintTimeConstant(componentIndex)",
            "config->GetScintYieldFraction(componentIndex)",
        ]

        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, source)

    def test_generic_composition_replaces_carbon_hydrogen_config(self) -> None:
        """Config and messenger should expose only generic composition controls."""

        root = _repo_root()
        config_header = (root / "sim" / "include" / "config.hh").read_text(
            encoding="utf-8"
        )
        messenger_source = (root / "sim" / "src" / "messenger.cc").read_text(
            encoding="utf-8"
        )

        self.assertIn("struct ScintillatorElementConfig", config_header)
        self.assertIn("struct ScintillatorIsotopeConfig", config_header)
        self.assertIn("GetScintElements()", config_header)
        self.assertIn("SetScintElements(", config_header)
        self.assertIn('"/scintillator/properties/elements"', messenger_source)
        self.assertIn('"/scintillator/properties/isotopes"', messenger_source)

        for removed_token in ("carbonAtoms", "hydrogenAtoms"):
            self.assertNotIn(removed_token, config_header)
            self.assertNotIn(removed_token, messenger_source)

    def test_enriched_isotopes_are_validated_before_construction(self) -> None:
        """Geant4 isotope records should be checked before they are constructed."""

        source = (_repo_root() / "sim" / "src" / "DetectorConstruction.cc").read_text(
            encoding="utf-8"
        )

        resolve_z = source.index("nist->GetZ(elementConfig.symbol)")
        validate_mass = source.index(
            "nist->GetIsotopeMass(atomicNumber, isotopeConfig.massNumber)"
        )
        construct_isotope = source.index("new G4Isotope")

        self.assertLess(resolve_z, validate_mass)
        self.assertLess(validate_mass, construct_isotope)


if __name__ == "__main__":
    unittest.main()
