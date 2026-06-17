"""Comprehensive unit tests for simulation metadata and run-environment models."""

from __future__ import annotations

from datetime import date as DateType
from datetime import datetime
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

from src.models.metadata import Metadata, RunControls, WorkingDirectoryLayout


# ============================================================================
# RunControls Tests
# ============================================================================


class TestRunControls:
    """Tests for simulation stage control flags."""

    def test_default_all_stages_enabled(self) -> None:
        """All stages should be enabled by default."""
        controls = RunControls()
        assert controls.geant4_simulation is True
        assert controls.transportation is True
        assert controls.intensification is True
        assert controls.sensor_detection is True

    def test_all_stages_enabled_explicitly(self) -> None:
        """Explicitly enabling all stages should validate."""
        controls = RunControls(
            geant4_simulation=True,
            transportation=True,
            intensification=True,
            sensor_detection=True,
        )
        assert controls.geant4_simulation is True
        assert controls.transportation is True
        assert controls.intensification is True
        assert controls.sensor_detection is True

    def test_geant4_only_configuration(self) -> None:
        """Only Geant4 simulation enabled should validate."""
        controls = RunControls(
            geant4_simulation=True,
            transportation=False,
            intensification=False,
            sensor_detection=False,
        )
        assert controls.geant4_simulation is True
        assert controls.transportation is False

    def test_geant4_and_transportation_only(self) -> None:
        """Geant4 and transportation without intensification should validate."""
        controls = RunControls(
            geant4_simulation=True,
            transportation=True,
            intensification=False,
            sensor_detection=False,
        )
        assert controls.geant4_simulation is True
        assert controls.transportation is True
        assert controls.intensification is False

    def test_up_to_intensification(self) -> None:
        """Enabling up to intensification should validate."""
        controls = RunControls(
            geant4_simulation=True,
            transportation=True,
            intensification=True,
            sensor_detection=False,
        )
        assert controls.geant4_simulation is True
        assert controls.transportation is True
        assert controls.intensification is True
        assert controls.sensor_detection is False

    def test_transportation_without_geant4_rejected(self) -> None:
        """Transportation requires Geant4 simulation."""
        with pytest.raises(
            ValidationError,
            match="Transportation stage requires GEANT4 simulation",
        ):
            RunControls(
                geant4_simulation=False,
                transportation=True,
            )

    def test_intensification_without_transportation_rejected(self) -> None:
        """Intensification requires transportation."""
        with pytest.raises(
            ValidationError,
            match="Intensification stage requires transportation",
        ):
            RunControls(
                geant4_simulation=True,
                transportation=False,
                intensification=True,
            )

    def test_sensor_detection_without_intensification_rejected(self) -> None:
        """Sensor detection requires intensification."""
        with pytest.raises(
            ValidationError,
            match="Sensor detection stage requires intensification",
        ):
            RunControls(
                geant4_simulation=True,
                transportation=True,
                intensification=False,
                sensor_detection=True,
            )

    def test_all_stages_disabled(self) -> None:
        """All stages disabled should validate."""
        controls = RunControls(
            geant4_simulation=False,
            transportation=False,
            intensification=False,
            sensor_detection=False,
        )
        assert controls.geant4_simulation is False
        assert controls.transportation is False
        assert controls.intensification is False
        assert controls.sensor_detection is False

    def test_sensor_without_geant4_rejected(self) -> None:
        """Sensor detection requires full pipeline."""
        with pytest.raises(ValidationError):
            RunControls(
                geant4_simulation=False,
                transportation=False,
                intensification=False,
                sensor_detection=True,
            )


# ============================================================================
# WorkingDirectoryLayout Tests
# ============================================================================


