"""Check macro exit status at the real Geant4 executable boundary."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def scintipix() -> Path:
    executable = Path(__file__).resolve().parents[2] / "build" / "scintipix"
    if not executable.is_file():
        if os.environ.get("CI"):
            pytest.fail(f"CI must build {executable} before running Python tests")
        pytest.skip("Build the simulator with 'pixi run build-sim' to run this test")
    return executable


@pytest.mark.parametrize(
    ("commands", "diagnostic"),
    [
        ("/this/command/does/not/exist 1\n", "COMMAND NOT FOUND"),
        ("/control/verbose 3\n", "parameter out of range"),
        (
            "/scintillator/properties/elements C=0.5,H=0.4\n",
            "Invalid scintillator elements command",
        ),
    ],
)
def test_invalid_macro_exits_nonzero(
    scintipix: Path, tmp_path: Path, commands: str, diagnostic: str
) -> None:
    macro = tmp_path / "invalid.mac"
    macro.write_text("/control/verbose 0\n" + commands)

    result = subprocess.run(
        [str(scintipix), str(macro)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    output = result.stdout + result.stderr
    assert diagnostic in output, output
    assert result.returncode != 0, output


def test_valid_macro_exits_zero(scintipix: Path, tmp_path: Path) -> None:
    macro = tmp_path / "valid.mac"
    macro.write_text("/control/verbose 0\n")

    result = subprocess.run(
        [str(scintipix), str(macro)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
