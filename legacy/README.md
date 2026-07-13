# Legacy code

This directory preserves the retired HDF5 pipeline and code written against
the deleted `SimConfig`, `ConfigIO`, and `OpticalTransport` APIs.

It is excluded from normal pytest collection and is not part of the active
ScintiPix runtime. New work should use the top-level `Simulation` model and the
fixed-record binary output documented in `.agents/docs/OUTPUT.md`.
