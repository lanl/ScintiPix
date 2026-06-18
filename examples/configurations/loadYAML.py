"""Simple example: Load a YAML file into a Simulation model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.config.yaml import from_yaml

# Load YAML file
yaml_path = Path(__file__).parent.parent / "yamlFiles" / "EJ200.yaml"
simulation = from_yaml(yaml_path)

# Print results
print(f"Loaded: {yaml_path.name}")
print(f"Scintillator: {simulation.scintillator.properties.name}")
print(f"  Density: {simulation.scintillator.properties.composition.density} g/cm³")
print(f"  Atoms: {simulation.scintillator.properties.composition.atoms}")
print(f"  Scint Yield: {simulation.scintillator.properties.optical.scint_yield} photons/MeV")
print(f"Source: {simulation.source.gps.particle}")
print(f"Energy: {simulation.source.gps.energy.mono_mev} MeV")
