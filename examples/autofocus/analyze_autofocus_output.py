"""Plot photon output from a completed autofocus simulation."""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT))

from examples.analysis.imaging.plotter import (  # noqa: E402
    image_scintillator_exit,
    image_transported_photons,
)
from src.config.yaml import from_yaml  # noqa: E402

DEFAULT_YAML_PATH = (
    REPO_ROOT / "examples" / "yamlFiles" / "EJ200_siemens_50mm.yaml"
)


def main() -> None:
    """Create images from existing simulated and transported photon output."""
    if len(sys.argv) > 2:
        raise SystemExit(
            "Usage: python examples/autofocus/analyze_autofocus_output.py "
            "[path/to/simulation.yaml]"
        )

    yaml_path = (
        Path(sys.argv[1]) if len(sys.argv) == 2 else DEFAULT_YAML_PATH
    ).expanduser().resolve()
    config = from_yaml(yaml_path)
    run_env = config.metadata.run_environment
    field_of_view = config.scintillator.field_of_view

    simulated_bin = Path(run_env.simulated_photons_directory) / run_env.photons_filename
    transported_bin = (
        Path(run_env.transported_photons_directory) / run_env.photons_filename
    )

    image_scintillator_exit(
        simulated_bin,
        bins=100,
        dimensions_mm=(field_of_view.width_mm, field_of_view.height_mm),
        output_path=run_env.run_directory / "scintillator_exit.png",
        show=False,
    )
    image_transported_photons(
        transported_bin,
        bins=200,
        extent_mm=10,
        output_path=run_env.run_directory / "photocathode_image.png",
        show=False,
    )


if __name__ == "__main__":
    main()
