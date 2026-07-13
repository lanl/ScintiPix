"""Run autofocus demonstration with Geant4 simulation and optical transport.

This example demonstrates the complete workflow:
1. Automatic lens focusing to optimize working distance and lens parameters
2. Geant4 simulation to generate scintillation photons
3. Optical transport through the lens system to the photocathode

The autofocused configuration is saved to the config directory for reference.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT))

from src.config.yaml import from_yaml  # noqa: E402
from src.runner.runSimulation import run_simulation  # noqa: E402
from examples.analysis.imaging.plotter import (  # noqa: E402
    image_transported_photons,
    image_scintillator_exit,
)

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

    # Generate scintillator exit image if simulation was enabled
    if run_controls.geant4_simulation:
        simulated_bin = Path(run_env.simulated_photons_directory) / "photons.bin"
        if simulated_bin.exists():
            print("\n" + "=" * 60)
            print("Generating scintillator exit image (Siemens star pattern)...")
            print("=" * 60)

            output_image = Path(run_env.run_directory) / "scintillator_exit.png"

            try:
                image_scintillator_exit(
                    simulated_bin,
                    bins=100,
                    extent_mm=25,
                    cmap="gray",
                    log_scale=False,
                    output_path=output_image,
                    show=False,
                )
                print(f"\n✓ Scintillator exit image saved to: {output_image}")
            except Exception as e:
                print(f"\n✗ Error generating scintillator exit image: {e}")
        else:
            print(f"\n⚠ Simulated photons file not found: {simulated_bin}")

    # Generate photocathode image if transport was enabled
    if run_controls.transportation:
        transported_bin = Path(run_env.transported_photons_directory) / "photons.bin"
        if transported_bin.exists():
            print("\n" + "=" * 60)
            print("Generating photocathode image...")
            print("=" * 60)

            output_image = Path(run_env.run_directory) / "photocathode_image.png"

            try:
                image_transported_photons(
                    transported_bin,
                    bins=200,
                    extent_mm=10,
                    cmap="hot",
                    output_path=output_image,
                    show=False,
                )
                print(f"\n✓ Photocathode image saved to: {output_image}")
            except Exception as e:
                print(f"\n✗ Error generating image: {e}")
        else:
            print(f"\n⚠ Transported photons file not found: {transported_bin}")


if __name__ == "__main__":
    main()
