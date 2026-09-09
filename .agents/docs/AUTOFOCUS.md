# Auto-Focus Implementation

**Date:** 2026-07-09  
**Status:** In Progress

---

## Overview

Auto-focus calculates optimal working distance and internal lens focus adjustment to image the scintillator FOV onto the intensifier.

**Key Requirements:**
1. Working distance from **magnification requirement** 
2. Back focal distance **varies within C-mount lens limits** (~10-30mm)
3. Optimize for **best image quality**

---

## Algorithm

### 1. Calculate Required Magnification
```python
M = intensifier_diameter / scintillator_fov_diagonal
```

### 2. Estimate Working Distance
```python
working_distance = focal_length * (1 + 1/M)  # Thin lens approximation
# For f=50mm, M=0.127x → ~440-500mm
```

### 3. Optimize Focus (zfine)
- Allow back focus to vary (10-30mm range)
- Allow working distance to vary. 
- Allow focus gap thickness to vary
- Minimize RMS spot size
- Two-stage: paraxial (fast) → ray-based (accurate)

### 4. Update the Simulation
```python
config.optical.interface.position_mm.z_mm
primary_lens.focus_adjustment_mm
primary_lens.back_focus_mm
```

`auto_focus_lens(config)` updates the validated configuration and returns
`None`.

---

## Implementation Status

The bounded autofocus path is implemented in `src/optics/focus.py` and is run by
`src/runner/runSimulation.py` before macro generation when enabled. It can vary
working distance and any focus or back-focus values for which the configuration
provides explicit bounds. The routine updates the validated configuration in
place.

The current unit tests exercise catalog loading, required bounds, and the
RayOptics focus path. The tests validate the software path; they do not establish
mechanical limits for a physical lens, mount, adapter, or intensifier assembly.

Some lens prescriptions or requested fields of view may still fail to produce a
valid solution within their configured bounds. Treat those as configuration or
prescription limitations, not as evidence that autofocus can move beyond the
bounds supplied in the YAML file. The Canon, Nikkor, and Navitar-related catalog
entries require separate mechanical and optical validation before production
use.

---

## Lens Catalog

Focus gaps defined in `catalogs/lenses/catalog.yaml`:

```yaml
CanonEF50mmf1.0L:
  focusGaps:
    - gapIndex: 10
      defaultThickness: 10.229
      scalingFactor: 1.0

NikkorZ58mmf0.95:
  focusGaps:
    - gapIndex: 22
      defaultThickness: 21.29  # G4LumaCam uses 2.68mm
      scalingFactor: 1.0
```

---

## References

- Implementation: `src/optics/focus.py`
- G4LumaCam: https://github.com/TsvikiHirsh/G4LumaCam
- C-mount FFD: 17.526mm (nominal, but varies with manual focus!)
