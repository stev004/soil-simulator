# UNRESOLVED_REFERENCES

Items that could **not** be completely verified against an authoritative record, or that require author-held information. Per the task, no completed bibliography entry is created for anything listed here as unresolved. For transparency, the block below also records the previously-unresolved items that this update **did** resolve.

## Still unresolved / requiring author input or a residual caveat

### NASA POWER — formal data-product citation as a completed BibTeX entry
- **Status:** Partially resolved (intentionally not a completed .bib entry)
- **Detail:** NASA POWER's official Referencing Guide supplies POWER's Reference and Data Reference text and requires service name, version number, and access date, but NASA POWER is not registered as a single citable DOI work. It is therefore documented in DATASET_CITATION_AND_LICENCE.md with the exact required wording rather than added as a completed bibliography entry. Cite the MERRA-2 basis (Gelaro et al. 2017, verified) alongside the POWER data reference.
- **Missing / required:** Author-supplied POWER product name (e.g. Daily/Monthly) + version string + access date at time of extraction.

### MERRA-2 / NASA data-licence characterisation (public domain)
- **Status:** Bibliography resolved; licence characterisation medium confidence
- **Detail:** Gelaro et al. (2017) is fully verified (Crossref). The 'public domain / no restrictions' characterisation of MERRA-2 distribution was not confirmed from a NASA GES DISC page in this session (publisher/NASA data-policy page not fetched).
- **Missing / required:** Official NASA data-policy page confirmation of redistribution terms (only needed if MERRA-2 is used directly rather than via POWER).

### SoilGrids underlying WoSIS point-data licence
- **Status:** Not applicable to this manuscript / unverified
- **Detail:** The gridded SoilGrids 2.0 predictions used here are CC BY 4.0 (confirmed). The underlying WoSIS point database may carry different terms; it was not used and its licence was not verified.
- **Missing / required:** WoSIS licence terms (only if point data were ever used).

### RothC model description (rothamsted2024rothc) — formal publication metadata
- **Status:** Included as a technical report; medium confidence
- **Detail:** The RothC model-description PDF is hosted on rothamsted.ac.uk and cited as a Rothamsted Research technical document (2024). It has no DOI and no formal author list beyond the institution. Entry is included with institution authorship and stable URL; the year is taken from the document as recorded in the repository inventory and was not independently DOI-verified.
- **Missing / required:** A DOI or formal publication record; independent confirmation of the document date.

### Exact AI product/model names, versions, and dates used in development
- **Status:** Author input required (not a bibliographic verification item)
- **Detail:** Section 9 requires the author to state which AI coding assistants / models were used, with versions and dates. These are records only the author holds; the AI_DISCLOSURE_SOURCES.md file supplies the POLICY basis, not the product identities.
- **Missing / required:** Author-supplied product/model names, versions, dates, and the roles each supported.

## Previously unresolved — RESOLVED in this update

The following items from `manuscript/manifests/unresolved_citations_v2.md` are now fully verified and appear in `VERIFIED_REFERENCES.bib`:

- **Saltelli (2010) first-order estimator** → Saltelli et al. 2010, Comput. Phys. Commun. 181(2):259–270, doi:10.1016/j.cpc.2009.09.018
- **Jansen (1999) total-order estimator** → Jansen 1999, Comput. Phys. Commun. 117(1–2):35–43, doi:10.1016/S0010-4655(98)00154-4
- **Ishigami benchmark** → Ishigami & Homma 1990, ISUMA '90, IEEE, pp. 398–403, doi:10.1109/ISUMA.1990.151285
- **SciPy / scipy.stats.qmc.Sobol** → Virtanen et al. 2020, Nature Methods 17(3):261–272, doi:10.1038/s41592-019-0686-2 (version 1.18.0)
- **SoilGrids 2.0** → Poggio et al. 2021, SOIL 7(1):217–240, doi:10.5194/soil-7-217-2021 (CC BY 4.0). Corrected lead author: Poggio, not de Sousa.
- **Rothamsted e-RA Hoosfield SOC dataset** → Rothamsted Research 2012, doi:10.23637/KeyRefOAHBsoc (CC BY 4.0; mandatory citation string captured)
- **RothC/Hoosfield example v2.1.1** → Coleman, Prout & Milne 2025, Zenodo, doi:10.5281/zenodo.17454357 (concept 10.5281/zenodo.10707406), Apache-2.0. Inventory DOI 10.5281/zenodo.10724802 was INCORRECT.
- **RothC official Python release** → Coleman, Milne & Prout 2024, Zenodo, doi:10.5281/zenodo.10732265, Apache-2.0
- **Broader literature base** → 25 Crossref-verified context references added (see LITERATURE_REVIEW_NOTES.md)

## Corrections made to the imported inventory

- **SoilGrids 2.0 lead author** was recorded as *de Sousa, L. M.* in the inventory; the authoritative record lists **Poggio, L.** as lead author (de Sousa is second of seven).
- **RothC v2.1.1 DOI** in the inventory (`10.5281/zenodo.10724802`) is **incorrect** — it resolves to an unrelated mammographic-density study. The correct record is `10.5281/zenodo.17454357` (concept `10.5281/zenodo.10707406`).
- **RothC Python release authors**: the authoritative record gives *Coleman, Kevin; Milne, Alice; Prout, Jonah* (the inventory's 'A. E.' / 'J. M.' middle initials are not in the DataCite record).
