"""Hierarchical Pydantic models for GEANT4 simulation configuration.

This module remains the public compatibility surface for config models while
implementation classes are organized in domain-specific modules under
`src.config.models`.
"""

from __future__ import annotations

from pydantic import AliasChoices, Field, model_validator

from models.base import StrictModel
from models.intensifier import Intensifier
from models.metadata import Metadata
from models.optics import Optics
from models.scintillator import  Scintillator
from models.sensor import Sensor
from models.source import Source
from models.geant4runtime import Geant4RunTime



class Simulation(StrictModel):
    """Top-level simulation class. This controls the overall ScintiPix simulation, including GEANT4, optical transport, intensifier, and sensor components.

    """

    source: Source
    scintillator: Scintillator
    geant4runner: Geant4RunTime
    metadata: Metadata
    optical: Optics | None = None
    intensifier: Intensifier | None = None
    sensor: Sensor | None = None

