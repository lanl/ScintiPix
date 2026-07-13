"""Simulation metadata and run-environment models."""

from __future__ import annotations

from datetime import date as DateType
from datetime import datetime
from pathlib import Path

from pydantic import Field, field_validator, model_validator

try:
    from src.common.utilities import ensure_directories
    from src.common.utilities import resolve_path
except ModuleNotFoundError:  # pragma: no cover - supports PYTHONPATH=src usage
    from common.utilities import ensure_directories
    from common.utilities import resolve_path

from .base import StrictModel


class RunControls(StrictModel):
    """Simulation stage controls.

    These define how far the simulation should proceed from Geant4 simulations,
    to transportation of photons, to the intensification stage and finally to the
    detection of sensor hits.
    """

    auto_focus_lens: bool = Field(
        default=False,
        description="Whether to run the automatic lens focusing routine to determine optimal working distance.",
    )
    geant4_simulation: bool = Field(
        default=True,
        description="Whether to run the Geant4 simulation stage.",
    )
    transportation: bool = Field(
        default=True,
        description="Whether to run the transportation stage.",
    )
    intensification: bool = Field(
        default=True,
        description="Whether to run the intensification stage.",
    )
    sensor_detection: bool = Field(
        default=True,
        description="Whether to run the sensor detection stage.",
    )

    @model_validator(mode="after")
    def check_sequential_requirements(self) -> "RunControls":
        """Check that the simulation stages are enabled sequentially.

        Ensures that if a later stage is enabled, all preceding stages are also enabled.
        Raises a ValueError if the sequential requirement is not met.
        """

        if self.transportation and not self.geant4_simulation:
            raise ValueError("Transportation stage requires GEANT4 simulation to be enabled.")
        if self.intensification and not self.transportation:
            raise ValueError("Intensification stage requires transportation to be enabled.")
        if self.sensor_detection and not self.intensification:
            raise ValueError("Sensor detection stage requires intensification to be enabled.")
        return self


