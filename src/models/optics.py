"""Optical subsystem configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, model_validator

from .base import StrictModel, Vec3Mm


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

    @model_validator(mode="after")
    def validate_lens_reference(self) -> "Lens":
        """Require lens reference and fill a fallback display name."""

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
        return self


class OpticalInterface(StrictModel):
    """Optical interface (scoring plane) configuration.

    The optical interface is a circular scoring plane in Geant4 positioned
    between the scintillator and the lens/PMT system. It records photons
    that exit the scintillator and are accepted by the optical system.
    """

    diameter_mm: float = Field(alias="diameterMm", gt=0)
    position_mm: Vec3Mm = Field(alias="positionMm")


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
