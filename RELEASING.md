# Releasing ScintiPix

This project uses annotated SemVer tags. The first release is `v0.1.0`, not
`v1.0.0`: the intensifier and sensor stages are still under development.

## Before tagging

1. Start from the intended release commit and confirm the working tree is
   clean.
2. Update `pixi.toml`, `CHANGELOG.md`, `CITATION.cff`, and user-facing example
   metadata together when the version changes.
3. Install from the committed lockfile with `pixi install` on a declared
   platform: Linux x86_64 or Apple Silicon macOS.
4. Run the environment check, Python tests, simulator build, and C++ tests:

   ```bash
   pixi run check-environment
   pixi run test-python
   pixi run build-sim
   pixi run test-sim
   ```

5. Validate the current YAML examples and run one documented example from a
   clean checkout. Do not treat ignored `data/`, `build/`, `resources/`, or
   scratch files as release contents.
6. Check documentation links and copy-paste commands, then run `git diff --check`.
7. Review `THIRD_PARTY_NOTICES.md`. Resolve any redistribution question before
   publishing an archive that includes the affected asset.

## Tag and publish

After the release commit is approved:

```bash
git tag -a v0.1.0 -m "ScintiPix v0.1.0"
git push origin v0.1.0
git archive --format=tar.gz --prefix=ScintiPix-0.1.0/ \
  --output=ScintiPix-0.1.0.tar.gz v0.1.0
shasum -a 256 ScintiPix-0.1.0.tar.gz
```

Create the GitHub release from the tag, attach the source archive and its
SHA-256 checksum, and copy the matching `CHANGELOG.md` entry into the release
notes. State the supported platforms and known limitations. Verify the public
release by downloading the archive into a new directory and following the
installation and test steps above.

Do not publish a binary artifact unless it has been built and tested separately
for its target platform. The source release is the reproducible release
artifact; dependencies are resolved from the committed Pixi lockfile.
