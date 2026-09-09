Python unit tests cover configuration, macro generation, optics, output, and
runner behavior under `test/unit/`.

Run from the repository root:

```bash
pixi run test-python
```

The native Geant4 test is separate:

```bash
pixi run test-sim
```

The equivalent direct Python command is:

```bash
python -m pytest -q
```
