#!/usr/bin/env python3
"""Example script to generate a GEANT4 macro file from a ScintiPix YAML configuration.

This script loads a ScintiPix YAML file, creates a Simulation object,
and writes a corresponding GEANT4 macro file using the existing macro generation utilities.
"""

import sys
from pathlib import Path

try:
    from src.config.yaml import from_yaml
    from src.config.macro import write_macro
except ModuleNotFoundError:
    # Fallback for when script is run from within the examples directory
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.config.yaml import from_yaml
    from src.config.macro import write_macro


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python writeMacro.py <path_to_yaml_file>")
        print("Example: python writeMacro.py ../../yamlFiles/CanonEF50mmf1p0L_example.yaml")
        sys.exit(1)

    yaml_path = Path(sys.argv[1])
    if not yaml_path.is_file():
        print(f"Error: YAML file not found: {yaml_path}")
        sys.exit(1)

    try:
        # Load and hydrate the simulation configuration from YAML
        simulation = from_yaml(yaml_path, hydrate_catalogs=True)
        print(f"Loaded simulation configuration from: {yaml_path}")
        print(f"Simulation run ID: {simulation.metadata.run_environment.simulation_run_id}")
    except Exception as e:
        print(f"Error loading YAML configuration: {e}")
        sys.exit(1)

    try:
        # Generate the macro file path and write the macro
        macro_path = write_macro(simulation)
        print(f"Successfully wrote GEANT4 macro to: {macro_path}")
    except Exception as e:
        print(f"Error writing macro file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()