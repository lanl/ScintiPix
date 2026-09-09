# ScintiPix

ScintiPix is a Geant4-based simulation for scintillator and neutron-GPS
workflows with optical-photon recording at an optical-interface plane.

This source tree prepares the **v0.1.0 release candidate**. The candidate
changes are not yet tagged or published. The Geant4 simulation and binary
optical transport workflows are available. The intensifier and sensor stages
are still under development and are not part of the supported end-to-end
workflow.

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
selected fixed-record binary outputs before assembling the Python parquet
tables.

The YAML runner is the supported run path for a clean checkout. The checked-in
static run macros under `sim/macros/` are developer or legacy material: they
assume pre-existing output directories and are not standalone release examples.
The native executable writes SCINPIX binary records; the Python runner creates
Parquet tables afterward.

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

## Release and provenance

- Release candidate metadata: [`CITATION.cff`](CITATION.cff)
- Release process and publication gate: [`RELEASING.md`](RELEASING.md)
- License: [`LICENSE`](LICENSE)
- Bundled-data review record: [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

The source archive and release tag will be linked here after publication. Cite
the software release using `CITATION.cff`, and cite the scientific source data
separately where applicable. The bundled-data review record must be resolved
before redistributing an archive that includes affected assets.

## Validation

From a clean checkout, the release checks are:

```bash
pixi run check-environment
pixi run build-sim
pixi run test-python
pixi run test-sim
```

## License

ScintiPix is distributed under GPLv3 with LANL open-source approval O5110.
See `LICENSE` for details.
