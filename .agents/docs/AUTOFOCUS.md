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

**Completed:**
- ✅ Models (`FocusGap`, lens catalog structure)
- ✅ Focus gaps identified (Canon: gap 10, Nikkor: gaps 22/24/31)
- ✅ Helper functions (`get_focus_gaps_as_tuples`, `apply_focus_adjustment`)
- ✅ Hybrid optimization (`optimize_focus_hybrid`)
- ✅ Main function (`auto_focus_lens`)
- ✅ Runner integration before macro generation

**Current Issue:**
- Canon EF 50mm ZMX fails at finite distances (DISZ INFINITY)
- Nikkor Z 58mm ZMX works but needs G4LumaCam modifications (gap 22: 21.29mm → 2.68mm)
- Need proper lens for Navitar DO-5095 proxy

**Next Steps:**
1. Modify optimization to allow variable back focus (10-30mm)
2. Use Nikkor Z 58mm with G4LumaCam mods as Navitar proxy
3. Complete unit tests

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
