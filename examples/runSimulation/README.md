# Run Simulation Examples

This folder contains scripts that generate macros from YAML and launch `scintipix`.

The `run_simulation_from_yaml.py` entry point performs one YAML -> one macro ->
one run.

Run from repo root:

```bash
pixi run python examples/runSimulation/run_simulation_from_yaml.py \
  examples/yamlFiles/CanonEF50mmf1p0L_example.yaml
```
