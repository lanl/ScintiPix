# Optics Overview

This note is for future agents working on optical transport.

The current source of truth is the Geant4 simulation output. The downstream
Python optics, intensifier, and sensor stages have not yet been updated to the
new Geant4 output path. Do not treat the existing `src/optics/OpticalTransport.py`
as the desired design.

## Current Handoff From Geant4

Geant4 creates and tracks scintillation photons inside the scintillator. Photons
that reach the optical interface are recorded by the optical-interface sensitive
detector.

The optical interface represents the lens entrance plane. For each detected
optical photon, Geant4 records:

- source/provenance IDs
- photon creation position and time
- scintillator exit position, when available
- optical-interface hit position
- optical-interface hit time
- optical-interface direction
- polarization
- energy and wavelength

These photon rows are currently written through the Geant4 binary output path,
normally under:

```text
<run_root>/simulatedPhotons/photons.bin
```

The binary row layout is defined in:

- `sim/include/structures.hh`
- `sim/src/SimIO.cc`

## Intended Optical Transport

The future `OpticalTransport.py` rewrite should start from the current Geant4
photon binary output and transport photons from the optical-interface plane to
the photocathode/input plane of the image intensifier.

The core mapping should stay simple:

```text
Geant4 optical-interface photon
  position + direction + wavelength + time
        |
        v
ray optics through configured lens
        |
        v
intensifier photocathode/input-plane hit
```

The optical transport output should preserve provenance IDs so downstream
stages can link transported photons back to the original Geant4 photon rows.

## Rewrite Boundary

### Scintillation Photons to Transported Photons

Need to rewrite `src/optics/OpticalTransport.py`. 
Currently has a lot of legacy code and AI generated junk code. 
Note: Avoid carrying over old HDF5 assumptions unless they are still explicitly needed.

The new implementation should answer these questions:

1. Where should the optical interface be (at the scintillator or at the lens entrance plane)?
2. Do we need to do any configuration of the lens based on zmxFiles?
3. Do we need to create a batch processing mechanism to accelerate this part of the code?
4. Is the back focal plane of the lens set, or do we need to adjust the position of the intensifier to align with the focal plane?

We need a comprehensive understanding of Ray Optics libraries to accurately model the propagation of photons through the lens system and ensure that the optical transport stage correctly maps optical-interface photons to the intensifier photocathode/input-plane hits.

Keep the transport stage focused on ray optics. 
The photocathode response, MCP/phosphor behavior will be in the intensifier module, while 
sensor readout belongs to the sensor modules.
