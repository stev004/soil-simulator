# Data availability evidence

## External sources and licences

| Source | Use | Licence recorded by project | Access date | Local cache | Manifest |
|---|---|---|---|---|---|
| SoilGrids 2.0 median predictions | 0–23 cm soil covariates for 64-location frame | CC BY 4.0 | 2026-07-21 | `data/raw/phase96_empirical/soilgrids/` | `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json` |
| NASA POWER v10 / MERRA-2 monthly 2001–2020 | Temperature and precipitation; derived Thornthwaite PET | CC0 under NASA Earthdata policy unless specifically restricted | 2026-07-21 | `data/raw/phase96_empirical/nasa_power/` | same manifest |
| RothC model and Hoosfield example v2.1.1 | Official monthly normal and treatment reconstruction | Apache-2.0 | 2026-07-21 | `data/raw/phase96_validation/RothC_Code-v2.1.1.zip` | same manifest |
| Rothamsted e-RA Hoosfield observations | Long-term total-SOC observations | Licence/access conditions must be checked at source before redistribution | recorded in frozen Phase 9.5 source artifact | local normalized fixture under `data/` | `outputs/phase95_v0.9.5/long_term_validation.json` |

This archive does not claim permission to publicly redistribute restricted or
otherwise unavailable data. Consult each upstream source and its current terms.

## Raw, processed, generated and simulated records

- **Raw:** byte-preserved external response/archive caches under
  `data/raw/phase96_empirical/` and `data/raw/phase96_validation/`.
- **Processed:** thickness/unit-harmonised paired locations and monthly climate
  in `data/processed/phase96_empirical_*_v1.csv`.
- **Generated:** 112 synthetic descendants in
  `outputs/phase96_v0.9.6/generated_population_v0.9.6.json`.
- **Simulated:** validation trajectories, sensitivity evaluations and paired
  effect targets under `outputs/phase96_v0.9.6/` and
  `outputs/phase97_v0.9.7/`.

`manuscript/data/DATA_INDEX.csv` records the local path, byte size and SHA-256
for every raw/processed entry in the Phase 9.6 source manifest plus the indexed
generated/simulated artifacts. Processed hashes are
`f44f0130c58e1366ec4e064ea88f229043536d64aef2d38d6117a31a83995942`
(soil) and
`5608dc77ee79e30bbda3fae40c800f4961b6ddb224d3b8080228f2f884855df1`
(climate). The source manifest is canonical.
