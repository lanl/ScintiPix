"""Top-level Pydantic model for ScintiPix simulation configuration."""

from __future__ import annotations

from .base import StrictModel
from .geant4runtime import Geant4RunTime
from .intensifier import Intensifier
from .metadata import Metadata
from .optics import Optics
from .scintillator import Scintillator
from .sensor import Sensor
from .source import Source


class Simulation(StrictModel):
    """Top-level ScintiPix simulation configuration."""

    source: Source
    scintillator: Scintillator
    geant4runner: Geant4RunTime
    metadata: Metadata
    optical: Optics | None = None
    intensifier: Intensifier | None = None
    sensor: Sensor | None = None
