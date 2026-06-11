"""Simulation and runner execution models."""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from .base import StrictModel


class RuntimeControlsConfig(StrictModel):
    """Optional GEANT4 runtime control command settings.

    These values map to macro preamble commands commonly used for run logging
    and progress control.
    """

    control_verbose: int | None = Field(default=None, alias="controlVerbose", ge=0)
    run_verbose: int | None = Field(default=None, alias="runVerbose", ge=0)
    event_verbose: int | None = Field(default=None, alias="eventVerbose", ge=0)
    tracking_verbose: int | None = Field(default=None, alias="trackingVerbose", ge=0)
    print_progress: int | None = Field(default=None, alias="printProgress", gt=0)
    store_trajectory: bool | None = Field(default=None, alias="storeTrajectory")

    @model_validator(mode="after")
    def require_at_least_one_control(self) -> "RuntimeControlsConfig":
        """Require at least one runtime control field when block is present."""

        if (
            self.control_verbose is None
            and self.run_verbose is None
            and self.event_verbose is None
            and self.tracking_verbose is None
            and self.print_progress is None
            and self.store_trajectory is None
        ):
            raise ValueError(
                "`simulation.runtimeControls` must set at least one control value."
            )
        return self


class SimulationConfig(StrictModel):
    """Run-control block for simulation execution commands.

    This block captures execution-time knobs that map to `/run/*` macro
    commands. It is intentionally separate from geometry and metadata so run
    volume can be tuned without changing detector/source definitions.
    """

    number_of_particles: int | None = Field(default=None, alias="numberOfParticles", gt=0)
    runtime_controls: RuntimeControlsConfig | None = Field(
        default=None, alias="runtimeControls"
    )

    @model_validator(mode="after")
    def require_at_least_one_setting(self) -> "SimulationConfig":
        """Require at least one run-control setting when block is present."""

        if self.number_of_particles is None and self.runtime_controls is None:
            raise ValueError(
                "`simulation` must include `numberOfParticles` and/or `runtimeControls`."
            )
        return self


class RunnerConfig(StrictModel):
    """Python-side simulation launch settings consumed by `src.runner`.

    These values are intentionally separate from :class:`SimulationConfig`,
    which maps to GEANT4 macro commands. `RunnerConfig` captures how Python
    should launch and verify a simulation that has already been configured.
    The runner launches GEANT4 in batch mode via a macro file, so the default
    terminal progress bar is off unless explicitly enabled.
    """

    binary: str = Field(min_length=1, default="scintipix")
    show_progress: bool = Field(default=False, alias="showProgress")
    verify_output: bool = Field(default=True, alias="verifyOutput")

    @field_validator("binary")
    @classmethod
    def require_non_blank_binary(cls, value: str) -> str:
        """Reject blank/whitespace-only executable names."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("`runner.binary` must not be blank.")
        return normalized
