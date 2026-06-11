"""Simulation metadata and run-environment models."""

from __future__ import annotations

from datetime import date as DateType
from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator

from .base import StrictModel


class RunEnvironmentOutputInfo(StrictModel):
    """Output staging settings nested under `RunEnvironment`.

    Directory values are interpreted relative to
    `Metadata.RunEnvironment.WorkingDirectory` when given as relative paths.

    Transport chunking controls apply to optical-transport HDF5 writing:
    - `transport_chunk_rows`:
      - integer: explicit rows per HDF5 chunk and per in-memory work batch.
      - `"auto"`: derive rows from `transport_chunk_target_mib`.
    - `transport_chunk_target_mib`:
      - target memory budget (MiB) for one transport processing batch when
        `transport_chunk_rows` is `"auto"`.
      - the transport module estimates rows using
        `(input_row_bytes + output_row_bytes)` and clamps to valid bounds.
    """

    simulated_photons_dir: str = Field(
        default="simulatedPhotons",
        validation_alias=AliasChoices(
            "SimulatedPhotonsDirectory",
            "simulated_photons_dir",
            "simulatedPhotonsDir",
        ),
        serialization_alias="SimulatedPhotonsDirectory",
        min_length=1,
    )
    transported_photons_dir: str = Field(
        default="transportedPhotons",
        validation_alias=AliasChoices(
            "TransportedPhotonsDirectory",
            "transported_photons_dir",
            "transportedPhotonsDir",
        ),
        serialization_alias="TransportedPhotonsDirectory",
        min_length=1,
    )
    transport_chunk_rows: int | Literal["auto"] = Field(
        default="auto",
        validation_alias=AliasChoices(
            "TransportChunkRows",
            "transport_chunk_rows",
            "transportChunkRows",
        ),
        serialization_alias="TransportChunkRows",
    )
    transport_chunk_target_mib: float = Field(
        default=32.0,
        validation_alias=AliasChoices(
            "TransportChunkTargetMiB",
            "transport_chunk_target_mib",
            "transportChunkTargetMiB",
        ),
        serialization_alias="TransportChunkTargetMiB",
        gt=0.0,
    )

    @field_validator("transport_chunk_rows", mode="before")
    @classmethod
    def normalize_transport_chunk_rows(
        cls,
        value: object,
    ) -> int | Literal["auto"]:
        """Normalize `TransportChunkRows` input into `int` or `"auto"`.

        Accepted inputs:
        - `None` or empty string -> `"auto"`
        - case-insensitive `"auto"` string -> `"auto"`
        - positive integer (or numeric string) -> integer row count

        Rejected inputs:
        - zero/negative values
        - non-numeric strings other than `"auto"`
        - non-string/non-integer object types
        """

        if value is None:
            return "auto"
        if isinstance(value, str):
            token = value.strip()
            if token == "":
                return "auto"
            if token.lower() == "auto":
                return "auto"
            try:
                value = int(token)
            except ValueError as exc:
                raise ValueError(
                    "`TransportChunkRows` must be a positive integer or 'auto'."
                ) from exc
        if isinstance(value, int):
            if value <= 0:
                raise ValueError("`TransportChunkRows` must be > 0 when specified.")
            return value
        raise ValueError("`TransportChunkRows` must be a positive integer or 'auto'.")


class RunEnvironmentConfig(StrictModel):
    """Run directory layout and execution-path context.

    Default layout policy:
    - `SimulationRunID`: "example"
    - `SubRunNumber`: `0`
    - `WorkingDirectory`: `data/`
    - `MacroDirectory`: `macros/`
    - `LogDirectory`: `logs/`
    - `OutputInfo.SimulatedPhotonsDirectory`: `simulatedPhotons/`
    - `OutputInfo.TransportedPhotonsDirectory`: `transportedPhotons/`
    - `OutputInfo.TransportChunkRows`: `auto`
    - `OutputInfo.TransportChunkTargetMiB`: `32`
    """

    simulation_run_id: str = Field(alias="SimulationRunID", default="example", min_length=1)
    sub_run_number: int = Field(alias="SubRunNumber", default=0, ge=0, le=9999)
    working_directory: str | None = Field(default=None, alias="WorkingDirectory")
    macro_directory: str | None = Field(default=None, alias="MacroDirectory")
    log_directory: str | None = Field(default=None, alias="LogDirectory")
    output_info: RunEnvironmentOutputInfo = Field(
        alias="OutputInfo", default_factory=RunEnvironmentOutputInfo
    )

    @model_validator(mode="after")
    def apply_layout_defaults(self) -> "RunEnvironmentConfig":
        """Fill directory defaults for run environment.

        WorkingDirectory defaults to `data`.
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


class MetadataConfig(StrictModel):
    """Simulation metadata and IO context block."""

    author: str = Field(min_length=1)
    date: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    run_environment: RunEnvironmentConfig = Field(
        validation_alias=AliasChoices("RunEnvironment", "run_environment"),
        serialization_alias="RunEnvironment",
        default_factory=RunEnvironmentConfig,
    )

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
