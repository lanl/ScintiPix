# ScintiPix

ScintiPix is a Geant4-based simulation for scintillator and neutron-GPS
workflows with optical-photon recording at an optical-interface plane.

## Quick start

```bash
pixi install
pixi run build-sim
pixi run python examples/runSimulation/run_simulation_from_yaml.py \
  examples/yamlFiles/CanonEF50mmf1p0L_example.yaml
```

The YAML is validated as the top-level `Simulation` model. The runner writes a
Geant4 macro, optionally runs autofocus, launches `scintipix`, and writes the
selected fixed-record binary outputs.

## Current workflows

- Generate and run from YAML: `examples/runSimulation/`
- Inspect source timing: `examples/sourceTiming/`
- Load or write configuration files: `examples/configurations/`
- Plot primary timing: `analysis/plotting/`
- Read the binary output contract: `.agents/docs/OUTPUT.md`
- Read the autofocus and optics design: `.agents/docs/AUTOFOCUS.md` and
  `.agents/docs/OPTICS.md`

The RayOptics transport, intensifier, and sensor runtime stages are being
rebuilt around the binary photon output. Their retired HDF5 implementations and
deleted-model callers are preserved under `legacy/` and are not active code.

## Repository layout

- `sim/`: Geant4 application
- `src/models/`: Pydantic simulation models
- `src/config/`: YAML, catalog, and macro configuration
- `src/optics/`: autofocus and current optics work
- `catalogs/`: lens and scintillator catalogs
- `examples/`: current runnable examples
- `analysis/`: current lightweight analysis
- `test/`: active tests
- `legacy/`: retired HDF5 and old-model code

## License

ScintiPix is distributed under GPLv3 with LANL open-source approval O5110.
See `LICENSE` for details.
