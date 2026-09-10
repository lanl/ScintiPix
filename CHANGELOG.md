# Changelog

All notable ScintiPix releases are documented here.

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
