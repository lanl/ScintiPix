"""Geant4 run-command settings and Python runner launch options."""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from .base import StrictModel


class Geant4RuntimeControls(StrictModel):
    """Optional Geant4 macro preamble controls.

    These fields map to verbosity, progress, and trajectory commands that are
    emitted before `/run/initialize` and `/run/beamOn`.
    """

    control_verbose: int | None = Field(default=None, alias="controlVerbose", ge=0)
    run_verbose: int | None = Field(default=None, alias="runVerbose", ge=0)
    event_verbose: int | None = Field(default=None, alias="eventVerbose", ge=0)
    tracking_verbose: int | None = Field(default=None, alias="trackingVerbose", ge=0)
    print_progress: int | None = Field(default=None, alias="printProgress", gt=0)
    store_trajectory: bool | None = Field(default=None, alias="storeTrajectory")

    @model_validator(mode="after")
    def require_at_least_one_control(self) -> "Geant4RuntimeControls":
        """Reject an empty `runtimeControls` block."""

        has_control = any(
            value is not None
            for value in (
                self.control_verbose,
                self.run_verbose,
                self.event_verbose,
                self.tracking_verbose,
                self.print_progress,
                self.store_trajectory,
            )
        )
        if not has_control:
            raise ValueError(
                "`simulation.runtimeControls` must set at least one control value."
            )
        return self


class Geant4OutputConfig(StrictModel):
    """Select which Geant4 simulation output tables are written."""

    primaries: bool = True
    secondaries: bool = True
    photons: bool = True

    @model_validator(mode="after")
    def require_at_least_one_table(self) -> "Geant4OutputConfig":
        """Reject output config that disables every table."""

        if not (self.primaries or self.secondaries or self.photons):
            raise ValueError("`geant4runner.output` must enable at least one table.")
        return self

class ResolutionTarget(StrictModel):
    """Configuration for the Geant4-side resolution target (Siemens star)."""

    enabled: bool = Field(default=False, alias="resolutionTargetEnabled")
    outer_radius_mm: float = Field(
        default=100.0, alias="resolutionTargetOuterRadiusMm", gt=0.0
    )
    line_pairs: int = Field(
        default=64, alias="resolutionTargetLinePairs", gt=0
    )

class PhotonCullingConfig(StrictModel):
    """Photon culling optimization settings.

    When enabled, photons emitted away from the detector are not tracked,
    reducing simulation time while maintaining accuracy for detected photons.
    """

    enabled: bool = False
    acceptance_angle_deg: float = Field(
        default=30.0, alias="acceptanceAngleDeg", gt=0.0, le=180.0
    )


class Geant4RunTime(StrictModel):
    """Geant4 run-command settings for one simulation run.

    `numberOfParticles` maps to `/run/beamOn`. `runtimeControls` maps to
    optional macro preamble commands for verbosity, progress, and trajectory
    storage.
    """

    number_of_particles: int | None = Field(
        default=None, alias="numberOfParticles", gt=0
    )
    runtime_controls: Geant4RuntimeControls | None = Field(
        default=None, alias="runtimeControls"
    )
    events_per_output: int = Field(default=1000, alias="eventsPerOutput", gt=0)
    output: Geant4OutputConfig = Field(default_factory=Geant4OutputConfig)
    photon_culling: PhotonCullingConfig = Field(
        default_factory=PhotonCullingConfig, alias="photonCulling"
    )
    resolution_target: ResolutionTarget = Field(
        default_factory=ResolutionTarget, alias="resolutionTarget"
    )

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

    @model_validator(mode="after")
    def require_at_least_one_setting(self) -> "Geant4RunTime":
        """Reject an empty `simulation` block."""

        if self.number_of_particles is None and self.runtime_controls is None:
            raise ValueError(
                "`simulation` must include `numberOfParticles` and/or `runtimeControls`."
            )
        return self
