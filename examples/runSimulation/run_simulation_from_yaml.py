"""Generate a Geant4 macro from Simulation YAML and run ScintiPix."""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT))

from src.config.yaml import from_yaml  # noqa: E402
from src.runner.runSimulation import run_simulation  # noqa: E402

DEFAULT_YAML_PATH = (
    REPO_ROOT / "examples" / "yamlFiles" / "pulsed_neutron_source_timing.yaml"
)


def main() -> None:
    if len(sys.argv) > 2:
        raise SystemExit(
            "Usage: python examples/runSimulation/run_simulation_from_yaml.py "
            "[path/to/simulation.yaml]"
        )

    yaml_path = (
        Path(sys.argv[1]) if len(sys.argv) == 2 else DEFAULT_YAML_PATH
    ).expanduser().resolve()
    config = from_yaml(yaml_path)
    run_simulation(config)


if __name__ == "__main__":
    main()
