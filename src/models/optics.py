"""Optical subsystem configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, model_validator

from .base import StrictModel, Vec3Mm


class FocusGap(StrictModel):
    """Definition of a lens gap that moves during focusing.

    Each focus gap has a default thickness and responds to the focus
    adjustment (zfine) with a specific scaling factor.
    """

    gap_index: int = Field(alias="gapIndex", ge=0, description="Index of the gap in the lens sequential model")
    default_thickness_mm: float = Field(
        alias="defaultThickness",
        ge=0.0,
        description="Default thickness in mm when lens is at reference focus position",
    )
    scaling_factor: float = Field(
        default=1.0,
        alias="scalingFactor",
        description="How much this gap moves per unit of focus adjustment (can be negative for compensating groups)",
    )


class Lens(StrictModel):
    """Individual optical lens descriptor.

    A lens can be specified either directly with `zmxFile` (and optional
    `smxFile`) or via `catalogId` resolved from `catalogs/lenses/catalog.yaml`.
    `primary` indicates which lens entry should be treated as the principal
    lens for downstream assumptions.
    """

    name: str | None = None
    description: str = ""
    primary: bool = False
    catalog_id: str | None = Field(default=None, alias="catalogId", min_length=1)
    zmx_file: str | None = Field(default=None, alias="zmxFile", min_length=1)
    smx_file: str | None = Field(default=None, alias="smxFile", min_length=1)
    focus_gaps: list[FocusGap] | None = Field(
        default=None,
        alias="focusGaps",
        description="Definition of which gaps move during focusing (loaded from catalog or user-provided)",
    )
    focus_adjustment_mm: float | None = Field(
        default=None,
        alias="focusAdjustmentMm",
        description="Internal lens focus adjustment (zfine) applied to achieve focus at image plane",
    )
    focus_adjustment_bounds_mm: tuple[float, float] | None = Field(
        default=None,
        alias="focusAdjustmentBoundsMm",
        description="Physically attainable interval for internal lens focus adjustment",
    )
    back_focus_mm: float | None = Field(
        default=None,
        alias="backFocusMm",
        gt=0.0,
        description=(
            "Distance from the last modeled optical surface to the "
            "intensifier photocathode image plane"
        ),
    )
    back_focus_bounds_mm: tuple[float, float] | None = Field(
        default=None,
        alias="backFocusBoundsMm",
        description=(
            "Physically attainable back-focus interval imposed by the lens "
            "mount, adapter, and intensifier interface"
        ),
    )

    @model_validator(mode="after")
    def validate_lens_reference(self) -> "Lens":
        """Validate the lens reference, name, and mechanical back focus."""

        if self.catalog_id is None and self.zmx_file is None:
            raise ValueError(
                "Each optical lens must provide `catalogId` and/or `zmxFile`."
            )
        if self.name is None or not self.name.strip():
            if self.catalog_id is not None:
                self.name = self.catalog_id
            elif self.zmx_file is not None:
                self.name = Path(self.zmx_file).stem
            else:
                self.name = "Lens"

        if self.back_focus_bounds_mm is not None:
            lower_mm, upper_mm = self.back_focus_bounds_mm
            if lower_mm <= 0.0 or upper_mm <= 0.0:
                raise ValueError("`backFocusBoundsMm` values must be positive.")
            if lower_mm > upper_mm:
                raise ValueError(
                    "`backFocusBoundsMm` minimum must not exceed its maximum."
                )
            if self.back_focus_mm is not None and not (
                lower_mm <= self.back_focus_mm <= upper_mm
            ):
                raise ValueError(
                    "`backFocusMm` must lie within `backFocusBoundsMm`."
                )

        if self.focus_adjustment_bounds_mm is not None:
            lower_mm, upper_mm = self.focus_adjustment_bounds_mm
            if lower_mm > upper_mm:
                raise ValueError(
                    "`focusAdjustmentBoundsMm` minimum must not exceed its maximum."
                )
            if self.focus_adjustment_mm is not None and not (
                lower_mm <= self.focus_adjustment_mm <= upper_mm
            ):
                raise ValueError(
                    "`focusAdjustmentMm` must lie within `focusAdjustmentBoundsMm`."
                )
        return self


class OpticalInterface(StrictModel):
    """Optical interface (scoring plane) configuration.

    The optical interface is a circular scoring plane in Geant4 positioned
    between the scintillator and the lens/PMT system. It records photons
    that exit the scintillator and are accepted by the optical system.
    """

    diameter_mm: float = Field(alias="diameterMm", gt=0)
    position_mm: Vec3Mm = Field(alias="positionMm")
    working_distance_bounds_mm: tuple[float, float] | None = Field(
        default=None,
        alias="workingDistanceBoundsMm",
        description=(
            "Physically attainable scintillator-back-face to lens-entrance interval"
        ),
    )

    @model_validator(mode="after")
    def validate_working_distance_bounds(self) -> "OpticalInterface":
        """Require positive, ordered working-distance bounds."""

        if self.working_distance_bounds_mm is not None:
            lower_mm, upper_mm = self.working_distance_bounds_mm
            if lower_mm <= 0.0 or upper_mm <= 0.0:
                raise ValueError("`workingDistanceBoundsMm` values must be positive.")
            if lower_mm > upper_mm:
                raise ValueError(
                    "`workingDistanceBoundsMm` minimum must not exceed its maximum."
                )
        return self


class OpticalTransportAssumptions(StrictModel):
    """Physical mapping assumptions used by downstream optical transport.

    Definitions:
    - `objectPlane`: origin object plane for lens focus assumptions.
    - `opticalInterfaceRepresents`: physical meaning of Geant4 optical-interface
      hit plane used as ray-tracing input.
    """

    object_plane: Literal["scintillator_back_face"] = Field(
        default="scintillator_back_face",
        validation_alias=AliasChoices("objectPlane", "object_plane"),
        serialization_alias="objectPlane",
    )
    optical_interface_represents: Literal["lens_entrance_plane"] = Field(
        default="lens_entrance_plane",
        validation_alias=AliasChoices(
            "opticalInterfaceRepresents",
            "optical_interface_represents",
        ),
        serialization_alias="opticalInterfaceRepresents",
    )


class Optics(StrictModel):
    """Optical subsystem definition.

    Includes:
    - lens list metadata (optional for PMT-only setups)
    - optical interface (scoring plane) configuration
    - transport progress reporting
    """

    lenses: list[Lens] | None = None
    interface: OpticalInterface
    show_transport_progress: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "showTransportProgress",
            "show_transport_progress",
        ),
        serialization_alias="showTransportProgress",
    )
    transport_assumptions: OpticalTransportAssumptions = Field(
        default_factory=OpticalTransportAssumptions,
        alias="transportAssumptions",
    )

    @model_validator(mode="after")
    def validate_primary_lens_count(self) -> "Optics":
        """Require exactly one primary lens if lenses are specified.

        A single primary lens simplifies downstream assumptions in macro
        generation and geometry bookkeeping.
        """

        if self.lenses is None or len(self.lenses) == 0:
            return self
        primary_count = sum(1 for lens in self.lenses if lens.primary)
        if primary_count != 1:
            raise ValueError("`optical.lenses` must contain exactly one primary lens.")
        return self
