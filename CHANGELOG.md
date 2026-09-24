# Changelog

All notable ScintiPix releases are documented here.

## [0.3.0] - 2026-09-24

This feature release corrects source timing in the supported OGS/AmBe example
and clarifies how photon row order relates to arrival time.

### Fixed

- The OGS/AmBe example now uses continuous source timing at 2,200,000 neutrons
  per second instead of assigning every event time zero (#62).
- README release links now point to the release, source archive, and checksum.

### Documentation

- Clarified that `photon_id` identifies a row rather than arrival order; sort
  by `timestamp_canonical` when time ordering is needed (#60).
- Explained how source flux sets the event spacing in the OGS/AmBe example.

### Validation

- Added a regression test for the OGS/AmBe timing mode and source rate.

### Known limitations

- The intensifier and sensor runtime stages are not supported end to end.
- Geant4 uses fresh random seeds by default. Exact replay requires the relevant
  seeds, process setup, runtime configuration, software environment, and worker
  behavior; identical configuration files do not by themselves guarantee
  identical physics output.
- The locked environment targets Linux x86_64 and Apple Silicon macOS only.
- The mixed AmBe event model does not apply the catalog's separate gamma
  scintillation profile to coincident neutron/gamma events. This release does
  not claim pulse-shape discrimination behavior.
- Bundled lens prescriptions and reference data retain the provenance and
  attribution notes in `THIRD_PARTY_NOTICES.md` and are unchanged from v0.2.0.

## [0.2.0] - 2026-09-09

This release improves installation, first-run guidance, and continuous
validation while preserving the supported Geant4 and RayOptics workflow.

### Added

- Quick-install and getting-started instructions for the OGS/AmBe example.
- README documents where the release page, source archive, and checksum will
  appear when the v0.2.0 release is published.
- GitHub Actions CI on Linux x86_64 and Apple Silicon macOS.

### Known limitations

- The intensifier and sensor runtime stages are not supported end to end.
- Geant4 uses fresh random seeds by default. Exact replay requires the relevant
  seeds, process setup, runtime configuration, software environment, and worker
  behavior; identical configuration files do not by themselves guarantee
  identical physics output.
- The locked environment currently targets Linux x86_64 and Apple Silicon
  macOS only.
- The mixed AmBe event model currently does not apply the catalog's separate
  gamma scintillation profile to coincident neutron/gamma events. The release
  does not claim pulse-shape discrimination behavior.
- Bundled lens prescriptions and reference data are documented with their
  available provenance and attribution notes in `THIRD_PARTY_NOTICES.md`.

## [0.1.0] - 2026-09-09

ScintiPix's first release. This is an early release; the intensifier and
sensor stages remain under development.

### Added

- YAML-driven Geant4 simulation configuration with validated Pydantic models.
- Bundled lens, scintillator, and AmBe source catalogs.
- Fixed-record binary output for primary particles, secondary particles, and
  optical photons.
- RayOptics transport to the intensifier photocathode plane.
- Run-clock parquet tables and an eight-column HERMES-style photon table with
  event truth labels.
- Examples for source timing, autofocus, catalog loading, and optical transport.

### Known limitations

- The intensifier and sensor runtime stages are not supported end to end.
- Geant4 uses fresh random seeds by default. The run log records seed messages,
  which may include multiple master and worker seed pairs. Exact replay also
  requires the relevant process setup, runtime configuration, software
  environment, and all required seeds; identical configuration files do not by
  themselves guarantee identical physics output.
- The locked environment currently targets Linux x86_64 and Apple Silicon
  macOS only.
- The mixed AmBe event model currently does not apply the catalog's separate
  gamma scintillation profile to coincident neutron/gamma events. The release
  does not claim pulse-shape discrimination behavior.
- Bundled lens prescriptions and reference data are documented with their
  available provenance and attribution notes in `THIRD_PARTY_NOTICES.md`.
