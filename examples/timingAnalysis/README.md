# Timing Analysis Examples

Timing-related examples are split by stage:

- Geant4 source/neutron timing:
  [`examples/sourceTiming/README.md`](../sourceTiming/README.md)
- Photon creation-delay and scintillation timing analysis:
  [`examples/analysisLite/README.md`](../analysisLite/README.md)

Use the source-timing examples when you want to inspect `creation_time_ns`,
`primary_interaction_time_ns`, and their difference directly from `/primaries`.
Use the analysis-lite timing example when you already have an HDF5 file and
want plots or fits of photon creation delays.
