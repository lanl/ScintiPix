# Third-party and reference-data notes

This file records what the repository itself says about bundled non-code data.
It is a release review record, not a substitute for confirming redistribution
rights with the relevant owner.

## Lens prescriptions

The files under `catalogs/lenses/mxFiles/` are Zemax prescriptions and optional
SMX sidecars. The files identify external sources or references, including Bill
Claff / PhotonsToPhotos URLs, G4LumaCam, and a Canon patent example. The catalog
and lens README do not state redistribution terms. Confirm permission and any
required attribution for each prescription before redistributing a release
archive containing them.

## Scintillator curves and material values

The files under `catalogs/scintillators/` contain material compositions and
optical curves. The material YAML files identify sources for several values,
including SSLG4-derived entries and published OGS measurements or estimates.
The repository does not record a license or redistribution grant for each
source dataset. Preserve those citations and confirm the applicable terms
before treating the data as GPL-covered project material.

## AmBe spectrum

`catalogs/sources/AmBe/emerging_neutron_spectrum.csv` is described in
`catalogs/README.md` as a digitization of F. Falezza et al., *Nuclear
Instruments and Methods in Physics Research A* 1085 (2026) 171233, Figure 9.
The CSV records `energy_MeV` and `relative_intensity` in 50 keV bins. The
repository does not record a DOI, digitization checksum, or permission to
redistribute the extracted values. Confirm the reuse status and add the DOI and
method details before public redistribution.

## Project license boundary

`LICENSE` and the README state that ScintiPix software is GPLv3-or-later under
LANL open-source approval O5110. That statement does not, by itself, establish
that every externally sourced prescription or reference dataset is licensed
under GPLv3. Keep third-party notices and any required terms with a release.
