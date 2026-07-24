# References and Data Sources

These are starting sources, not a complete systematic review.

## Carbon-model foundations

1. Rothamsted Research. **RothC – A model for the turnover of carbon in soil: Model Description** (February 2024).
   - https://www.rothamsted.ac.uk/sites/default/files/Documents/RothC_description.pdf

2. Rothamsted Research. **Rothamsted Carbon Model (RothC)**.
   - https://www.rothamsted.ac.uk/rothamsted-carbon-model-rothc

3. Coleman, K., Milne, A. E. and Prout, J. M. (2024). **Python version of
   RothC Official Rothamsted Research Release, v1.0.0**.
   - https://doi.org/10.5281/zenodo.10732265

4. DSSAT. **CENTURY soil organic matter module**.
   - https://dssat.net/models-overview/components/century-organic-matter-module/

5. APSIM. **SoilN model documentation**.
   - https://www.apsim.info/documentation/model-documentation/soil-modules-documentation/soiln/

## AMF data and mechanisms

6. Stewart, J. D. et al. (2026). **Global density and biomass of arbuscular mycorrhizal fungal networks. Science 392.**
   - https://www.science.org/doi/10.1126/science.adu4373

7. Dryad. **Arbuscular mycorrhizal fungal mycelial density database.**
   - https://datadryad.org/dataset/doi:10.5061/dryad.p2ngf1w1f

8. Hawkins, H.-J. et al. (2023). **Mycorrhizal mycelium as a global carbon pool. Current Biology.**
   - https://doi.org/10.1016/j.cub.2023.02.027

9. Staddon, P. L. et al. (2003). **Rapid turnover of hyphae of mycorrhizal fungi determined by AMS microanalysis of 14C. Science.**
   - https://pubmed.ncbi.nlm.nih.gov/12750519/

10. Horsch, C. C. A. et al. (2023). **Trait-based assembly of arbuscular mycorrhizal fungal communities determines soil carbon formation and retention. New Phytologist.**
   - https://pubmed.ncbi.nlm.nih.gov/36978279/

11. Mason, A. R. G. et al. (2025). **Enhanced stabilisation of soil carbon via arbuscular mycorrhizal fungi and biochar. Scientific Reports.**
    - https://www.nature.com/articles/s41598-025-23219-0

12. Bowles, T. M. et al. (2017). **Ecological intensification and arbuscular mycorrhizas: a meta-analysis of tillage and cover crop effects. Journal of Applied Ecology.**
   - https://doi.org/10.1111/1365-2664.12815

13. Grimoldi, A. A. et al. (2006). **Arbuscular mycorrhizal colonization on
    carbon economy in perennial ryegrass: quantification by steady-state
    labelling and gas exchange. New Phytologist.**
    - https://doi.org/10.1111/j.1469-8137.2006.01853.x

14. Landis, F. C. and Fraser, L. H. (2008). **A new model of carbon and
    phosphorus transfers in arbuscular mycorrhizas. New Phytologist.**
    - https://doi.org/10.1111/j.1469-8137.2007.02268.x

15. Schnepf, A., Roose, T. and Schweiger, P. (2008). **Impact of growth and
    uptake patterns of arbuscular mycorrhizal fungi on plant phosphorus
    uptake—a modelling study. Plant and Soil.**
    - https://doi.org/10.1007/s11104-008-9749-3

16. See, C. R. et al. (2021). **Distinct carbon fractions drive a
    generalisable two-pool model of fungal necromass decomposition. Functional
    Ecology.**
    - https://doi.org/10.1111/1365-2435.13728

## Soil and climate covariates

17. ISRIC. **SoilGrids.**
    - https://isric.org/explore/soilgrids

18. de Sousa, L. M. et al. (2021). **SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. SOIL.**
    - https://soil.copernicus.org/articles/7/217/2021/

19. Copernicus Climate Data Store. **ERA5-Land.**
    - https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land

20. Muñoz-Sabater, J. et al. (2021). **ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. Earth System Science Data.**
    - https://essd.copernicus.org/articles/13/4349/2021/

## Long-term validation

