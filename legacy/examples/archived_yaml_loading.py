"""Simple example demonstrating YAML loading for Simulation configuration."""

from pathlib import Path
import sys

# Add src to path for imports
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from config.yaml import from_yaml

def main():
    """Load and print a Simulation configuration from YAML."""

    # Path to example YAML file
    yaml_path = repo_root / "examples" / "yamlFiles" / "EJ200.yaml"

    print(f"Loading configuration from: {yaml_path}")
    print("-" * 80)

    # Load the YAML file
    simulation = from_yaml(yaml_path)

    print("\nSuccessfully loaded Simulation configuration!")
    print("-" * 80)

    # Print some key details
    print(f"\nScintillator:")
    print(f"  Catalog ID: {simulation.scintillator.catalog_id}")
    print(f"  Dimensions (mm): {simulation.scintillator.dimension_mm}")
    print(f"  Position (mm): {simulation.scintillator.position_mm}")

    print(f"\nSource:")
    print(f"  Particle: {simulation.source.gps.particle}")
    print(f"  Energy Type: {simulation.source.gps.energy.type}")
    if simulation.source.gps.energy.mono_mev:
        print(f"  Mono Energy: {simulation.source.gps.energy.mono_mev} MeV")
    if simulation.source.timing:
        print(f"  Timing Mode: {simulation.source.timing.mode}")

    print(f"\nMetadata:")
    print(f"  Author: {simulation.metadata.author}")
    print(f"  Date: {simulation.metadata.date}")
    print(f"  Version: {simulation.metadata.version}")
    print(f"  Run ID: {simulation.metadata.run_environment.simulation_run_id}")

    if simulation.geant4runner:
        print(f"\nGeant4 Runner:")
        print(f"  Binary: {simulation.geant4runner.binary}")
        if simulation.geant4runner.number_of_particles:
            print(f"  Particles: {simulation.geant4runner.number_of_particles}")

    if simulation.optical:
        print(f"\nOptical System:")
        print(f"  Entrance Diameter: {simulation.optical.geometry.entrance_diameter} mm")
        if simulation.optical.lenses:
            print(f"  Lenses: {len(simulation.optical.lenses)} configured")

    if simulation.intensifier:
        print(f"\nIntensifier:")
        print(f"  Model: {simulation.intensifier.model}")

    if simulation.sensor:
        print(f"\nSensor:")
        print(f"  Model: {simulation.sensor.model}")

    print("\n" + "=" * 80)
    print("YAML loading test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
