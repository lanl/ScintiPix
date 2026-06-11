"""Run one Geant4 source-timing simulation from a SimConfig YAML file."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT))

from src.config.ConfigIO import from_yaml  # noqa: E402
from src.runner.runSimulation import run_simulation  # noqa: E402


if __name__ == "__main__":
    yaml_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else REPO_ROOT / "examples" / "yamlFiles" / "pulsed_neutron_source_timing.yaml"
    )

    config = from_yaml(yaml_path.expanduser().resolve())
    run_simulation(config)
