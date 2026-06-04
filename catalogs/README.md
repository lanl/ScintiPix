# Bundled Catalogs

This directory is the single repository home for predefined catalog assets used
by ScintiPix.

Layout:

- `lenses/`: optical lens catalog, Zemax prescriptions, and optional SMX sidecars.
- `scintillators/`: scintillator material catalog, material definitions, and optical curves.

Migration note:

- Lens assets moved from root-level `lenses/` to `catalogs/lenses/`.
- Scintillator assets moved from root-level `scintillators/` to `catalogs/scintillators/`.
- Default catalog-loading APIs resolve the new locations automatically. Code that
  passes explicit filesystem paths should update those paths when using the
  bundled catalogs.
