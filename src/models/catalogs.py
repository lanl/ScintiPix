"""Catalog index models for bundled ScintiPix definitions."""

from __future__ import annotations

from pydantic import Field, model_validator

from .base import StrictModel
from .optics import Lens
from .scintillator import ScintillatorProperties


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
