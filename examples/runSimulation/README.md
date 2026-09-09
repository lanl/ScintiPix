# Run Simulation Examples

This folder contains scripts that generate macros from YAML and launch `scintipix`.

The `run_simulation_from_yaml.py` entry point performs one YAML -> one macro ->
one run. The YAML runner is the supported clean-checkout path; the static
macros under `sim/macros/` are developer or legacy material and are not
standalone release examples.

Run from the repository root after installing Pixi:

```bash
pixi install
pixi run build-sim
pixi run python examples/runSimulation/run_simulation_from_yaml.py \
  examples/yamlFiles/OGS_50mm_AmBe.yaml
```

The OGS example enables autofocus and binary RayOptics transport. Photon
multiplication and sensor readout are not part of this release.