class TestWorkingDirectoryLayout:
    """Tests for run directory layout and path resolution."""

    def test_default_values(self) -> None:
        """Default values should be applied correctly."""
        layout = WorkingDirectoryLayout()
        assert layout.simulation_run_id == "example"
        assert layout.sub_run_number == 0
        assert layout.working_directory == "data"
        assert layout.macro_directory == "macros"
        assert layout.log_directory == "logs"

    def test_optional_directories_default_to_none(self) -> None:
        """Optional stage directories should default to None."""
        layout = WorkingDirectoryLayout()
        assert layout.primaries_directory is None
        assert layout.secondaries_directory is None
        assert layout.simulated_photons_directory is None
        assert layout.transported_photons_directory is None
        assert layout.intensified_photons_directory is None
        assert layout.sensor_hits_directory is None

    def test_alias_handling(self) -> None:
        """PascalCase aliases should map to snake_case fields."""
        layout = WorkingDirectoryLayout.model_validate(
            {
                "SimulationRunID": "test_run",
                "SubRunNumber": 42,
                "WorkingDirectory": "/tmp/data",
                "MacroDirectory": "mac",
                "LogDirectory": "log",
                "PrimariesDirectory": "prim",
                "SecondariesDirectory": "sec",
                "SimulatedPhotonsDirectory": "sim_phot",
                "TransportedPhotonsDirectory": "trans_phot",
                "IntensifiedPhotonsDirectory": "intens_phot",
                "SensorHitsDirectory": "hits",
            }
        )
        assert layout.simulation_run_id == "test_run"
        assert layout.sub_run_number == 42
        assert layout.working_directory == "/tmp/data"
        assert layout.macro_directory == "mac"
        assert layout.primaries_directory == "prim"
        assert layout.sensor_hits_directory == "hits"

    def test_empty_simulation_run_id_rejected(self) -> None:
        """Empty simulation_run_id should be rejected."""
        with pytest.raises(ValidationError, match="simulation_run_id"):
            WorkingDirectoryLayout(simulation_run_id="")

    def test_negative_sub_run_number_rejected(self) -> None:
        """Negative sub_run_number should be rejected."""
        with pytest.raises(ValidationError, match="sub_run_number"):
            WorkingDirectoryLayout(sub_run_number=-1)

    def test_sub_run_number_above_9999_rejected(self) -> None:
        """sub_run_number above 9999 should be rejected."""
        with pytest.raises(ValidationError, match="sub_run_number"):
            WorkingDirectoryLayout(sub_run_number=10000)

    def test_valid_sub_run_number_range(self) -> None:
        """Valid sub_run_number range should be accepted."""
        layout0 = WorkingDirectoryLayout(sub_run_number=0)
        assert layout0.sub_run_number == 0

        layout9999 = WorkingDirectoryLayout(sub_run_number=9999)
        assert layout9999.sub_run_number == 9999

    def test_blank_working_directory_gets_default(self) -> None:
        """Blank working_directory should be replaced with default."""
        layout = WorkingDirectoryLayout(working_directory="   ")
        assert layout.working_directory == "data"

    def test_blank_macro_directory_gets_default(self) -> None:
        """Blank macro_directory should be replaced with default."""
        layout = WorkingDirectoryLayout(macro_directory="")
        assert layout.macro_directory == "macros"

    def test_blank_log_directory_gets_default(self) -> None:
        """Blank log_directory should be replaced with default."""
        layout = WorkingDirectoryLayout(log_directory="   ")
        assert layout.log_directory == "logs"

    def test_run_directory_property(self) -> None:
        """run_directory should format correctly."""
        layout = WorkingDirectoryLayout(
            simulation_run_id="test",
            sub_run_number=5,
            working_directory="/tmp",
        )
        assert layout.run_directory == Path("/tmp/test_005")

    def test_run_directory_with_three_digit_padding(self) -> None:
        """sub_run_number should be zero-padded to 3 digits."""
        layout = WorkingDirectoryLayout(
            simulation_run_id="exp",
            sub_run_number=0,
        )
        assert layout.run_directory == Path("data/exp_000")

        layout99 = WorkingDirectoryLayout(
            simulation_run_id="exp",
            sub_run_number=99,
        )
        assert layout99.run_directory == Path("data/exp_099")

    def test_apply_stage_defaults_geant4_only(self) -> None:
        """apply_stage_defaults should set Geant4 directories only."""
        layout = WorkingDirectoryLayout()
        controls = RunControls(
            geant4_simulation=True,
            transportation=False,
            intensification=False,
            sensor_detection=False,
        )
        layout.apply_stage_defaults(controls)

        assert layout.primaries_directory == "primaries"
        assert layout.secondaries_directory == "secondaries"
        assert layout.simulated_photons_directory == "simulatedPhotons"
        assert layout.transported_photons_directory is None
        assert layout.intensified_photons_directory is None
        assert layout.sensor_hits_directory is None

    def test_apply_stage_defaults_full_pipeline(self) -> None:
        """apply_stage_defaults should set all directories for full pipeline."""
        layout = WorkingDirectoryLayout()
        controls = RunControls()
        layout.apply_stage_defaults(controls)

        assert layout.primaries_directory == "primaries"
        assert layout.secondaries_directory == "secondaries"
        assert layout.simulated_photons_directory == "simulatedPhotons"
        assert layout.transported_photons_directory == "transportedPhotons"
        assert layout.intensified_photons_directory == "intensifiedPhotons"
        assert layout.sensor_hits_directory == "sensorHits"

    def test_apply_stage_defaults_preserves_explicit_values(self) -> None:
        """apply_stage_defaults should not overwrite explicit values."""
        layout = WorkingDirectoryLayout(
            primaries_directory="custom_primaries",
            simulated_photons_directory="custom_photons",
        )
        controls = RunControls()
        layout.apply_stage_defaults(controls)

        assert layout.primaries_directory == "custom_primaries"
        assert layout.simulated_photons_directory == "custom_photons"

    def test_apply_stage_defaults_fills_blank_values(self) -> None:
        """apply_stage_defaults should replace blank values with defaults."""
        layout = WorkingDirectoryLayout(
            primaries_directory="  ",
            simulated_photons_directory="",
        )
        controls = RunControls()
        layout.apply_stage_defaults(controls)

        assert layout.primaries_directory == "primaries"
        assert layout.simulated_photons_directory == "simulatedPhotons"

    def test_directories_to_create_includes_run_root(self) -> None:
        """directories_to_create should include run root."""
        layout = WorkingDirectoryLayout()
        directories = layout.directories_to_create()
        assert "run root" in directories
        assert directories["run root"] == Path("data/example_000")

    def test_directories_to_create_excludes_none_values(self) -> None:
        """directories_to_create should exclude None directories."""
        layout = WorkingDirectoryLayout()
        directories = layout.directories_to_create()
        assert "secondaries directory" not in directories
        assert "primaries directory" not in directories

    def test_directories_to_create_with_explicit_values(self) -> None:
        """directories_to_create should include explicitly set directories."""
        layout = WorkingDirectoryLayout(
            primaries_directory="prim",
            secondaries_directory="sec",
        )
        layout.resolve_directories()
        directories = layout.directories_to_create()
        assert "primaries directory" in directories
        assert directories["primaries directory"] == (
            _repo_root() / "data" / "example_000" / "prim"
        )
        assert "secondaries directory" in directories
        assert directories["secondaries directory"] == (
            _repo_root() / "data" / "example_000" / "sec"
        )

    def test_resolve_directories_relative_paths(self) -> None:
        """resolve_directories should resolve relative directories under run root."""
        layout = WorkingDirectoryLayout(
            simulation_run_id="test",
            sub_run_number=0,
            working_directory="/tmp",
            primaries_directory="subdir",
        )
        layout.resolve_directories()
        assert Path(layout.primaries_directory) == Path("/tmp/test_000/subdir").resolve()

    def test_resolve_directories_absolute_paths(self) -> None:
        """resolve_directories should preserve absolute directory paths."""
        layout = WorkingDirectoryLayout(primaries_directory="/absolute/path")
        layout.resolve_directories()
        assert Path(layout.primaries_directory) == Path("/absolute/path")

    def test_resolve_directories_none_values_remain_none(self) -> None:
        """resolve_directories should leave unset optional directories as None."""
        layout = WorkingDirectoryLayout()
        layout.resolve_directories()
        assert layout.primaries_directory is None


