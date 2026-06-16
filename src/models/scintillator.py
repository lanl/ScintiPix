"""Scintillator configuration models."""

from __future__ import annotations

import math

from pydantic import AliasChoices, Field, model_validator

from .base import Size3Mm, StrictModel, Vec3Mm


class ScintillationTimeComponent(StrictModel):
    """Single scintillation decay component in nanoseconds."""

    time_constant: float = Field(alias="timeConstant", ge=0)
    yield_fraction: float = Field(alias="yieldFraction", ge=0)


class ScintillationTimeComponentsByExcitation(StrictModel):
    """Particle-keyed scintillation component profiles.

    Supported optional profiles:
    - ``default``: generic fallback profile
    - ``neutron``: profile selected for neutron sources
    - ``gamma``: profile selected for gamma sources
    """

    default: list[ScintillationTimeComponent] | None = None
    neutron: list[ScintillationTimeComponent] | None = None
    gamma: list[ScintillationTimeComponent] | None = None

    @staticmethod
    def _validate_profile(
        profile_name: str,
        components: list[ScintillationTimeComponent],
    ) -> None:
        if len(components) != 3:
            raise ValueError(
                f"`timeComponents.{profile_name}` must define exactly 3 components."
            )
        total = sum(component.yield_fraction for component in components)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1.0e-9):
            raise ValueError(
                f"`timeComponents.{profile_name}` yield fractions must sum to ~1.0."
            )
        active_component_count = sum(
            1
            for component in components
            if component.yield_fraction > 0.0 and component.time_constant > 0.0
        )
        if active_component_count == 0:
            raise ValueError(
                f"`timeComponents.{profile_name}` must define at least one active "
                "component (`yieldFraction > 0` and `timeConstant > 0`)."
            )

    @model_validator(mode="after")
    def validate_profiles(self) -> "ScintillationTimeComponentsByExcitation":
        """Require at least one profile and validate each present profile."""

        profile_names = ("default", "neutron", "gamma")
        present = False
        for profile_name in profile_names:
            components = getattr(self, profile_name)
            if components is None:
                continue
            present = True
            self._validate_profile(profile_name, components)
        if not present:
            raise ValueError(
                "`timeComponents` must provide at least one profile: "
                "`default`, `neutron`, or `gamma`."
            )
        return self

    def resolve_for_particle(
        self,
        particle: str,
    ) -> tuple[str, list[ScintillationTimeComponent]]:
        """Select profile for a source particle with fallback handling."""

        token = particle.strip().lower()
        if token in {"neutron", "n"} and self.neutron is not None:
            return "neutron", self.neutron
        if token in {"gamma", "g"} and self.gamma is not None:
            return "gamma", self.gamma
        if self.default is not None:
            return "default", self.default

        available_profiles = [
            profile_name
            for profile_name in ("neutron", "gamma")
            if getattr(self, profile_name) is not None
        ]
        if len(available_profiles) == 1:
            profile_name = available_profiles[0]
            components = getattr(self, profile_name)
            assert components is not None
            return profile_name, components

        raise ValueError(
            "Could not resolve scintillation `timeComponents` profile for "
            f"particle {particle!r}. Provide a matching profile "
            "(`neutron`/`gamma`) or `default`."
        )


class ScintillatorProperties(StrictModel):
    """Optical material table for scintillator definition.

    Fields map directly to common GEANT4 material-property table concepts.
    Core fields (`photonEnergy`, `rIndex`, `nKEntries`, `timeComponents`)
    define mandatory optical behavior, while extended fields enable full
    material and optical-table configuration through macros.
    """

    name: str
    photon_energy: list[float] = Field(alias="photonEnergy", min_length=1)
    r_index: list[float] = Field(alias="rIndex", min_length=1)
    n_k_entries: int = Field(alias="nKEntries", gt=0)
    time_components: ScintillationTimeComponentsByExcitation = Field(
        alias="timeComponents"
    )
    abs_length: list[float] | None = Field(default=None, alias="absLength")
    scint_spectrum: list[float] | None = Field(default=None, alias="scintSpectrum")
    density: float | None = Field(default=None, gt=0)
    carbon_atoms: int | None = Field(default=None, alias="carbonAtoms", gt=0)
    hydrogen_atoms: int | None = Field(default=None, alias="hydrogenAtoms", gt=0)
    scint_yield: float | None = Field(default=None, alias="scintYield", gt=0)
    resolution_scale: float | None = Field(default=None, alias="resolutionScale", gt=0)

    @model_validator(mode="after")
    def validate_table_lengths(self) -> "ScintillatorProperties":
        """Require optical-table cardinality consistency.

        This check ensures both lookup arrays match the declared `nKEntries`
        value so later table construction cannot silently misalign.
        """

        if len(self.photon_energy) != self.n_k_entries:
            raise ValueError("`photonEnergy` length must match `nKEntries`.")
        if len(self.r_index) != self.n_k_entries:
            raise ValueError("`rIndex` length must match `nKEntries`.")
        if self.abs_length is not None and len(self.abs_length) != self.n_k_entries:
            raise ValueError("`absLength` length must match `nKEntries`.")
        if (
            self.scint_spectrum is not None
            and len(self.scint_spectrum) != self.n_k_entries
        ):
            raise ValueError("`scintSpectrum` length must match `nKEntries`.")
        return self


class Scintillator(StrictModel):
    """Scintillator geometry + material properties block."""

    catalog_id: str | None = Field(default=None, alias="catalogId", min_length=1)
    position_mm: Vec3Mm
    dimension_mm: Size3Mm
    mask_radius_mm: float = Field(
        default=0.0,
        validation_alias=AliasChoices("maskRadius", "maskRadiusMm", "mask_radius_mm"),
        serialization_alias="maskRadius",
        ge=0,
    )
    properties: ScintillatorProperties | None = None

    @model_validator(mode="after")
    def require_properties_or_catalog(self) -> "Scintillator":
        """Require either explicit properties or a catalog reference."""

        if self.catalog_id is None and self.properties is None:
            raise ValueError(
                "`scintillator` must provide `properties` and/or `catalogId`."
            )
        return self
