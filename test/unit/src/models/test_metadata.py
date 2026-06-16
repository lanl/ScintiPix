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

from src.models.metadata import Metadata, WorkingDirectoryLayout


def test_metadata_creates_default_directories_for_enabled_stages(tmp_path: Path) -> None:
    metadata = Metadata(
        author="Unit Test",
        date="2026-06-16",
        version="test",
        description="Directory validation test.",
        RunEnvironment={
            "WorkingDirectory": str(tmp_path),
            "SimulationRunID": "unit",
            "SubRunNumber": 7,
        },
    )

    run_root = tmp_path / "unit_007"
    assert metadata.run_environment.run_directory == run_root
    for directory in (
        "primaries",
        "simulatedPhotons",
        "transportedPhotons",
        "intensifiedPhotons",
        "sensorHits",
        "macros",
        "logs",
    ):
        assert (run_root / directory).is_dir()
    assert not (run_root / "secondaries").exists()


def test_metadata_skips_directories_for_disabled_stages(
    tmp_path: Path,
) -> None:
    Metadata(
        author="Unit Test",
        date="2026-06-16",
        version="test",
        description="Geant4-only directory validation test.",
        RunControls={
            "transportation": False,
            "intensification": False,
            "sensor_detection": False,
        },
        RunEnvironment={
            "WorkingDirectory": str(tmp_path),
            "SimulationRunID": "geant4_only",
        },
    )

    run_root = tmp_path / "geant4_only_000"
    assert (run_root / "primaries").is_dir()
    assert (run_root / "simulatedPhotons").is_dir()
    assert not (run_root / "transportedPhotons").exists()
    assert not (run_root / "intensifiedPhotons").exists()
    assert not (run_root / "sensorHits").exists()


def test_metadata_creates_explicit_optional_stage_directories(tmp_path: Path) -> None:
    Metadata(
        author="Unit Test",
        date="2026-06-16",
        version="test",
        description="Explicit optional directory validation test.",
        RunControls={
            "transportation": False,
            "intensification": False,
            "sensor_detection": False,
        },
        RunEnvironment={
            "WorkingDirectory": str(tmp_path),
            "SimulationRunID": "custom",
            "PrimariesDirectory": "neutrons",
            "SecondariesDirectory": "secondaries",
            "SimulatedPhotonsDirectory": "photons",
        },
    )

    run_root = tmp_path / "custom_000"
    assert (run_root / "neutrons").is_dir()
    assert (run_root / "secondaries").is_dir()
    assert (run_root / "photons").is_dir()


def test_working_directory_layout_rejects_file_path_collisions(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "collision_000"
    run_root.mkdir(parents=True)
    (run_root / "logs").write_text("not a directory", encoding="utf-8")

    with pytest.raises(ValidationError, match="log directory is not a directory"):
        Metadata(
            author="Unit Test",
            date="2026-06-16",
            version="test",
            description="Path collision validation test.",
            RunEnvironment={
                "WorkingDirectory": str(tmp_path),
                "SimulationRunID": "collision",
            },
        )


def test_working_directory_layout_only_fills_universal_defaults() -> None:
    layout = WorkingDirectoryLayout()

    assert layout.working_directory == "data"
    assert layout.macro_directory == "macros"
    assert layout.log_directory == "logs"
    assert layout.secondaries_directory is None
    assert layout.intensified_photons_directory is None
