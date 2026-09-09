# Third-party and reference-data notes

This file records the project's review of bundled non-code data for the v0.1.0
release. To the best of the ScintiPix team's knowledge, the catalog properties
and derived reference data were assembled by project contributors from public
research and publicly available resources. The project team has reviewed this
basis and the release includes the available source and attribution information.
External publications and resources are cited as scientific or technical
references where known.

This record describes how the materials were developed and reviewed; it is not
a legal determination of ownership, licensing, or redistribution permission.
It does not change the license of an external work or grant rights that the
project does not hold.

## Lens prescriptions

The files under `catalogs/lenses/mxFiles/` are Zemax prescriptions and optional
SMX sidecars. The files identify external sources or references, including Bill
Claff / PhotonsToPhotos URLs, G4LumaCam, and a Canon patent example. The catalog
and lens README do not state redistribution terms. For v0.1.0, the project team
reviewed the available source information and retained the known references and
attribution notes for these project reference materials. This review does not
make a legal determination about rights held by external sources.

## Scintillator curves and material values

The files under `catalogs/scintillators/` contain material compositions and
optical curves. The material YAML files identify sources for several values,
including SSLG4-derived entries and published OGS measurements or estimates.
The project team reviewed these references for v0.1.0 and retained the cited
source information. The project license does not change the terms of an
external source dataset.

## AmBe spectrum

`catalogs/sources/AmBe/emerging_neutron_spectrum.csv` is described in
`catalogs/README.md` as a digitization of F. Falezza et al., *Nuclear
Instruments and Methods in Physics Research A* 1085 (2026) 171233, Figure 9.
The CSV records `energy_MeV` and `relative_intensity` in 50 keV bins. The
project team retained the cited publication and the description of the
50 keV-bin digitization in the repository. The project license does not change
the terms of the source publication or extracted reference values.

## Project license boundary

`LICENSE` and the README state that ScintiPix software is GPLv3-or-later under
LANL open-source approval O5110. That statement does not, by itself, establish
that every externally sourced prescription or reference dataset is licensed
under GPLv3. This release retains the available third-party notices and source
references with the project materials.
