"""Intensifier configuration models."""

from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator, model_validator

from .base import StrictModel


class IntensifierInputScreenConfig(StrictModel):
    """Usable active area on the intensifier input plane."""

    image_circle_diameter_mm: float = Field(
        gt=0.0,
        validation_alias=AliasChoices(
            "image_circle_diameter_mm",
            "imageCircleDiameterMm",
        ),
        serialization_alias="image_circle_diameter_mm",
    )
    center_mm: tuple[float, float] = Field(
        default=(0.0, 0.0),
        validation_alias=AliasChoices("center_mm", "centerMm"),
        serialization_alias="center_mm",
    )
    magnification: float = Field(default=1.0, gt=0.0)
    coordinate_frame: str = Field(
        default="intensifier_input_plane",
        validation_alias=AliasChoices("coordinate_frame", "coordinateFrame"),
        serialization_alias="coordinate_frame",
        min_length=1,
    )
    notes: str | None = None

    @field_validator("center_mm", mode="before")
    @classmethod
    def normalize_center_mm(cls, value: object) -> tuple[float, float]:
        """Accept center as `[x, y]`, `(x, y)`, or `{x_mm, y_mm}`."""

        if value is None:
            return (0.0, 0.0)
        if isinstance(value, (tuple, list)):
            if len(value) != 2:
                raise ValueError("`center_mm` must contain exactly two values: [x_mm, y_mm].")
            return (float(value[0]), float(value[1]))
        if isinstance(value, dict):
            keys = set(value.keys())
            if {"x_mm", "y_mm"}.issubset(keys):
                return (float(value["x_mm"]), float(value["y_mm"]))
            if {"x", "y"}.issubset(keys):
                return (float(value["x"]), float(value["y"]))
        raise ValueError(
            "`center_mm` must be [x_mm, y_mm], [x, y], "
            "or a mapping with either `{x_mm, y_mm}` or `{x, y}`."
        )


class IntensifierConfig(StrictModel):
    """Image-intensifier model metadata and active input-screen definition."""

    class PhotocathodeStageConfig(StrictModel):
        """Photocathode response parameters for the intensifier model."""

        qe_wavelength_nm: list[float] = Field(
            default_factory=lambda: [350.0, 500.0, 650.0],
            validation_alias=AliasChoices("qe_wavelength_nm", "qeWavelengthNm"),
            serialization_alias="qe_wavelength_nm",
            min_length=1,
        )
        qe_values: list[float] = Field(
            default_factory=lambda: [0.15, 0.25, 0.05],
            validation_alias=AliasChoices("qe_values", "qeValues"),
            serialization_alias="qe_values",
            min_length=1,
        )
        collection_efficiency: float = Field(
            default=1.0,
            validation_alias=AliasChoices(
                "collection_efficiency",
                "collectionEfficiency",
            ),
            serialization_alias="collection_efficiency",
            ge=0.0,
            le=1.0,
        )
        tts_sigma_ns: float = Field(
            default=0.0,
            validation_alias=AliasChoices("tts_sigma_ns", "ttsSigmaNs"),
            serialization_alias="tts_sigma_ns",
            ge=0.0,
        )

        @model_validator(mode="after")
        def validate_qe_tables(self) -> "IntensifierConfig.PhotocathodeStageConfig":
            if len(self.qe_wavelength_nm) != len(self.qe_values):
                raise ValueError(
                    "`intensifier.photocathode.qe_wavelength_nm` and "
                    "`intensifier.photocathode.qe_values` must have the same length."
                )
            if any(
                later < earlier
                for earlier, later in zip(
                    self.qe_wavelength_nm,
                    self.qe_wavelength_nm[1:],
                )
            ):
                raise ValueError(
                    "`intensifier.photocathode.qe_wavelength_nm` must be monotonic increasing."
                )
            if any(value < 0.0 or value > 1.0 for value in self.qe_values):
                raise ValueError(
                    "`intensifier.photocathode.qe_values` must lie in [0, 1]."
                )
            return self

    class McpStageConfig(StrictModel):
        """Dual-stage MCP parameters for the intensifier model."""

        stage1_mean_gain: float = Field(
            default=8.0,
            validation_alias=AliasChoices("stage1_mean_gain", "stage1MeanGain"),
            serialization_alias="stage1_mean_gain",
            gt=0.0,
        )
        stage1_gain_shape: float = Field(
            default=2.0,
            validation_alias=AliasChoices("stage1_gain_shape", "stage1GainShape"),
            serialization_alias="stage1_gain_shape",
            gt=0.0,
        )
        stage2_mean_gain: float = Field(
            default=800.0,
            validation_alias=AliasChoices("stage2_mean_gain", "stage2MeanGain"),
            serialization_alias="stage2_mean_gain",
            gt=0.0,
        )
        stage2_gain_shape: float = Field(
            default=2.0,
            validation_alias=AliasChoices("stage2_gain_shape", "stage2GainShape"),
            serialization_alias="stage2_gain_shape",
            gt=0.0,
        )
        gain_ref: float = Field(
            default=1000.0,
            validation_alias=AliasChoices("gain_ref", "gainRef"),
            serialization_alias="gain_ref",
            gt=0.0,
        )
        spread_sigma0_mm: float = Field(
            default=0.03,
            validation_alias=AliasChoices("spread_sigma0_mm", "spreadSigma0Mm"),
            serialization_alias="spread_sigma0_mm",
            ge=0.0,
        )
        spread_gain_exponent: float = Field(
            default=0.4,
            validation_alias=AliasChoices(
                "spread_gain_exponent",
                "spreadGainExponent",
            ),
            serialization_alias="spread_gain_exponent",
        )

    class PhosphorStageConfig(StrictModel):
        """Phosphor response parameters for the intensifier model."""

        phosphor_gain: float = Field(
            default=1.0,
            validation_alias=AliasChoices("phosphor_gain", "phosphorGain"),
            serialization_alias="phosphor_gain",
            gt=0.0,
        )
        decay_fast_ns: float = Field(
            default=70.0,
            validation_alias=AliasChoices("decay_fast_ns", "decayFastNs"),
            serialization_alias="decay_fast_ns",
            ge=0.0,
        )
        decay_slow_ns: float = Field(
            default=200.0,
            validation_alias=AliasChoices("decay_slow_ns", "decaySlowNs"),
            serialization_alias="decay_slow_ns",
            ge=0.0,
        )
        fast_fraction: float = Field(
            default=0.9,
            validation_alias=AliasChoices("fast_fraction", "fastFraction"),
            serialization_alias="fast_fraction",
            ge=0.0,
            le=1.0,
        )
        psf_sigma_mm: float = Field(
            default=0.04,
            validation_alias=AliasChoices("psf_sigma_mm", "psfSigmaMm"),
            serialization_alias="psf_sigma_mm",
            ge=0.0,
        )

    model: str = Field(min_length=1)
    write_output_hdf5: bool = Field(
        default=False,
        validation_alias=AliasChoices("write_output_hdf5", "writeOutputHdf5"),
        serialization_alias="write_output_hdf5",
    )
    input_screen: IntensifierInputScreenConfig = Field(
        validation_alias=AliasChoices("input_screen", "inputScreen"),
        serialization_alias="input_screen",
    )
    photocathode: PhotocathodeStageConfig = Field(default_factory=PhotocathodeStageConfig)
    mcp: McpStageConfig = Field(default_factory=McpStageConfig)
    phosphor: PhosphorStageConfig = Field(default_factory=PhosphorStageConfig)
