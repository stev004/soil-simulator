# Software availability evidence

- Package: `soil-simulator` version **0.9.7**.
- Local runtime used for Phase 9.8 verification: Python **3.14.6**.
- Dependency lock: `uv.lock` (Phase 9.7 SHA-256
  `0ad11bbd5f72afb978c45019cc597fccb4731588daa5404884e06e2a58054cbe`).
- Build metadata: `pyproject.toml`.
- Source package: `src/soil_simulator/`.
- CLI entry point: `soil-simulator = soil_simulator.cli:main`.
- Licence in package metadata: proprietary. No broader redistribution right is
  implied by this archive.

The checkout supplied for Phase 9.8 contains no `.git` directory, so a commit
SHA or tag cannot be recovered. It also has no `uv` executable. File-level
SHA-256 manifests, package version and lockfile are therefore the available
identity evidence. This limitation must be disclosed rather than replaced by
an inferred repository version.

Preferred clean installation where `uv` is available:

```bash
uv sync --frozen --extra dev
uv run soil-simulator show-model-info
```

Local Phase 9.8 fallback used the existing locked environment:

```bash
.venv/bin/python -c "import soil_simulator; print(soil_simulator.__version__)"
.venv/bin/soil-simulator show-model-info
```

Build and installed-wheel checks are specified in `REPRODUCIBILITY.md` and
recorded in `manuscript/data/software_verification_summary.json` after replay.
