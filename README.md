# ScintiPix

ScintiPix is a Geant4-based simulation for scintillator and neutron-GPS
workflows with optical-photon recording at an optical-interface plane.

This first release is **v0.1.0**. The Geant4 simulation and binary optical
transport workflows are available. The intensifier and sensor stages are still
under development and are not part of the supported end-to-end workflow.

## Quick start

ScintiPix supports Pixi environments on Linux x86_64 (`linux-64`) and Apple
Silicon macOS (`osx-arm64`). Install Pixi, then create the locked environment:

```bash
pixi install
pixi run build-sim
pixi run python examples/runSimulation/run_simulation_from_yaml.py \
  examples/yamlFiles/OGS_50mm_AmBe.yaml
```

The YAML is validated as the top-level `Simulation` model. The runner writes a
Geant4 macro, optionally runs autofocus, launches `scintipix`, and writes the
selected fixed-record binary outputs and parquet tables.

## Current workflows

- Generate and run from YAML: `examples/runSimulation/`
- Inspect source timing: `examples/sourceTiming/`
- Load or write configuration files: `examples/configurations/`
- Plot primary timing: `examples/analysis/plotting/`
- Read the output file formats: `.agents/docs/outputs.md`
- Read the autofocus and optics design: `.agents/docs/AUTOFOCUS.md` and
  `.agents/docs/OPTICS.md`

The RayOptics transport stage is active and writes binary photons at the
intensifier photocathode plane. Photon multiplication and sensor readout are
still under development. Their retired HDF5 implementations and deleted-model
callers are preserved under `legacy/` and are not active code.

## Repository layout

- `sim/`: Geant4 application
- `src/models/`: Pydantic simulation models
- `src/config/`: YAML, catalog, and macro configuration
- `src/optics/`: autofocus and current optics work
- `catalogs/`: lens and scintillator catalogs
- `examples/`: current runnable examples
- `examples/analysis/`: current lightweight analysis
- `test/`: active tests
- `legacy/`: retired HDF5 and old-model code

## License

ScintiPix is distributed under GPLv3 with LANL open-source approval O5110.
See `LICENSE` for details.
