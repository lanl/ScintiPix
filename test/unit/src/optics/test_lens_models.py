"""Unit tests for bundled lens model path resolution."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


def _repo_root() -> Path:
    """Resolve repository root by searching parent directories."""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "src").is_dir() and (parent / "pixi.toml").is_file():
            return parent
    raise RuntimeError("Could not resolve repository root from test path.")


sys.path.insert(0, str(_repo_root()))


class LensModelPathTests(unittest.TestCase):
    """Validate default bundled lens asset lookup."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from src.optics.LensModels import resolve_lens_path, resolve_smx_path
        except ModuleNotFoundError as exc:
            missing = (getattr(exc, "name", "") or "").lower()
            if missing in {"numpy", "pandas"}:
                raise unittest.SkipTest(
                    f"Missing dependency for lens-model tests: {exc}. "
                    "Run in the project environment (for example: pixi run pytest)."
                ) from exc
            raise

        cls._resolve_lens_path = staticmethod(resolve_lens_path)
        cls._resolve_smx_path = staticmethod(resolve_smx_path)

    def test_resolve_lens_alias_uses_catalogs_lens_directory(self) -> None:
        """Lens aliases should resolve to bundled assets under `catalogs/lenses`."""

        zmx_path = self._resolve_lens_path("canon50")

        self.assertTrue(zmx_path.exists())
        self.assertTrue(
            str(zmx_path).endswith(
                "catalogs/lenses/zmxFiles/CanonEF50mmf1.0L.zmx"
            )
        )

    def test_resolve_smx_infers_catalogs_lens_sidecar(self) -> None:
        """SMX inference should use the bundled sidecar directory."""

        zmx_path = self._resolve_lens_path("canon50")
        smx_path = self._resolve_smx_path(None, zmx_path=zmx_path)

        self.assertIsNotNone(smx_path)
        assert smx_path is not None
        self.assertTrue(smx_path.exists())
        self.assertTrue(
            str(smx_path).endswith(
                "catalogs/lenses/smxFiles/CanonEF50mmf1.0L.smx"
            )
        )


if __name__ == "__main__":
    unittest.main()
