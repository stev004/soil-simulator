# DATASET_CITATION_AND_LICENCE

Citation, licence, and redistribution review for the data and software products used or referenced by the `soil_simulator` manuscript. Licence terms were read from the official product/licence pages where reachable (ISRIC SoilGrids, NASA POWER Referencing Guide, Rothamsted e-RA dataset page) and confirmed against DataCite `rightsList` for DOI-registered items. Statements are limited to published licence terms; no legal conclusions are drawn beyond them.

Each entry states separately: what may be **cited**, what may be **redistributed**, what should only be **linked/indexed**, the **required attribution** language, and whether an **access date** is required.

## SoilGrids 2.0 (ISRIC)

- **Recommended citation:** Poggio, L., de Sousa, L. M., Batjes, N. H., Heuvelink, G. B. M., Kempen, B., Ribeiro, E., & Rossiter, D. (2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. SOIL, 7(1), 217-240.
- **DOI / URL:** 10.5194/soil-7-217-2021 ; product: https://www.isric.org/explore/soilgrids
- **Licence:** CC BY 4.0 (confirmed verbatim on isric.org/explore/soilgrids: 'SoilGrids maps are publicly available on the SoilGrids website under the CC-BY 4.0 License')
- **May be cited:** Yes — cite the Poggio et al. (2021) SOIL paper for methodology and the SoilGrids product/version for the data.
- **May be redistributed:** Yes, under CC BY 4.0 with attribution. Derived layers (e.g. 0-23 cm harmonised covariates) may be redistributed with attribution.
- **Link/index only:** Not required; data is openly licensed.
- **Required attribution language:** Attribute to ISRIC — World Soil Information, SoilGrids, CC BY 4.0; cite Poggio et al. (2021).
- **Access date required:** Yes
- **Verification source:** Crossref (DOI) + official ISRIC page (licence, verbatim)
- **Confidence:** high
- **Notes:** Gridded SoilGrids predictions are CC BY 4.0. Underlying WoSIS point data may carry different terms — not used here. Record SoilGrids version and access date.

## NASA POWER (v10 / MERRA-2-derived meteorology)

- **Recommended citation:** POWER's Reference: 'The data was obtained from the National Aeronautics and Space Administration (NASA) Langley Research Center (LaRC) Prediction of Worldwide Energy Resources (POWER) Project funded through the NASA Earth Science Division.' POWER's Data Reference: 'The data was obtained from the POWER Project's [product/version] version on YYYY/MM/DD.'
- **DOI / URL:** https://power.larc.nasa.gov/ ; docs https://power.larc.nasa.gov/docs/referencing/
- **Licence:** NASA POWER data are freely available for public use; NASA requests acknowledgement rather than imposing a restrictive licence.
- **May be cited:** Yes — include BOTH POWER's Reference and POWER's Data Reference (official requirement).
- **May be redistributed:** Yes — freely usable; the POWER Project requests notification of publications using the data.
- **Link/index only:** Not required.
- **Required attribution language:** Include service name, version number, and date accessed, plus the two POWER references above (per NASA POWER Referencing Guide).
- **Access date required:** Yes
- **Verification source:** Official NASA POWER Referencing Guide (verbatim)
- **Confidence:** high
- **Notes:** Verified verbatim on power.larc.nasa.gov/docs/referencing/: 'include the service name, version number, and date accessed'. Meteorology is MERRA-2-derived.

## MERRA-2 (NASA GMAO reanalysis; basis of NASA POWER meteorology)

- **Recommended citation:** Gelaro, R., McCarty, W., Suárez, M. J., et al. (2017). The Modern-Era Retrospective Analysis for Research and Applications, Version 2 (MERRA-2). Journal of Climate, 30(14), 5419-5454.
- **DOI / URL:** 10.1175/JCLI-D-16-0758.1
- **Licence:** MERRA-2 products distributed by NASA GES DISC are in the public domain (no restrictions); citation of Gelaro et al. (2017) expected.
- **May be cited:** Yes — cite Gelaro et al. (2017) as the MERRA-2 reference.
- **May be redistributed:** Yes — NASA Earth science data are open; here MERRA-2 is used indirectly via NASA POWER.
- **Link/index only:** Not required.
- **Required attribution language:** Cite Gelaro et al. (2017); acknowledge NASA GMAO / GES DISC if MERRA-2 used directly.
- **Access date required:** No
- **Verification source:** Crossref (DOI); NASA data-policy characterisation not page-verified
- **Confidence:** medium
- **Notes:** In this manuscript MERRA-2 enters only via NASA POWER; the POWER references are the operative citation. Public-domain characterisation from NASA data policy was NOT fetched from a NASA page this session — stated at medium confidence.

## Rothamsted e-RA — Hoosfield soil organic carbon content

- **Recommended citation:** Rothamsted Research (2012). Dataset: Hoosfield soil organic carbon content. Electronic Rothamsted Archive, Rothamsted Research, Harpenden, UK. DOI: 10.23637/KeyRefOAHBsoc
- **DOI / URL:** 10.23637/KeyRefOAHBsoc ; https://www.era.rothamsted.ac.uk/dataset/rhb2/01-HBSOC1852
- **Licence:** CC BY 4.0 (confirmed on the dataset page: 'This dataset is available under a Creative Commons Attribution Licence (4.0)'; DataCite rightsList: cc-by-4.0, Copyright Rothamsted Research).
- **May be cited:** Yes — the page states a MANDATORY citation ('YOU MUST CITE AS: ...') exactly as above.
- **May be redistributed:** Yes, under CC BY 4.0 with the mandatory attribution/citation. A normalised local total-SOC fixture may be redistributed with the required citation.
- **Link/index only:** Not required for this dataset (openly licensed with a DOI).
- **Required attribution language:** Use the exact mandatory citation string above (Rothamsted Research 2012; DOI 10.23637/KeyRefOAHBsoc).
- **Access date required:** No
- **Verification source:** Official e-RA dataset page (verbatim) + DataCite (DOI + licence)
- **Confidence:** high
- **Notes:** Fully resolved: DOI verified via DataCite (Rothamsted Research 2012, v1.0, CC BY 4.0, created 2012-12-13). This RESOLVES the previously-unresolved e-RA Hoosfield reference. Broadbalk/Ley-Arable SOC datasets are separate e-RA records (not used).

## Official RothC archives (Zenodo)

- **Recommended citation:** RothC v2.1.1: Coleman, K., Prout, J., & Milne, A. (2025). RothC Official Rothamsted Research Release (v2.1.1). Zenodo. DOI: 10.5281/zenodo.17454357. — Python RothC v1.0.0: Coleman, K., Milne, A., & Prout, J. (2024). Python version of RothC Official Rothamsted Research Release. Zenodo. DOI: 10.5281/zenodo.10732265.
- **DOI / URL:** 10.5281/zenodo.17454357 (concept 10.5281/zenodo.10707406) ; 10.5281/zenodo.10732265 (concept 10.5281/zenodo.10732264)
- **Licence:** Apache License 2.0 (both, confirmed via DataCite rightsList).
- **May be cited:** Yes — cite the version-pinned Zenodo DOI (and note concept DOI).
- **May be redistributed:** Yes — Apache-2.0 permits redistribution and modification with licence/notice retention.
- **Link/index only:** Not required.
- **Required attribution language:** Cite Coleman et al. Zenodo release with version and DOI; retain Apache-2.0 licence and NOTICE on any redistributed code.
- **Access date required:** No
- **Verification source:** DataCite (DOI, creators, version, licence)
- **Confidence:** high
- **Notes:** Inventory DOI 10.5281/zenodo.10724802 for v2.1.1 was INCORRECT (unrelated record); corrected to 10.5281/zenodo.17454357. RothC v2.1.1 includes the Hoosfield example.

## Summary of redistribution posture

| Source | Licence | Cite | Redistribute | Access date | Confidence |
|---|---|---|---|---|---|
| SoilGrids 2.0 | CC BY 4.0 | Yes | Yes | Yes | high |
| NASA POWER | NASA POWER data are fr | Yes | Yes | Yes | high |
| MERRA-2 | MERRA-2 products distr | Yes | Yes | No | medium |
| Rothamsted e-RA — Hoosfield soil organic carbon content | CC BY 4.0 | Yes | Yes | No | high |
| Official RothC archives | Apache License 2.0 | Yes | Yes | No | high |

### Key points
- **SoilGrids 2.0** and the **Hoosfield SOC** dataset are both **CC BY 4.0** — redistributable with attribution (the derived 0–23 cm covariate table and the normalised total-SOC fixture may be redistributed with the required citation).
- The **Hoosfield SOC** dataset carries a **mandatory citation string** and its own DOI (`10.23637/KeyRefOAHBsoc`); use it verbatim.
- **NASA POWER** requires both POWER's Reference and Data Reference, including **service name, version number, and date accessed**.
- **RothC** Zenodo archives are **Apache-2.0** — code may be redistributed/modified with licence and NOTICE retained.
- **MERRA-2** enters only via NASA POWER; cite Gelaro et al. (2017). NASA public-domain characterisation was not page-verified this session (medium confidence).
- **ERA5-Land** is the *intended* production source and was **not** used in the pilot; cite it only as such.