# ============================================================================
# Metadata Tests
# ============================================================================


class TestMetadata:
    """Tests for complete simulation metadata model."""

    @staticmethod
    def _minimal_metadata_payload(tmp_path: Path) -> dict:
        """Helper to create minimal valid metadata payload."""
        return {
            "author": "Test Author",
            "date": "2026-06-16",
            "version": "1.0.0",
            "description": "Test simulation",
            "RunEnvironment": {
                "WorkingDirectory": str(tmp_path),
                "SimulationRunID": "test",
            },
        }

    def test_valid_minimal_metadata(self, tmp_path: Path) -> None:
        """Minimal valid metadata should validate."""
        metadata = Metadata.model_validate(self._minimal_metadata_payload(tmp_path))
        assert metadata.author == "Test Author"
        assert metadata.date == "2026-06-16"
        assert metadata.version == "1.0.0"
        assert metadata.description == "Test simulation"

    def test_run_controls_default_factory(self, tmp_path: Path) -> None:
        """run_controls should use default factory if not provided."""
        metadata = Metadata.model_validate(self._minimal_metadata_payload(tmp_path))
        assert metadata.run_controls.geant4_simulation is True
        assert metadata.run_controls.transportation is True
        assert metadata.run_controls.intensification is True
        assert metadata.run_controls.sensor_detection is True

    def test_run_controls_alias_handling(self, tmp_path: Path) -> None:
        """RunControls alias should map to run_controls."""
        payload = self._minimal_metadata_payload(tmp_path)
        payload["RunControls"] = {
            "geant4_simulation": True,
            "transportation": False,
            "intensification": False,
            "sensor_detection": False,
        }
        metadata = Metadata.model_validate(payload)
        assert metadata.run_controls.transportation is False

    def test_run_environment_alias_handling(self, tmp_path: Path) -> None:
        """RunEnvironment alias should map to run_environment."""
        metadata = Metadata.model_validate(self._minimal_metadata_payload(tmp_path))
        assert metadata.run_environment.simulation_run_id == "test"

    def test_empty_author_rejected(self, tmp_path: Path) -> None:
        """Empty author should be rejected."""
        payload = self._minimal_metadata_payload(tmp_path)
        payload["author"] = ""
        with pytest.raises(ValidationError, match="author"):
            Metadata.model_validate(payload)

    def test_empty_date_rejected(self, tmp_path: Path) -> None:
        """Empty date should be rejected."""
        payload = self._minimal_metadata_payload(tmp_path)
        payload["date"] = ""
        with pytest.raises(ValidationError, match="date"):
            Metadata.model_validate(payload)

    def test_empty_version_rejected(self, tmp_path: Path) -> None:
        """Empty version should be rejected."""
        payload = self._minimal_metadata_payload(tmp_path)
        payload["version"] = ""
        with pytest.raises(ValidationError, match="version"):
            Metadata.model_validate(payload)

    def test_empty_description_rejected(self, tmp_path: Path) -> None:
        """Empty description should be rejected."""
        payload = self._minimal_metadata_payload(tmp_path)
        payload["description"] = ""
        with pytest.raises(ValidationError, match="description"):
            Metadata.model_validate(payload)

    def test_date_normalization_from_datetime(self, tmp_path: Path) -> None:
        """datetime objects should be normalized to ISO date strings."""
        payload = self._minimal_metadata_payload(tmp_path)
        payload["date"] = datetime(2026, 6, 16, 14, 30, 0)
        metadata = Metadata.model_validate(payload)
        assert metadata.date == "2026-06-16"

    def test_date_normalization_from_date(self, tmp_path: Path) -> None:
        """date objects should be normalized to ISO date strings."""
        payload = self._minimal_metadata_payload(tmp_path)
        payload["date"] = DateType(2026, 6, 16)
        metadata = Metadata.model_validate(payload)
        assert metadata.date == "2026-06-16"

    def test_date_string_preserved(self, tmp_path: Path) -> None:
        """String dates should be preserved as-is."""
        payload = self._minimal_metadata_payload(tmp_path)
        payload["date"] = "2026-06-16"
        metadata = Metadata.model_validate(payload)
        assert metadata.date == "2026-06-16"

    def test_metadata_creates_default_directories_for_enabled_stages(
        self, tmp_path: Path
    ) -> None:
        """Metadata should create default directories for enabled stages."""
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
            "secondaries",
            "simulatedPhotons",
            "transportedPhotons",
            "intensifiedPhotons",
            "sensorHits",
            "macros",
            "logs",
        ):
            assert (run_root / directory).is_dir()

    def test_metadata_skips_directories_for_disabled_stages(
        self,
        tmp_path: Path,
    ) -> None:
        """Metadata should skip directories for disabled stages."""
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

    def test_metadata_creates_explicit_optional_stage_directories(
        self, tmp_path: Path
    ) -> None:
        """Metadata should create explicitly specified optional directories."""
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
        self,
        tmp_path: Path,
    ) -> None:
        """Metadata should reject directory paths that collide with files."""
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

    def test_complete_metadata_configuration(self, tmp_path: Path) -> None:
        """Complete metadata with all fields should validate."""
        metadata = Metadata.model_validate(
            {
                "author": "John Doe",
                "date": "2026-06-16",
                "version": "2.1.0",
                "description": "Full pipeline simulation with custom directories",
                "RunControls": {
                    "geant4_simulation": True,
                    "transportation": True,
                    "intensification": True,
                    "sensor_detection": True,
                },
                "RunEnvironment": {
                    "SimulationRunID": "full_test",
                    "SubRunNumber": 123,
                    "WorkingDirectory": str(tmp_path),
                    "MacroDirectory": "custom_macros",
                    "LogDirectory": "custom_logs",
                    "PrimariesDirectory": "custom_primaries",
                    "SecondariesDirectory": "custom_secondaries",
                    "SimulatedPhotonsDirectory": "custom_sim_photons",
                    "TransportedPhotonsDirectory": "custom_trans_photons",
                    "IntensifiedPhotonsDirectory": "custom_intens_photons",
                    "SensorHitsDirectory": "custom_hits",
                },
            }
        )

        assert metadata.author == "John Doe"
        assert metadata.version == "2.1.0"
        run_root = tmp_path / "full_test_123"
        assert (run_root / "custom_macros").is_dir()
        assert (run_root / "custom_primaries").is_dir()
        assert (run_root / "custom_secondaries").is_dir()
        assert (run_root / "custom_hits").is_dir()

    def test_metadata_with_partial_pipeline(self, tmp_path: Path) -> None:
        """Metadata with partial pipeline should only create relevant directories."""
        metadata = Metadata.model_validate(
            {
                "author": "Test User",
                "date": "2026-06-16",
                "version": "1.0",
                "description": "Partial pipeline test",
                "RunControls": {
                    "geant4_simulation": True,
                    "transportation": True,
                    "intensification": False,
                    "sensor_detection": False,
                },
                "RunEnvironment": {
                    "WorkingDirectory": str(tmp_path),
                    "SimulationRunID": "partial",
                },
            }
        )

        run_root = tmp_path / "partial_000"
        assert (run_root / "primaries").is_dir()
        assert (run_root / "simulatedPhotons").is_dir()
        assert (run_root / "transportedPhotons").is_dir()
        assert not (run_root / "intensifiedPhotons").exists()
        assert not (run_root / "sensorHits").exists()
        assert metadata.run_controls.intensification is False

    def test_serialization_uses_aliases(self, tmp_path: Path) -> None:
        """Serialized output should use PascalCase aliases."""
        metadata = Metadata.model_validate(self._minimal_metadata_payload(tmp_path))
        dumped = metadata.model_dump(by_alias=True)
        assert "RunControls" in dumped
        assert "RunEnvironment" in dumped
        assert "SimulationRunID" in dumped["RunEnvironment"]
