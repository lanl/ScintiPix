# Catalogs of predefined objects for ScintiPix

This directory is the single repository home for predefined catalog objects, like lenses and scintillators, used by ScintiPix.

Main Layout:

- `lenses/`: optical lens catalog, Zemax prescriptions, and optional SMX sidecars.
- `scintillators/`: scintillator material catalog, material definitions, and optical curves.

## Lenses ##

Selection:
- CanonEF50mmf1.0L
- Nikkor80-200mmf2.8D
- NikkorZ58mmf0.95

Lens Layout:
- `catalog.yaml`: lens catalog entries with metadata and references to Zemax/SMX files.
- `mxFiles/`: Zemax lens prescriptions and optional SMX sidecars.

## Scintillators ##
Selection:
- NaI(Tl): Sodium Iodide doped with Thallium
- CsI(Tl): Cesium Iodide doped with Thallium
- CsI(Na): Cesium Iodide doped with Sodium
- EJ-200: Plastic scintillator from Eljen Technology
- EJ-276D: Plastic scintillator from Eljen Technology with pulse shape discrimination properties
- EJ-276G: Plastic scintillator from Eljen Technology with pulse shape discrimination properties and improved gamma sensitivity
- EJ-426: Plastic scintillator from Eljen Technology with pulse shape discrimination properties and improved neutron sensitivity

Scintillator Layout:
- `catalog.yaml`: scintillator catalog entries with metadata and references to material/curve files.
- `materials/`: material definition files for scintillators.
- `curves/`: optical curve files for scintillators.
