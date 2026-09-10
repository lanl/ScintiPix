# ScintiPix

[![CI](https://github.com/lanl/ScintiPix/actions/workflows/ci.yml/badge.svg)](https://github.com/lanl/ScintiPix/actions/workflows/ci.yml)

ScintiPix is a Geant4-based simulation for scintillator and neutron-GPS
workflows with optical-photon recording at an optical-interface plane.

This source tree prepares the **v0.2.0 release**. The Geant4 simulation and
binary optical transport workflows are available. The intensifier and sensor
stages are still under development and are not part of the supported end-to-end
workflow.

## Quick install

ScintiPix uses [Pixi](https://pixi.sh/latest/installation/) to install its
Python, Geant4, C++, and RayOptics dependencies. The locked environment
supports Linux x86_64 (`linux-64`) and Apple Silicon macOS (`osx-arm64`).

Clone the repository and enter the project directory:

```bash
git clone --depth 1 https://github.com/lanl/ScintiPix.git
cd ScintiPix
```

Install the environment and build the simulator:

```bash
pixi install
pixi run build-sim
```

## Getting started

Run the supported OGS scintillator, Canon lens, and AmBe source example from
the repository root:

```bash
pixi run python examples/runSimulation/run_simulation_from_yaml.py \
  examples/yamlFiles/OGS_50mm_AmBe.yaml
```

This command validates the YAML configuration, runs bounded autofocus, launches
Geant4, transports photons with RayOptics, and assembles the Parquet tables.
The native simulator writes fixed-record binary files first; Python creates the
Parquet tables afterward. The run uses fresh Geant4 random seeds, so photon
counts and other physics results vary between runs.

The example writes its results under:

```text
data/OGS_50mm_AmBe_000/
  config/OGS_50mm_AmBe_000.yaml
  logs/runLog.txt
  primaries/primaries.bin
  secondaries/secondaries.bin
  simulatedPhotons/photons.bin
  transportedPhotons/photons.bin
  photons.parquet
```

The run also creates the corresponding Parquet tables beside the primary and
simulated-photon binary files. See [the output format guide](.agents/docs/outputs.md)
for the file layout, time bases, and Python readers.

The YAML runner is the supported clean-checkout path. The static run macros
under `sim/macros/` are developer or legacy material: they assume pre-existing
output directories and are not standalone release examples.

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

- Release metadata: [`CITATION.cff`](CITATION.cff)
- Release process: [`RELEASING.md`](RELEASING.md)
- License: [`LICENSE`](LICENSE)
- Bundled-data notes: [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

- Previous published release: [`v0.1.0`](https://github.com/lanl/ScintiPix/releases/tag/v0.1.0)
- v0.2.0 release page: pending publication
- Source archive and checksum: published with each tagged release

Cite the software release using `CITATION.cff`, and cite the scientific source
data separately where applicable. The bundled-data notes retain source and
attribution information for the catalog and reference materials.

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
