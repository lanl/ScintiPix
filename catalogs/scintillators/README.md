# Scintillator Catalog

This directory stores the bundled Python-native scintillator catalog for ScintiPix.

Path: `catalogs/scintillators/`

Current materials:
- `EJ200` (default baseline)
- `EJ-426` (SSLG4-derived ZnS:Ag/LiF-6 style entry; Li-6 enrichment noted)
- `EJ-276D` (SSLG4-derived optical curves/constants)
- `EJ-276G` (SSLG4-derived optical curves/constants)
- `CsI-Na` (SSLG4 isc-2001)
- `CsI-Tl` (SSLG4 isc-2002)
- `NaI-Tl` (SSLG4 isc-2004)

## Layout

- `catalog.yaml`: catalog index (version, default material, material registry).
- `materials/*.yaml`: per-scintillator metadata, composition, and curve references.
- `curves/<material>/*.csv`: optical property curves (`energy_eV,value`).

Material compositions use an `elements` list. Each `massFraction` is the
element's fraction of the complete material mass, and the fractions sum to
1.0. Optional isotope records use `atomFraction` within one element.

## Curve file format

- UTF-8 text.
- Header row: `energy_eV,value` (recommended).
- Data rows: two numeric columns.
- Comments are allowed with `#`.

Example:

```csv
energy_eV,value
2.00,1.58
2.40,1.58
```
