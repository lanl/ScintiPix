"""Unit tests for source catalog loading."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import textwrap
import unittest


def _repo_root() -> Path:
    """Resolve repository root by searching parent directories."""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "src").is_dir() and (parent / "pixi.toml").is_file():
            return parent
    raise RuntimeError("Could not resolve repository root from test path.")


sys.path.insert(0, str(_repo_root()))


class SourceCatalogTests(unittest.TestCase):
    """Validate source catalog index/entry loading."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from src.config.SourceCatalog import available_sources, load_source
        except ModuleNotFoundError as exc:
            missing_name = (getattr(exc, "name", "") or "").lower()
            if "pydantic" in missing_name or "yaml" in missing_name:
                raise unittest.SkipTest(
                    f"Missing dependency for catalog tests: {exc}. "
                    "Run in the project environment (for example: pixi run test-python)."
                ) from exc
            raise

        cls._available_sources = staticmethod(available_sources)
        cls._load_source = staticmethod(load_source)

    def test_default_catalog_contains_ambe(self) -> None:
        """Catalog index should expose the bundled AmBe entry."""

        self.assertIn("AmBe", self._available_sources())

    def test_load_ambe_entry(self) -> None:
        """The AmBe entry should carry the intrinsic source parameters."""

        entry = self._load_source("AmBe")
        self.assertEqual(entry.kind, "radioactive-source")
        self.assertEqual(entry.particle, "neutron")
        self.assertEqual(entry.angular.type, "iso")
        self.assertEqual(entry.energy.type, "AmBe")
        self.assertIsNotNone(entry.correlated_gamma)
        self.assertAlmostEqual(entry.correlated_gamma.probability, 0.582)

    def test_default_load_returns_default_entry(self) -> None:
        """Loading with no id should return the catalog default entry."""

        entry = self._load_source()
        self.assertEqual(entry.particle, "neutron")
        self.assertEqual(entry.energy.type, "AmBe")

    def test_unknown_source_raises(self) -> None:
        """Requesting an unknown source id should raise KeyError."""

        with self.assertRaises(KeyError):
            self._load_source("does-not-exist")

    def test_temp_catalog_loads_beam_entry(self) -> None:
        """A custom catalog with a beam entry should load and apply defaults."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "catalog.yaml").write_text(
                textwrap.dedent(
                    """
                    version: 1
                    default: DTBeam
                    sources:
                      DTBeam:
                        kind: beam
                        particle: neutron
                        energy:
                          type: Mono
                          monoMeV: 14.1
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            entry = self._load_source("DTBeam", catalog_path=root / "catalog.yaml")
            self.assertEqual(entry.kind, "beam")
            self.assertEqual(entry.energy.mono_mev, 14.1)
            # Angular is not given, so the beam2d default applies.
            self.assertEqual(entry.angular.type, "beam2d")
            self.assertIsNone(entry.correlated_gamma)


if __name__ == "__main__":
    unittest.main()
