"""Hierarchical Pydantic models for GEANT4 simulation configuration.

This module remains the public compatibility surface for config models while
implementation classes are organized in domain-specific modules under
`src.config.models`.
"""

from __future__ import annotations

from pydantic import AliasChoices, Field, model_validator

from src.config.defaults import default_sim_config_payload
from src.config.models import (
    GpsAngularConfig,
    GpsEnergyConfig,
    GpsPositionConfig,
    IntensifierConfig,
    IntensifierInputScreenConfig,
    LensConfig,
    MetadataConfig,
    OpticalConfig,
    OpticalGeometry,
    OpticalTransportAssumptionsConfig,
    RunEnvironmentConfig,
    RunEnvironmentOutputInfo,
    RunnerConfig,
    RuntimeControlsConfig,
    ScintillationTimeComponent,
    ScintillationTimeComponentsByExcitation,
    ScintillatorConfig,
    ScintillatorProperties,
    SensorConfig,
    SensitiveDetectorConfig,
    SimulationConfig,
    Size3Mm,
    SourceConfig,
    SourceGpsConfig,
    SourceTimingConfig,
    StrictModel,
    Vec3,
    Vec3Mm,
)


class SimConfig(StrictModel):
    """Top-level simulation configuration root.

    The `metadata` field accepts either `metadata` or aliased `Metadata` in
    input YAML and serializes back out as `Metadata` for consistency with
    project examples.
    """

    scintillator: ScintillatorConfig
    source: SourceConfig
    optical: OpticalConfig
    intensifier: IntensifierConfig | None = None
    sensor: SensorConfig | None = None
    simulation: SimulationConfig | None = None
    runner: RunnerConfig = Field(default_factory=RunnerConfig)
    metadata: MetadataConfig = Field(
        validation_alias=AliasChoices("Metadata", "metadata"),
        serialization_alias="Metadata",
    )

    @model_validator(mode="after")
    def validate_scintillation_profile_selection(self) -> "SimConfig":
        """Ensure configured source particle has a resolvable time profile."""

        properties = self.scintillator.properties
        if properties is not None:
            properties.time_components.resolve_for_particle(self.source.gps.particle)
        return self


def default_sim_config() -> SimConfig:
    """Return a minimal valid configuration for bootstrapping/tests."""

    return SimConfig.model_validate(default_sim_config_payload())


__all__ = [
    "StrictModel",
    "Vec3Mm",
    "Size3Mm",
    "Vec3",
    "ScintillationTimeComponent",
    "ScintillationTimeComponentsByExcitation",
    "ScintillatorProperties",
    "ScintillatorConfig",
    "GpsPositionConfig",
    "GpsAngularConfig",
    "GpsEnergyConfig",
    "SourceGpsConfig",
    "SourceTimingConfig",
    "SourceConfig",
    "LensConfig",
    "OpticalGeometry",
    "SensitiveDetectorConfig",
    "OpticalTransportAssumptionsConfig",
    "OpticalConfig",
    "IntensifierInputScreenConfig",
    "IntensifierConfig",
    "SensorConfig",
    "RunEnvironmentOutputInfo",
    "RunEnvironmentConfig",
    "MetadataConfig",
    "RuntimeControlsConfig",
    "SimulationConfig",
    "RunnerConfig",
    "SimConfig",
    "default_sim_config",
]
