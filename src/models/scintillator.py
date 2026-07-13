"""Scintillator configuration models."""

from __future__ import annotations

import math

from pydantic import AliasChoices, Field, model_validator

from src.common.utilities import ValueWithUnit, extract_numeric_value, convert_time_to_ns, convert_density_to_g_cm3, convert_scint_yield_to_per_mev
from .base import Size3Mm, StrictModel, Vec3Mm


class CurveReference(StrictModel):
    """Reference to an external curve file with unit metadata.

    Used in catalog files to reference optical property curves stored as
    separate CSV/data files.
    """

    path: str = Field(min_length=1, description="Relative or absolute path to curve file")
    x_unit: str = Field(alias="xUnit", min_length=1, description="Unit for x-axis (energy)")
    y_unit: str = Field(alias="yUnit", min_length=1, description="Unit for y-axis (property value)")


class OpticalCurves(StrictModel):
    """Collection of optical curve references for catalog files."""

    r_index: CurveReference = Field(alias="rIndex")
    abs_length: CurveReference | None = Field(default=None, alias="absLength")
    scint_spectrum: CurveReference | None = Field(default=None, alias="scintSpectrum")


class OpticalConstants(StrictModel):
    """Optical constants for scintillator material (catalog format)."""

    scint_yield: ValueWithUnit = Field(alias="scintYield")
    resolution_scale: float = Field(alias="resolutionScale")
    time_components: "ScintillationTimeComponentsByExcitation" = Field(alias="timeComponents")

    @model_validator(mode="after")
    def validate_positive_values(self) -> "OpticalConstants":
        """Validate that resolution_scale is positive."""
        if self.resolution_scale <= 0:
            raise ValueError("resolution_scale must be > 0")
        if self.scint_yield.value <= 0:
            raise ValueError("scint_yield value must be > 0")
        return self


class ScintillationTimeComponent(StrictModel):
    """Single scintillation decay component.

    Time constant can be specified as a float (assumed nanoseconds) or as
    ValueWithUnit for explicit units.
    """

    time_constant: ValueWithUnit | float = Field(alias="timeConstant")
    yield_fraction: float = Field(alias="yieldFraction", ge=0)

    @model_validator(mode="after")
    def validate_time_constant(self) -> "ScintillationTimeComponent":
        """Require a non-negative decay time."""

        if extract_numeric_value(self.time_constant, converter=convert_time_to_ns) < 0:
            raise ValueError("time_constant must be >= 0")
        return self

    @property
    def time_constant_ns(self) -> float:
        """Get time constant in nanoseconds."""
        return extract_numeric_value(self.time_constant, converter=convert_time_to_ns)


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
        components: list["ScintillationTimeComponent"],
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

        # Check for at least one active component
        active_component_count = 0
        for component in components:
            # Extract numeric time_constant value
            time_value = extract_numeric_value(
                component.time_constant,
                converter=convert_time_to_ns
            )
            if component.yield_fraction > 0.0 and time_value > 0.0:
                active_component_count += 1

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

class ScintillatorComposition(StrictModel):
    """Composition information of scintillator material.

    Density can be specified as a float (g/cm³) or as ValueWithUnit for explicit
    units. Elements are specified as a dictionary mapping element symbols to atom counts.

    Examples:
        >>> # Catalog format with unit
        >>> ScintillatorComposition(
        ...     density={"value": 1.05, "unit": "g/cm3"},
        ...     atoms={"C": 9, "H": 10}
        ... )
        >>> # Simulation format without unit
        >>> ScintillatorComposition(density=1.05, atoms={"C": 9, "H": 10})
    """

    density: ValueWithUnit | float
    atoms: dict[str, int] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_composition(self) -> "ScintillatorComposition":
        """Require positive density and atom counts."""

        density = extract_numeric_value(
            self.density,
            converter=convert_density_to_g_cm3,
        )
        if density <= 0:
            raise ValueError("density must be > 0")
        if any(count <= 0 for count in self.atoms.values()):
            raise ValueError("atom counts must be > 0")
        return self


