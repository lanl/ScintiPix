"""Primary source configuration models."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, Field, model_validator

from .base import StrictModel, Vec3, Vec3Mm


class GpsPositionConfig(StrictModel):
    """GPS position distribution configuration."""

    type: str = Field(default="Plane", min_length=1)
    shape: str = Field(default="Circle", min_length=1)
    center_mm: Vec3Mm = Field(alias="centerMm")
    radius_mm: float = Field(alias="radiusMm", gt=0)


class GpsAngularConfig(StrictModel):
    """GPS angular distribution configuration."""

    type: str = Field(default="beam2d", min_length=1)
    rot1: Vec3 = Field(default_factory=lambda: Vec3(x=1.0, y=0.0, z=0.0))
    rot2: Vec3 = Field(default_factory=lambda: Vec3(x=0.0, y=1.0, z=0.0))
    direction: Vec3 = Field(default_factory=lambda: Vec3(x=0.0, y=0.0, z=1.0))


class GpsEnergyConfig(StrictModel):
    """GPS energy distribution configuration."""

    type: str = Field(default="Mono", min_length=1)
    mono_mev: float | None = Field(default=None, alias="monoMeV", gt=0)

    @model_validator(mode="after")
    def validate_energy_payload(self) -> "GpsEnergyConfig":
        """Require mono energy value when GPS type is Mono."""

        if self.type.strip().lower() == "mono" and self.mono_mev is None:
            raise ValueError("`source.gps.energy.monoMeV` is required when type is 'Mono'.")
        return self


class SourceGpsConfig(StrictModel):
    """Explicit GPS command payload nested under source."""

    particle: str = Field(min_length=1)
    position: GpsPositionConfig
    angular: GpsAngularConfig = Field(default_factory=GpsAngularConfig)
    energy: GpsEnergyConfig


class SourceTimingConfig(StrictModel):
    """Optional neutron source timing model in global nanoseconds.

    `none` preserves the current event-local Geant4 timing behavior.
    `continuous` derives one source time per event from particle flux and source
    area. `pulsed` derives the event count assigned to each pulse from particle
    flux, source area, and pulse period, then samples creation time within each
    pulse window during Geant4 primary generation.
    """

    mode: Literal["none", "continuous", "pulsed"] = "none"
    start_time_ns: float = Field(
        default=0.0,
        validation_alias=AliasChoices("start_time_ns", "startTimeNs", "startTime"),
        serialization_alias="start_time_ns",
        ge=0.0,
    )
    particle_flux: float | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "particle_flux",
            "particleFlux",
        ),
        serialization_alias="particle_flux",
        gt=0.0,
    )
    pulse_period_ns: float | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "pulse_period_ns",
            "pulsePeriodNs",
            "pulsePeriod",
        ),
        serialization_alias="pulse_period_ns",
        gt=0.0,
    )
    pulse_time_offset_ns: float = Field(
        default=0.0,
        validation_alias=AliasChoices(
            "pulse_time_offset_ns",
            "pulseTimeOffsetNs",
            "pulseTimeOffset",
        ),
        serialization_alias="pulse_time_offset_ns",
        ge=0.0,
    )
    pulse_time_width_ns: float | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "pulse_time_width_ns",
            "pulseTimeWidthNs",
            "pulseTimeWidth",
        ),
        serialization_alias="pulse_time_width_ns",
        ge=0.0,
    )
    pulse_shape: Literal["uniform"] = Field(
        default="uniform",
        validation_alias=AliasChoices("pulse_shape", "pulseShape"),
        serialization_alias="pulse_shape",
    )

    @model_validator(mode="after")
    def validate_mode_payload(self) -> "SourceTimingConfig":
        """Require the timing fields needed by each configured mode."""

        if self.mode in {"continuous", "pulsed"} and self.particle_flux is None:
            raise ValueError(
                "`source.timing.particle_flux` is required when timing mode is "
                "'continuous' or 'pulsed'."
            )
        if self.mode == "pulsed":
            missing = [
                name
                for name, value in (
                    ("pulse_period_ns", self.pulse_period_ns),
                    ("pulse_time_width_ns", self.pulse_time_width_ns),
                )
                if value is None
            ]
            if missing:
                joined = ", ".join(f"`source.timing.{name}`" for name in missing)
                raise ValueError(
                    f"{joined} required when `source.timing.mode` is 'pulsed'."
                )
        return self


class SourceConfig(StrictModel):
    """Primary source block represented directly as GPS configuration."""

    gps: SourceGpsConfig
    timing: SourceTimingConfig | None = None
