# References source inventory

This is a source inventory for Prism, not a completed bibliography. Metadata is
transcribed only from repository documentation, configuration, manifests and
audits. “Checked” means the project or an archived independent audit explicitly
reports using/recomputing from the source; it is not a new Phase 9.8 literature
review.

| Authors/organisation | Year | Title | Journal/publisher | DOI or stable URL already documented | Supports | Independently checked | Metadata incomplete |
|---|---:|---|---|---|---|---|---|
| Rothamsted Research | 2024 | RothC – A model for the turnover of carbon in soil: Model Description | Rothamsted Research | https://www.rothamsted.ac.uk/sites/default/files/Documents/RothC_description.pdf | RothC equations and parity case | yes, v0.9.0 audit | no |
| Rothamsted Research | not documented | Rothamsted Carbon Model (RothC) | Rothamsted Research | https://www.rothamsted.ac.uk/rothamsted-carbon-model-rothc | Carbon-model context | no | year |
| Coleman, K.; Milne, A. E.; Prout, J. M. | 2024 | Python version of RothC Official Rothamsted Research Release, v1.0.0 | Zenodo | https://doi.org/10.5281/zenodo.10732265 | RothC implementation/parity and PET conversion | yes, v0.9.0 audit | no |
| Saltelli (full authors not documented in repository) | 2010 | First-order covariance estimator reference; title not documented | not documented | not documented | Phase 9.7 first-order sensitivity estimator | yes, focused Phase 9.7 audit | authors/title/journal/DOI |
| Jansen (full authors not documented in repository) | 1999 | Total-order estimator reference; title not documented | not documented | not documented | Phase 9.7 total-order sensitivity estimator | yes, focused Phase 9.7 audit | authors/title/journal/DOI |
| SciPy project | version 1.18.0 documented; year not documented | `scipy.stats.qmc.Sobol` | SciPy | not documented | Scrambled Sobol sequence implementation | yes, focused Phase 9.7 audit reproduced design hash | year/URL/citation metadata |
| Ishigami benchmark (source metadata not documented) | not documented | Ishigami function benchmark | not documented | not documented | Independent estimator sanity check | yes, focused Phase 9.7 audit | complete bibliographic metadata |
| DSSAT | not documented | CENTURY soil organic matter module | DSSAT | https://dssat.net/models-overview/components/century-organic-matter-module/ | Alternative carbon-model context | no | year/authors |
| APSIM | not documented | SoilN model documentation | APSIM | https://www.apsim.info/documentation/model-documentation/soil-modules-documentation/soiln/ | Alternative soil-model context | no | year/authors |
| Stewart, J. D. et al. | 2026 | Global density and biomass of arbuscular mycorrhizal fungal networks | Science 392 | https://www.science.org/doi/10.1126/science.adu4373 | Future AMF empirical grounding | no | full authors/pages |
| Dryad | not documented | Arbuscular mycorrhizal fungal mycelial density database | Dryad | https://datadryad.org/dataset/doi:10.5061/dryad.p2ngf1w1f | Future AMF empirical adapter | no | authors/year |
| Hawkins, H.-J. et al. | 2023 | Mycorrhizal mycelium as a global carbon pool | Current Biology | https://doi.org/10.1016/j.cub.2023.02.027 | AMF carbon-allocation prior | no | full metadata |
| Staddon, P. L. et al. | 2003 | Rapid turnover of hyphae of mycorrhizal fungi determined by AMS microanalysis of 14C | Science | https://pubmed.ncbi.nlm.nih.gov/12750519/ | AMF turnover range | no | DOI is additionally recorded in config; full pages incomplete |
| Horsch, C. C. A. et al. | 2023 | Trait-based assembly of arbuscular mycorrhizal fungal communities determines soil carbon formation and retention | New Phytologist | https://pubmed.ncbi.nlm.nih.gov/36978279/ | AMF community/carbon context | no | full metadata |
| Mason, A. R. G. et al. | 2025 | Enhanced stabilisation of soil carbon via arbuscular mycorrhizal fungi and biochar | Scientific Reports | https://www.nature.com/articles/s41598-025-23219-0 | AMF stabilisation context | no | full metadata |
| Bowles, T. M. et al. | 2017 | Ecological intensification and arbuscular mycorrhizas: a meta-analysis of tillage and cover crop effects | Journal of Applied Ecology | https://doi.org/10.1111/1365-2664.12815 | Tillage/cover direction, not magnitude | no | full authors/pages |
| Grimoldi, A. A. et al. | 2006 | Arbuscular mycorrhizal colonization on carbon economy in perennial ryegrass | New Phytologist | https://doi.org/10.1111/j.1469-8137.2006.01853.x | CUE formulation context | no | full authors/pages |
| Landis, F. C.; Fraser, L. H. | 2008 | A new model of carbon and phosphorus transfers in arbuscular mycorrhizas | New Phytologist | https://doi.org/10.1111/j.1469-8137.2007.02268.x | AMF P-transfer efficiency | no | pages |
| Schnepf, A.; Roose, T.; Schweiger, P. | 2008 | Impact of growth and uptake patterns of arbuscular mycorrhizal fungi on plant phosphorus uptake—a modelling study | Plant and Soil | https://doi.org/10.1007/s11104-008-9749-3 | AMF/root P kinetics | no | pages |
| See, C. R. et al. | 2021 | Distinct carbon fractions drive a generalisable two-pool model of fungal necromass decomposition | Functional Ecology | https://doi.org/10.1111/1365-2435.13728 | Necromass fractions; not exact routing values | no | full metadata |
| ISRIC | not documented | SoilGrids | ISRIC | https://isric.org/explore/soilgrids | Soil covariates | source bytes manifested | year |
| de Sousa, L. M. et al. | 2021 | SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty | SOIL | https://soil.copernicus.org/articles/7/217/2021/ | SoilGrids methodology | no | DOI not recorded |
| Copernicus Climate Data Store | not documented | ERA5-Land | Copernicus | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land | Intended population climate source | no | year |
| Muñoz-Sabater, J. et al. | 2021 | ERA5-Land: a state-of-the-art global reanalysis dataset for land applications | Earth System Science Data | https://essd.copernicus.org/articles/13/4349/2021/ | Reanalysis context | no | DOI not recorded |
| Rothamsted e-RA | not documented | Hoosfield soil organic carbon content | e-RA | https://www.era.rothamsted.ac.uk/dataset/rhb2/01-HBSOC1852 | Long-term SOC observations | source/normal independently reviewed | version/year details in artifact |
| Rothamsted e-RA | not documented | Broadbalk soil organic carbon content 1843–2015 | e-RA | https://www.era.rothamsted.ac.uk/dataset/rbk1/02-BKSOC1843 | Planned secondary validation | no | year/license |
| Rothamsted e-RA | not documented | Rothamsted Ley Arable Soil Organic Carbon 1948–2008 | e-RA | https://www.era.rothamsted.ac.uk/dataset/rrn1/01-HSOC4808 | Planned validation | no | year/license |
| International Soil Radiocarbon Database | not documented | International Soil Radiocarbon Database | ISRaD | https://www.soilradiocarbon.org/ | Potential validation data | no | authors/year/version |
| Wageningen University & Research | 1.0.0 | WOFOST crop parameters: Spring_barley_301 | WUR/GitHub | https://raw.githubusercontent.com/ajwdewit/WOFOST_crop_parameters/wofost72/barley.yaml | Temperature response | no | release year/authors |
| Boogaard, H. L. et al. | 2014 | User manual for WOFOST and the WOFOST Control Centre 2.1 | Wageningen UR | https://www.wur.nl/upload_mm/b/9/d/f465ce32-1d86-420d-8c80-0bc37c679ee7_WCC_Manual.pdf | Crop/harvest parameter context | no | full authors |
| PLOS ONE | 2021 | Estimating soil organic carbon changes in managed temperate moist grasslands with RothC | PLOS ONE | https://doi.org/10.1371/journal.pone.0256219 | Plant carbon fraction assumption | no | authors |
| OpenAI | not documented | Codex cloud documentation | OpenAI | https://developers.openai.com/codex/cloud | AI-assisted workflow context | no | year/version |
| OpenAI | not documented | Codex Prompting Guide | OpenAI Cookbook | https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide | AI-assisted workflow context | no | year/version |
| OpenAI | not documented | Unrolling the Codex agent loop | OpenAI | https://openai.com/index/unrolling-the-codex-agent-loop/ | AI-assisted workflow context | no | year |
| ISRIC | not documented | SoilGrids 2.0 REST/WCS documentation and data licence | ISRIC | https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs.html | Phase 9.6 extraction/licence | source bytes and hashes manifested | access-date metadata only |
| ISRIC | not documented | SoilGrids access on web | ISRIC | https://docs.isric.org/globaldata/soilgrids/access_on_web.html | Phase 9.6 API use | source bytes and hashes manifested | access-date metadata only |
| NASA Langley Research Center | not documented | NASA POWER API documentation | NASA | https://power.larc.nasa.gov/docs/services/api/ | Phase 9.6 climate extraction | source bytes and hashes manifested | release year/version metadata partial |
| Coleman, K.; Milne, A. E.; Prout, J. M. | 2024 | RothC model and Hoosfield example, v2.1.1 | Zenodo/Rothamsted Research | https://doi.org/10.5281/zenodo.10724802 | Source-corrected forcing and validation reconstruction | archive hash manifested | author metadata inferred from linked project documentation; verify before bibliography |
| Rothamsted Research e-RA | not documented | Hoosfield long-term experiment | Rothamsted Research | https://www.era.rothamsted.ac.uk/experiment/hoosfield | Treatment context | used in validation artifacts | citation metadata incomplete |

Before manuscript submission, Prism or a human reference manager must verify
all incomplete metadata against the source. It must not invent DOIs, authors,
years, page ranges or licences.