class ScintillatorOpticalProperties(StrictModel):
    """Optical properties of scintillator material.

    Supports two formats:
    1. Catalog format: curves/constants structure with CurveReferences and ValueWithUnit
    2. Simulation format: flat structure with inline arrays and numeric values

    The catalog loader transforms format 1 → format 2 during hydration.
    """

    # Catalog format: nested structure
    curves: "OpticalCurves | None" = None
    constants: "OpticalConstants | None" = None

    # Simulation format: flat structure with inline data
    photon_energy: list[float] | None = Field(default=None, alias="photonEnergy")
    r_index: list[float] | None = Field(default=None, alias="rIndex")
    r_index_file: str | None = Field(default=None, alias="rIndexFile")
    abs_length: list[float] | None = Field(default=None, alias="absLength")
    abs_length_file: str | None = Field(default=None, alias="absLengthFile")
    scint_spectrum: list[float] | None = Field(default=None, alias="scintSpectrum")
    scint_spectrum_file: str | None = Field(default=None, alias="scintSpectrumFile")
    n_k_entries: int | None = Field(default=None, alias="nKEntries", gt=0)
    time_components: "ScintillationTimeComponentsByExcitation | None" = Field(
        default=None, alias="timeComponents"
    )
    scint_yield: ValueWithUnit | float | None = Field(default=None, alias="scintYield")
    resolution_scale: float | None = Field(default=None, alias="resolutionScale")

    @model_validator(mode="after")
    def validate_format(self) -> "ScintillatorOpticalProperties":
        """Validate that either catalog or simulation format is used consistently."""
        has_simulation_format = (
            self.photon_energy is not None
            or self.r_index is not None
            or self.r_index_file is not None
        )
        has_catalog_format = self.curves is not None or self.constants is not None

        if not has_catalog_format and self.r_index is None and self.r_index_file is None:
            raise ValueError("rIndex or rIndexFile must be provided")

        # Validate positive values
        if self.resolution_scale is not None and self.resolution_scale <= 0:
            raise ValueError("resolution_scale must be > 0")

        if self.scint_yield is not None:
            if isinstance(self.scint_yield, (int, float)) and self.scint_yield <= 0:
                raise ValueError("scint_yield must be > 0")
            elif isinstance(self.scint_yield, ValueWithUnit) and self.scint_yield.value <= 0:
                raise ValueError("scint_yield value must be > 0")

        if self.n_k_entries is not None and self.n_k_entries <= 0:
            raise ValueError("n_k_entries must be > 0")

        # Both formats can coexist during transformation, so just validate internal consistency
        if has_simulation_format:
            # Validate simulation format consistency
            for value_field, file_field in [
                ("r_index", "r_index_file"),
                ("abs_length", "abs_length_file"),
                ("scint_spectrum", "scint_spectrum_file"),
            ]:
                if getattr(self, value_field) and getattr(self, file_field):
                    raise ValueError(
                        f"Cannot specify both {value_field} and {file_field}"
                    )

            if self.r_index is None and self.r_index_file is None:
                raise ValueError("Must provide rIndex or rIndexFile")

            # If inline arrays are used, validate grid consistency
            inline_arrays = [self.r_index, self.abs_length, self.scint_spectrum]
            if any(arr is not None for arr in inline_arrays):
                if self.photon_energy is None:
                    raise ValueError("photonEnergy required when inline curves are used")
                if self.n_k_entries is None:
                    raise ValueError("nKEntries required when inline curves are used")

                if len(self.photon_energy) != self.n_k_entries:
                    raise ValueError("photonEnergy length must match nKEntries")
                for arr, name in zip(inline_arrays, ["rIndex", "absLength", "scintSpectrum"]):
                    if arr is not None and len(arr) != self.n_k_entries:
                        raise ValueError(f"{name} length must match nKEntries")

        return self
    
    

class ScintillatorProperties(StrictModel):
    """Complete scintillator material definition.

    Combines material composition and optical properties in a nested structure
    that aligns with catalog file format.

    Supports both:
    - Catalog format: id, name, description, composition, optical (with curves/constants)
    - Simulation format: name, composition, optical (flat with inline data)
    """

    id: str | None = None  # Catalog format only
    name: str
    description: str | None = None  # Catalog format only
    composition: ScintillatorComposition
    optical: ScintillatorOpticalProperties

class ScintillatorFieldOfView(StrictModel):
    """Defines the field of view (FOV) of the scintillator in millimeters.

    This is used to determine the required magnification and lens selection
    to image the scintillator onto the intensifier active area. 
    
    The default is the dimension of the scintillator itself, but users can specify a smaller FOV to only image a portion of the scintillator, or a larger FOV to include some surrounding area. The optics stage will use this FOV along with the lens prescription and intensifier active area to calculate the optimal working distance and element spacing for the desired magnification.  
       
    """
    width_mm: float = Field(alias="widthMm", gt=0)
    height_mm: float = Field(alias="heightMm", gt=0)

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
    field_of_view: ScintillatorFieldOfView | None = Field(
        default=None,
        alias="fieldOfView",
    )   
    
    @model_validator(mode="after")
    def require_properties_or_catalog(self) -> "Scintillator":
        """Require either explicit properties or a catalog reference."""

        if self.catalog_id is None and self.properties is None:
            raise ValueError(
                "`scintillator` must provide `properties` and/or `catalogId`."
            )
        return self

    @model_validator(mode="after")
    def default_field_of_view(self) -> "Scintillator":
        """Default field of view to scintillator dimensions if not specified."""

        if self.field_of_view is None:
            self.field_of_view = ScintillatorFieldOfView(
                width_mm=self.dimension_mm.x_mm,
                height_mm=self.dimension_mm.y_mm,
            )
        return self
