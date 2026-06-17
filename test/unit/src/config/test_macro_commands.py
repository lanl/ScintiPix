"""Unit tests for macro.py write-only API.

Tests verify that write_macro() and append_macro_line() work correctly.
These tests are intentionally minimal and focused on the public API only.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


def _repo_root() -> Path:
    """Resolve repository root by searching parent directories."""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "src").is_dir() and (parent / "pixi.toml").is_file():
            return parent
    raise RuntimeError("Could not resolve repository root from test path.")


# Ensure repository root is importable when this file is run directly.
sys.path.insert(0, str(_repo_root()))


class MacroAppendLineTests(unittest.TestCase):
    """Tests for append_macro_line function."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load macro module or skip when dependencies are missing."""

        try:
            from src.config.macro import append_macro_line
        except ModuleNotFoundError as exc:
            missing_name = (getattr(exc, "name", "") or "").lower()
            message = str(exc).lower()
            if "pydantic" in missing_name or "pydantic" in message:
                raise unittest.SkipTest(
                    f"Missing dependency: {exc}. "
                    "Run in the project environment (for example: pixi run)."
                ) from exc
            raise

        cls.append_macro_line = staticmethod(append_macro_line)

    def test_append_macro_line_appends_single_line(self) -> None:
        """append_macro_line should append one normalized line per call."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            macro_path = tmp_path / "append_test.mac"
            macro_path.write_text("/run/initialize\n", encoding="utf-8")

            self.append_macro_line(macro_path, "/vis/open OGL")
            self.append_macro_line(macro_path, "/vis/drawVolume\n")

            written_lines = macro_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                written_lines,
                ["/run/initialize", "/vis/open OGL", "/vis/drawVolume"],
            )

    def test_append_macro_line_rejects_embedded_newlines(self) -> None:
        """append_macro_line should reject payloads with embedded newlines."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            macro_path = tmp_path / "append_test.mac"
            macro_path.write_text("/run/initialize\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                self.append_macro_line(
                    macro_path, "/vis/open OGL\n/vis/drawVolume"
                )

            with self.assertRaises(ValueError):
                self.append_macro_line(
                    macro_path, "/vis/open OGL\r/vis/drawVolume"
                )

            written_lines = macro_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(written_lines, ["/run/initialize"])

    def test_append_macro_line_strips_trailing_newlines(self) -> None:
        """append_macro_line should strip trailing newlines from input."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            macro_path = tmp_path / "append_test.mac"
            macro_path.write_text("", encoding="utf-8")

            self.append_macro_line(macro_path, "/run/initialize\n")
            self.append_macro_line(macro_path, "/gps/particle neutron\r\n")

            written_lines = macro_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                written_lines,
                ["/run/initialize", "/gps/particle neutron"],
            )


if __name__ == "__main__":
    unittest.main()
