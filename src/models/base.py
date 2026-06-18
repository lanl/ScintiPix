"""Shared base models and primitive vectors for simulation config schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model with strict validation defaults.

    Shared behavior for every config block:
    - unknown keys are rejected (`extra=\"forbid\"`)
    - either field-name or alias input is accepted (`populate_by_name=True`)
    - assignment after construction is revalidated (`validate_assignment=True`)
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        validate_assignment=True,
    )


class Vec3Mm(StrictModel):
    """Generic 3D coordinate vector in millimeters.

    Used for positions where negative values may be valid.
    """

    x_mm: float
    y_mm: float
    z_mm: float


class Size3Mm(StrictModel):
    """3D size/extent vector in millimeters.

    Unlike :class:`Vec3Mm`, every component must be strictly positive.
    """

    x_mm: float = Field(gt=0)
    y_mm: float = Field(gt=0)
    z_mm: float = Field(gt=0)


class Vec3(StrictModel):
    """Unitless 3D vector used by GPS angular command blocks."""

    x: float
    y: float
    z: float
