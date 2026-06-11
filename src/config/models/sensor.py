"""Sensor configuration models."""

from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator

from .base import StrictModel


class SensorConfig(StrictModel):
    """Downstream sensor/readout configuration."""

    class TimepixConfig(StrictModel):
        """Timepix sensor geometry and simplified readout settings."""

        pixels_x: int = Field(
            default=256,
            validation_alias=AliasChoices("pixels_x", "pixelsX"),
            serialization_alias="pixels_x",
            gt=0,
        )
        pixels_y: int = Field(
            default=256,
            validation_alias=AliasChoices("pixels_y", "pixelsY"),
            serialization_alias="pixels_y",
            gt=0,
        )
        pixel_pitch_mm: float = Field(
            default=0.055,
            validation_alias=AliasChoices("pixel_pitch_mm", "pixelPitchMm"),
            serialization_alias="pixel_pitch_mm",
            gt=0.0,
        )
        max_tot_ns: float = Field(
            default=25550.0,
            validation_alias=AliasChoices("max_tot_ns", "maxTotNs"),
            serialization_alias="max_tot_ns",
            gt=0.0,
        )
        dead_time_ns: float = Field(
            default=475.0,
            validation_alias=AliasChoices("dead_time_ns", "deadTimeNs"),
            serialization_alias="dead_time_ns",
            ge=0.0,
        )

    model: str = Field(min_length=1)
    timepix: TimepixConfig

    @field_validator("model")
    @classmethod
    def require_non_blank_model(cls, value: str) -> str:
        """Reject blank/whitespace-only sensor model names."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("`sensor.model` must not be blank.")
        return normalized