21. e-RA. **Hoosfield soil organic carbon content.**
    - https://www.era.rothamsted.ac.uk/dataset/rhb2/01-HBSOC1852

22. e-RA. **Broadbalk soil organic carbon content 1843–2015.**
    - https://www.era.rothamsted.ac.uk/dataset/rbk1/02-BKSOC1843

23. e-RA. **Rothamsted Ley Arable Soil Organic Carbon 1948–2008.**
    - https://www.era.rothamsted.ac.uk/dataset/rrn1/01-HSOC4808

24. International Soil Radiocarbon Database.
    - https://www.soilradiocarbon.org/

## Plant, harvest and phosphorus baseline

25. Wageningen University & Research. **WOFOST crop parameters v1.0.0:
    Spring barley (`Spring_barley_301`)**.
    - https://raw.githubusercontent.com/ajwdewit/WOFOST_crop_parameters/wofost72/barley.yaml

26. Boogaard, H. L. et al. (2014). **User manual for WOFOST and the WOFOST
    Control Centre 2.1**.
    - https://www.wur.nl/upload_mm/b/9/d/f465ce32-1d86-420d-8c80-0bc37c679ee7_WCC_Manual.pdf

27. PLOS ONE (2021). **Estimating soil organic carbon changes in managed
   temperate moist grasslands with RothC**.
   - https://doi.org/10.1371/journal.pone.0256219

## Phase 6 management interpretation

28. Bowles, T. M. et al. (2017). **Ecological intensification and arbuscular
    mycorrhizas: a meta-analysis of tillage and cover crop effects.** Journal
    of Applied Ecology.
    - https://doi.org/10.1111/1365-2664.12815

Bowles et al. supports expected tillage/cover-crop directions, not the Phase 6
numerical multipliers. FYM carbon routing follows reference 3's official RothC
implementation. Cover magnitude/water/P return, FYM P content, costs and
emissions proxies remain explicitly provisional pending composition-,
operation- and region-specific sources.

## Phase 7 population data strategy

References 17--20 define the intended production SoilGrids and ERA5-Land
sources. Version `0.7.0` does not silently download or claim to cache extracts
from them. Its checked-in `phase7_empirical_seed_fixture_v1.yaml` is a versioned
local research fixture using their covariate schemas, paired with explicit
local and hash-checked cached adapters. Reference 7 informs the future AMF
empirical adapter; bundled AMF initial stocks remain provisional prior anchors,
not records from that dataset. Real extractions must record query/spatial
aggregation code, source release/date, checksums, licences and 0--23 cm depth
aggregation before replacing the fixture.

## Codex workflow

29. OpenAI. **Codex cloud documentation.**
    - https://developers.openai.com/codex/cloud

30. OpenAI. **Codex Prompting Guide.**
    - https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide

31. OpenAI. **Unrolling the Codex agent loop.**
    - https://openai.com/index/unrolling-the-codex-agent-loop/

## Phase 9.6 empirical and long-term sources

32. ISRIC. **SoilGrids 2.0 REST/WCS documentation and data licence.**
    - https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs.html
    - https://docs.isric.org/globaldata/soilgrids/access_on_web.html
    - Median mapped properties are used under CC BY 4.0; source missing values
      are rejected rather than imputed.

33. NASA Langley Research Center. **NASA POWER API documentation.**
    - https://power.larc.nasa.gov/docs/services/api/
    - Monthly MERRA-2-derived grid values for 2001--2020 are cached locally.
      Monthly precipitation rates are converted to totals; Thornthwaite PET is
      a transparent derived variable under assumption A080.

34. Rothamsted Research. **RothC model and Hoosfield example, v2.1.1.**
    - https://doi.org/10.5281/zenodo.10724802
    - The official Apache-2.0 archive supplies the source-corrected monthly
      normal and historical treatment reconstruction used by Phase 9.6.

35. Rothamsted Research e-RA. **Hoosfield long-term experiment.**
    - https://www.era.rothamsted.ac.uk/experiment/hoosfield
    - The normalized local observation fixture and upstream extraction hashes
      remain distinct; total SOC validation does not validate AMF or MAOC.
