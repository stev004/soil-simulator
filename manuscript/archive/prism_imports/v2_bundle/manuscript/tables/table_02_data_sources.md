# Preview: table_02_data_sources

Generated from the adjacent CSV for human inspection. The CSV is canonical.

| dataset | data_class | coverage | units | license | access_date | local_path | sha256 | source_path | audit_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SoilGrids 2.0 median predictions | raw external prediction cache / processed empirical pilot | 64 requested; 56 accepted; 8 rejected; 0-23 cm | locations; cm | CC BY 4.0 | 2026-07-21 | data/raw/phase96_empirical/soilgrids/; data/processed/phase96_empirical_soil_locations_v1.csv | f44f0130c58e1366ec4e064ea88f229043536d64aef2d38d6117a31a83995942 | outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json | manifested; Phase 9.7 focused re-audit verified the 56-location pilot boundary |
| NASA POWER v10, MERRA-2 monthly 2001-2020 | raw external reanalysis cache / processed empirical pilot | monthly 2001-2020; 56 accepted locations | months; locations | CC0 under NASA Earthdata policy unless specifically restricted | 2026-07-21 | data/raw/phase96_empirical/nasa_power/; data/processed/phase96_empirical_monthly_climate_v1.csv | 5608dc77ee79e30bbda3fae40c800f4961b6ddb224d3b8080228f2f884855df1 | outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json | manifested; PET is derived under A080 |
| Official RothC model and Hoosfield example v2.1.1 | external validation/reference archive | Hoosfield model example and forcing | monthly forcing and t C ha-1 observations | Apache-2.0 | 2026-07-21 | data/raw/phase96_validation/RothC_Code-v2.1.1.zip | 728ef1320f8a660b14e12648fbf3d4d20917021016a24c46f5cde5c7609b9966 | outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json | source correction verified; cessation fit remains weak |