class WorkingDirectoryLayout(StrictModel):
    """Run directory layout and execution-path context.

    Default layout policy:
    - `SimulationRunID`: "example"
    - `SubRunNumber`: `0`
    - `WorkingDirectory`: `data/`
    - `MacroDirectory`: `macros/`
    - `LogDirectory`: `logs/`

    Stage directories default only when their corresponding run stage is enabled.
    Optional directories left as `None` are not checked or created.
    """

    simulation_run_id: str = Field(
        alias="SimulationRunID",
        default="example",
        min_length=1,
    )
    sub_run_number: int = Field(alias="SubRunNumber", default=0, ge=0, le=9999)
    working_directory: str | None = Field(default=None, alias="WorkingDirectory")
    macro_directory: str | None = Field(default=None, alias="MacroDirectory")
    log_directory: str | None = Field(default=None, alias="LogDirectory")
    primaries_directory: str | None = Field(default=None, alias="PrimariesDirectory")
    secondaries_directory: str | None = Field(
        default=None,
        alias="SecondariesDirectory",
    )
    simulated_photons_directory: str | None = Field(
        default=None,
        alias="SimulatedPhotonsDirectory",
    )
    transported_photons_directory: str | None = Field(
        default=None,
        alias="TransportedPhotonsDirectory",
    )
    intensified_photons_directory: str | None = Field(
        default=None,
        alias="IntensifiedPhotonsDirectory",
    )
    sensor_hits_directory: str | None = Field(default=None, alias="SensorHitsDirectory")
    config_directory: str | None = Field(default=None, alias="ConfigDirectory")
    primaries_filename: str = Field(
        default="primaries.bin",
        alias="PrimariesFilename",
        min_length=1,
    )
    secondaries_filename: str = Field(
        default="secondaries.bin",
        alias="SecondariesFilename",
        min_length=1,
    )
    photons_filename: str = Field(
        default="photons.bin",
        alias="PhotonsFilename",
        min_length=1,
    )

    @model_validator(mode="after")
    def fill_in_layout_defaults(self) -> "WorkingDirectoryLayout":
        """Fill directory defaults for run environment.

        WorkingDirectory defaults to `data`.
        If working_directory is "data", it's resolved to repo_root/data.
        Otherwise, it's used as-is (absolute or relative to cwd).
        Run-specific directories are resolved later as
        `<WorkingDirectory>/<SimulationRunID>/...`.
        """
        if self.working_directory is None or not self.working_directory.strip():
            self.working_directory = "data"
        if self.macro_directory is None or not self.macro_directory.strip():
            self.macro_directory = "macros"
        if self.log_directory is None or not self.log_directory.strip():
            self.log_directory = "logs"
        return self

    def apply_stage_defaults(self, controls: RunControls) -> None:
        """Fill defaults for stage directories required by enabled run controls."""

        if controls.auto_focus_lens:
            self.config_directory = _default_if_blank(
                self.config_directory,
                "config",
            )
        if controls.geant4_simulation:
            self.primaries_directory = _default_if_blank(
                self.primaries_directory,
                "primaries",
            )
            self.secondaries_directory = _default_if_blank(
                self.secondaries_directory,
                "secondaries",
            )
            self.simulated_photons_directory = _default_if_blank(
                self.simulated_photons_directory,
                "simulatedPhotons",
            )
        if controls.transportation:
            self.transported_photons_directory = _default_if_blank(
                self.transported_photons_directory,
                "transportedPhotons",
            )
        if controls.intensification:
            self.intensified_photons_directory = _default_if_blank(
                self.intensified_photons_directory,
                "intensifiedPhotons",
            )
        if controls.sensor_detection:
            self.sensor_hits_directory = _default_if_blank(
                self.sensor_hits_directory,
                "sensorHits",
            )

    def directories_to_create(self) -> dict[str, Path]:
        """Return configured directories that should exist for this run."""

        directories: dict[str, Path | None] = {
            "run root": self.run_directory,
            "macro directory": (
                Path(self.macro_directory) if self.macro_directory else None
            ),
            "log directory": Path(self.log_directory) if self.log_directory else None,
            "primaries directory": (
                Path(self.primaries_directory)
                if self.primaries_directory
                else None
            ),
            "secondaries directory": (
                Path(self.secondaries_directory)
                if self.secondaries_directory
                else None
            ),
            "simulated photons directory": (
                Path(self.simulated_photons_directory)
                if self.simulated_photons_directory
                else None
            ),
            "transported photons directory": (
                Path(self.transported_photons_directory)
                if self.transported_photons_directory
                else None
            ),
            "intensified photons directory": (
                Path(self.intensified_photons_directory)
                if self.intensified_photons_directory
                else None
            ),
            "sensor hits directory": (
                Path(self.sensor_hits_directory) if self.sensor_hits_directory else None
            ),
        }
        return {
            label: directory
            for label, directory in directories.items()
            if directory is not None
        }

    def create_directories(self) -> dict[str, Path]:
        """Create the configured run directory structure if it is missing."""

        return ensure_directories(self.directories_to_create(), create=True)

    def resolve_directories(self) -> None:
        """Resolve configured directories to absolute paths."""

        if self.working_directory is None:
            raise ValueError("Run environment directory defaults were not applied.")
        self.working_directory = str(resolve_path(self.working_directory))
        run_directory = self.run_directory
        for field_name in (
            "macro_directory",
            "log_directory",
            "primaries_directory",
            "secondaries_directory",
            "simulated_photons_directory",
            "transported_photons_directory",
            "intensified_photons_directory",
            "sensor_hits_directory",
        ):
            value = getattr(self, field_name)
            if value is None or not value.strip():
                continue
            setattr(
                self,
                field_name,
                str(resolve_path(value, base_directory=run_directory)),
            )

    @property
    def run_directory(self) -> Path:
        """Return the run root directory for this sub-run."""

        if self.working_directory is None:
            raise ValueError("Run environment directory defaults were not applied.")
        run_name = f"{self.simulation_run_id}_{self.sub_run_number:03d}"
        return Path(self.working_directory) / run_name


class Metadata(StrictModel):
    """Simulation metadata and IO context block."""

    author: str = Field(min_length=1)
    date: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    run_controls: RunControls = Field(default_factory=RunControls, alias="RunControls")
    run_environment: WorkingDirectoryLayout = Field(alias="RunEnvironment")

    @model_validator(mode="after")
    def prepare_run_layout(self) -> "Metadata":
        """Apply stage-aware defaults and create configured run directories."""

        self.run_environment.apply_stage_defaults(self.run_controls)
        self.run_environment.resolve_directories()
        try:
            self.run_environment.create_directories()
        except OSError as exc:
            raise ValueError(str(exc)) from exc
        return self

    @field_validator("date", mode="before")
    @classmethod
    def normalize_yaml_date(cls, value: object) -> object:
        """Normalize YAML date-like scalars to canonical ISO strings.

        YAML parsers may decode unquoted dates into `date`/`datetime` objects.
        This validator converts those to ISO strings so the field stays a
        predictable textual representation.
        """

        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, DateType):
            return value.isoformat()
        return value


def _default_if_blank(value: str | None, default: str) -> str:
    """Return a default for missing or blank string values."""

    if value is None or not value.strip():
        return default
    return value
