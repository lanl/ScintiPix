# Lens Asset Catalog

This directory stores all bundled optical-lens assets used by ScintiPix.

Path: `catalogs/lenses/`

Layout:
- `catalog.yaml`: index of available lens entries and default selection
- `mxFiles/`: Zemax sequential prescriptions (`.zmx`) and optional
  glass-replacement sidecars (`.smx`) used by RayOptics

Conventions:
- Lens IDs in `catalog.yaml` should map to one `.zmx` file and, when needed,
  one `.smx` file with the same base name.
- The `Simulation` model supports `optical.lenses[*].catalogId` to hydrate lens
  paths, focus gaps, and any configured autofocus geometry from this catalog.
- Production autofocus bounds must describe the actual lens, mount, adapter,
  and intensifier assembly. Do not infer them from the prescription alone.
