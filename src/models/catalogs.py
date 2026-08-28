"""Catalog index models for bundled ScintiPix definitions."""

from __future__ import annotations

from pydantic import Field, model_validator

from .base import StrictModel
from .optics import Lens
from .scintillator import ScintillatorProperties
from .source import CorrelatedGamma, GpsAngular, GpsEnergy


class LensCatalogIndex(StrictModel):
    """Top-level lens catalog index."""

    version: int = Field(ge=1)
    default: str = Field(min_length=1)
    lenses: dict[str, Lens] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_default_key(self) -> "LensCatalogIndex":
        if self.default not in self.lenses:
            raise ValueError(
                f"catalog default '{self.default}' not found in lenses mapping."
            )
        return self


class ScintillatorCatalogIndex(StrictModel):
    """Top-level scintillator catalog index."""

    version: int = Field(ge=1)
    default: str = Field(min_length=1)
    materials: dict[str, str | ScintillatorProperties] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_default_key(self) -> "ScintillatorCatalogIndex":
        if self.default not in self.materials:
            raise ValueError(
                f"catalog default '{self.default}' not found in materials mapping."
            )
        return self


class SourceCatalogEntry(StrictModel):
    """One source-catalog entry: the intrinsic parameters of a source type.

    Holds only what is intrinsic to the source itself (particle, angular
    distribution, energy, optional coincident gamma). Placement (`gps.position`)
    and `timing` are simulation-specific and are given in the `source` block,
    not here. `kind` is a descriptive tag: 'radioactive-source', 'beam', or
    'generator'.
    """

    kind: str = Field(min_length=1)
    particle: str = Field(min_length=1)
    angular: GpsAngular = Field(default_factory=GpsAngular)
    energy: GpsEnergy
    correlated_gamma: CorrelatedGamma | None = Field(
        default=None, alias="correlatedGamma"
    )


class SourceCatalogIndex(StrictModel):
    """Top-level source catalog index."""

    version: int = Field(ge=1)
    default: str = Field(min_length=1)
    sources: dict[str, SourceCatalogEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_default_key(self) -> "SourceCatalogIndex":
        if self.default not in self.sources:
            raise ValueError(
                f"catalog default '{self.default}' not found in sources mapping."
            )
        return self
