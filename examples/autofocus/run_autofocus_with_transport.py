"""Run autofocus, Geant4 simulation, and optical transport.

This example runs the simulation workflow:
1. Automatic lens focusing to optimize working distance and lens parameters
2. Geant4 simulation to generate scintillation photons
3. Optical transport through the lens system to the photocathode

Run ``analyze_autofocus_output.py`` separately to plot the resulting photons.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT))

from src.config.yaml import from_yaml  # noqa: E402
from src.runner.runSimulation import run_simulation  # noqa: E402

DEFAULT_YAML_PATH = (
    REPO_ROOT / "examples" / "yamlFiles" / "autofocus_siemens_star_50mm.yaml"
)


def main() -> None:
    """Run the autofocus simulation with optical transport."""
    if len(sys.argv) > 2:
        raise SystemExit(
            "Usage: python examples/autofocus/run_autofocus_with_transport.py "
            "[path/to/simulation.yaml]"
        )

    yaml_path = (
        Path(sys.argv[1]) if len(sys.argv) == 2 else DEFAULT_YAML_PATH
    ).expanduser().resolve()

    print(f"Loading configuration from: {yaml_path}")
    config = from_yaml(yaml_path)

    # Display workflow stages
    run_controls = config.metadata.run_controls
    print("\nWorkflow stages enabled:")
    print(f"  Auto-focus lens:      {run_controls.auto_focus_lens}")
    print(f"  Geant4 simulation:    {run_controls.geant4_simulation}")
    print(f"  Optical transport:    {run_controls.transportation}")
    print(f"  Intensification:      {run_controls.intensification}")
    print(f"  Sensor detection:     {run_controls.sensor_detection}")

    run_env = config.metadata.run_environment
    print(f"\nOutput directory: {run_env.run_directory}")

    if run_controls.auto_focus_lens:
        print(f"\nAutofocused config will be saved to:")
        print(f"  {run_env.config_directory}/")
        print(f"  {run_env.simulation_run_id}_{run_env.sub_run_number:03d}_focused.yaml")

    print("\nStarting simulation...\n")
    run_simulation(config)

    print("\n" + "=" * 60)
    print("Simulation complete!")
    print("=" * 60)

    # Display output locations
    print("\nOutput files:")
    if run_controls.geant4_simulation:
        print(f"  Simulated photons: {run_env.simulated_photons_directory}/")
    if run_controls.transportation:
        print(f"  Transported photons: {run_env.transported_photons_directory}/")
    if run_controls.auto_focus_lens and run_env.config_directory:
        print(f"  Focused config: {run_env.config_directory}/")


if __name__ == "__main__":
    main()
