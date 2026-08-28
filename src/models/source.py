"""Primary source models."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, Field, model_validator

from .base import StrictModel, Vec3, Vec3Mm


class GpsPosition(StrictModel):
    """GPS position distribution."""

    type: str = Field(default="Plane", min_length=1)
    shape: str = Field(default="Circle", min_length=1)
    center_mm: Vec3Mm = Field(alias="centerMm")
    radius_mm: float = Field(alias="radiusMm", gt=0)


class GpsAngular(StrictModel):
    """GPS angular distribution."""

    type: str = Field(default="beam2d", min_length=1)
    rot1: Vec3 = Field(default_factory=lambda: Vec3(x=1.0, y=0.0, z=0.0))
    rot2: Vec3 = Field(default_factory=lambda: Vec3(x=0.0, y=1.0, z=0.0))
    direction: Vec3 = Field(default_factory=lambda: Vec3(x=0.0, y=0.0, z=1.0))


class GpsEnergy(StrictModel):
    """GPS energy distribution.

    `type` names the Geant4 GPS energy distribution. `Mono` uses the single
    `monoMeV` value. `AmBe` samples the committed AmBe neutron energy spectrum
    (`catalogs/sources/AmBe/emerging_neutron_spectrum.csv`), which the macro
    writes out as a GPS arbitrary-energy histogram.
    """

    type: str = Field(default="Mono", min_length=1)
    mono_mev: float | None = Field(default=None, alias="monoMeV", gt=0)

    @model_validator(mode="after")
    def validate_energy_payload(self) -> "GpsEnergy":
        """Require mono energy value when GPS type is Mono."""

        if self.type.strip().lower() == "mono" and self.mono_mev is None:
            raise ValueError("`source.gps.energy.monoMeV` is required when type is 'Mono'.")
        return self


class SourceGps(StrictModel):
    """Explicit GPS command payload nested under source.

    `particle` and `energy` may be omitted when the parent `Source` names a
    `catalogId`; the source catalog fills them during hydration. `position` is
    always required, because where a source sits is specific to each simulation
    and is never a property of the source type.
    """

    particle: str | None = Field(default=None, min_length=1)
    position: GpsPosition
    angular: GpsAngular = Field(default_factory=GpsAngular)
    energy: GpsEnergy | None = None


class SourceTiming(StrictModel):
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
    def validate_mode_payload(self) -> "SourceTiming":
        """Require the timing fields needed by each ured mode."""

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


class CorrelatedGamma(StrictModel):
    """Optional 4.439 MeV gamma emitted with each AmBe neutron.

    Presence of this block turns the coincident gamma on in the primary
    generator; the gamma energy is fixed in the simulation code. `probability`
    is the chance per neutron that the gamma is emitted (Falezza et al. report
    about 0.582 for their source).
    """

    probability: float = Field(gt=0.0, le=1.0)


class Source(StrictModel):
    """Primary source block represented directly as GPS configuration.

    A source can be spelled out inline (a full `gps` block) or selected from
    the source catalog with `catalogId`, which fills the intrinsic fields
    (particle, angular distribution, energy, coincident gamma) during
    hydration. Either way the `gps.position` placement is given here.
    """

    gps: SourceGps
    catalog_id: str | None = Field(default=None, alias="catalogId", min_length=1)
    timing: SourceTiming | None = None
    correlated_gamma: CorrelatedGamma | None = Field(
        default=None, alias="correlatedGamma"
    )

    @model_validator(mode="after")
    def require_inline_or_catalog(self) -> "Source":
        """Require an inline particle and energy unless a catalog id is given."""

        if self.catalog_id is None:
            missing = [
                name
                for name, value in (
                    ("particle", self.gps.particle),
                    ("energy", self.gps.energy),
                )
                if value is None
            ]
            if missing:
                joined = ", ".join(f"`source.gps.{name}`" for name in missing)
                raise ValueError(
                    f"{joined} required unless `source.catalogId` is set."
                )
        return self
