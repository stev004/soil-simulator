# VERIFIED_REFERENCES

Verified bibliography for the `soil_simulator` methodological/software manuscript.
Every entry was checked against an authoritative registry (Crossref for articles/proceedings, DataCite for Zenodo software and dataset DOIs) and, for datasets, against the official product/licence page. No metadata was inferred. Sources that could not be completely verified are in `UNRESOLVED_REFERENCES.md` and are **not** listed here.

**Total verified references: 38** (BibTeX keys match `VERIFIED_REFERENCES.bib`).

Fields per entry: formatted citation; source type; authoritative verification source; model/manuscript role; confidence/status.

## Sensitivity-analysis methods

### 1. `saltelli2010variance`
- **Citation:** Saltelli, Andrea, Annoni, Paola, Azzini, Ivano, Campolongo, Francesca, Ratto, Marco, Tarantola, Stefano (2010). *Variance based sensitivity analysis of model output. Design and estimator for the total sensitivity index*. Computer Physics Communications, 181(2), 259--270. doi:10.1016/j.cpc.2009.09.018
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** First-order (S1) variance-based sensitivity estimator used in §2.6
- **Confidence/status:** High — verified

### 2. `jansen1999analysis`
- **Citation:** Jansen, Michiel J. W. (1999). *Analysis of variance designs for model output*. Computer Physics Communications, 117(1--2), 35--43. doi:10.1016/S0010-4655(98)00154-4
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Total-order (ST) variance-based sensitivity estimator used in §2.6
- **Confidence/status:** High — verified

### 3. `ishigami1990importance`
- **Citation:** Ishigami, T., Homma, T. (1990). *An importance quantification technique in uncertainty analysis for computer models*. Proceedings. First International Symposium on Uncertainty Modeling and Analysis (ISUMA '90), 398--403. doi:10.1109/ISUMA.1990.151285
- **Source type:** Conference paper
- **Verification source:** Crossref
- **Model/manuscript role:** Canonical Ishigami-function benchmark for estimator sanity check (§2.6)
- **Confidence/status:** High — verified

### 4. `sobol1967distribution`
- **Citation:** Sobol', I. M. (1967). *On the distribution of points in a cube and the approximate evaluation of integrals*. USSR Computational Mathematics and Mathematical Physics, 7(4), 86--112. doi:10.1016/0041-5553(67)90144-9
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Foundational Sobol'-sequence reference underlying scipy.stats.qmc.Sobol
- **Confidence/status:** High — verified

## Scientific-computing software

### 5. `virtanen2020scipy`
- **Citation:** Virtanen, Pauli, Gommers, Ralf, Oliphant, Travis E., et al. (2020). *SciPy 1.0: fundamental algorithms for scientific computing in Python*. Nature Methods, 17(3), 261--272. doi:10.1038/s41592-019-0686-2
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** SciPy; scipy.stats.qmc.Sobol scrambled sequence (version 1.18.0) used in §2.6
- **Confidence/status:** High — verified

## RothC model & software

### 6. `coleman1996rothc`
- **Citation:** Coleman, K., Jenkinson, D. S. (1996). *RothC-26.3---A model for the turnover of carbon in soil*. Evaluation of Soil Organic Matter Models, 237-246. doi:10.1007/978-3-642-61094-3_17
- **Source type:** Book chapter
- **Verification source:** Crossref
- **Model/manuscript role:** RothC-26.3 model structure underpinning the carbon core (§2.2)
- **Confidence/status:** High — verified

### 7. `rothamsted2024rothc`
- **Citation:** {Rothamsted Research} (2024). *RothC---A model for the turnover of carbon in soil: Model Description*. Rothamsted Research. https://www.rothamsted.ac.uk/sites/default/files/Documents/RothC_description.pdf
- **Source type:** Technical report
- **Verification source:** Official Rothamsted page
- **Model/manuscript role:** RothC model description; parity-case source (§2.2)
- **Confidence/status:** Medium — verified

### 8. `coleman2024pythonrothc`
- **Citation:** Coleman, Kevin, Milne, Alice, Prout, Jonah (2024). *Python version of RothC Official Rothamsted Research Release*. v1.0.0 Zenodo. doi:10.5281/zenodo.10732265
- **Source type:** Software (Zenodo)
- **Verification source:** DataCite
- **Model/manuscript role:** Python RothC implementation / parity & PET conversion
- **Confidence/status:** High — verified

### 9. `coleman2025rothc211`
- **Citation:** Coleman, Kevin, Prout, Jonah, Milne, Alice (2025). *RothC Official Rothamsted Research Release (v2.1.1)*. v2.1.1 Zenodo. doi:10.5281/zenodo.17454357
- **Source type:** Software (Zenodo)
- **Verification source:** DataCite + official page
- **Model/manuscript role:** RothC v2.1.1 official archive; source-corrected Hoosfield forcing (§2.5)
- **Confidence/status:** High — verified

## Datasets & data infrastructure

### 10. `poggio2021soilgrids`
- **Citation:** Poggio, Laura, de Sousa, Luis M., Batjes, Niels H., et al. (2021). *SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty*. SOIL, 7(1), 217--240. doi:10.5194/soil-7-217-2021
- **Source type:** Journal article
- **Verification source:** Crossref + ISRIC page
- **Model/manuscript role:** SoilGrids 2.0 soil covariates (§2.4)
- **Confidence/status:** High — verified

### 11. `gelaro2017merra2`
- **Citation:** Gelaro, Ronald, McCarty, Will, Su{\'a}rez, Max J., et al. (2017). *The Modern-Era Retrospective Analysis for Research and Applications, Version 2 (MERRA-2)*. Journal of Climate, 30(14), 5419--5454. doi:10.1175/JCLI-D-16-0758.1
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** MERRA-2 reanalysis basis of NASA POWER meteorology (§2.4)
- **Confidence/status:** High — verified

### 12. `munozsabater2021era5land`
- **Citation:** Mu{\~n}oz-Sabater, Joaqu{\'i}n, Dutra, Emanuel, Agust{\'i}-Panareda, Anna, et al. (2021). *ERA5-Land: a state-of-the-art global reanalysis dataset for land applications*. Earth System Science Data, 13(9), 4349--4383. doi:10.5194/essd-13-4349-2021
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** ERA5-Land; documented intended production climate source (not used in pilot)
- **Confidence/status:** High — verified

### 13. `rothamsted2012hoosfieldsoc`
- **Citation:** {Rothamsted Research} (2012). *Dataset: Hoosfield soil organic carbon content*. 1.0 Electronic Rothamsted Archive, Rothamsted Research. doi:10.23637/KeyRefOAHBsoc
- **Source type:** Dataset (e-RA/DataCite)
- **Verification source:** e-RA page + DataCite
- **Model/manuscript role:** Hoosfield long-term total-SOC observations (§2.5, §3.4)
- **Confidence/status:** High — verified

### 14. `perryman2018era`
- **Citation:** Perryman, Sarah A. M., Castells-Brooke, Nathalie I. D., Glendining, Margaret J., et al. (2018). *The electronic Rothamsted Archive (e-RA), an online resource for data from the Rothamsted long-term experiments*. Scientific Data, 5, 180072. doi:10.1038/sdata.2018.72
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** e-RA data-infrastructure citation (optional, supports §2.5 data provenance)
- **Confidence/status:** High — verified

## Soil & process-based model verification/validation

### 15. `oreskes1994verification`
- **Citation:** Oreskes, Naomi, Shrader-Frechette, Kristin, Belitz, Kenneth (1994). *Verification, Validation, and Confirmation of Numerical Models in the Earth Sciences*. Science, 263(5147), 641-646. doi:10.1126/science.263.5147.641
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Verification/validation/confirmation distinction (§1, §4.1)
- **Confidence/status:** High — verified

### 16. `refsgaard2004modelling`
- **Citation:** Refsgaard, Jens Christian, Henriksen, Hans Jørgen (2004). *Modelling guidelines––terminology and guiding principles*. Advances in Water Resources, 27(1), 71-82. doi:10.1016/j.advwatres.2003.08.006
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Environmental-model V&V terminology (§1, §4.1)
- **Confidence/status:** High — verified

### 17. `refsgaard2007uncertainty`
- **Citation:** Refsgaard, Jens Christian, van der Sluijs, Jeroen P., Højberg, Anker Lajer, Vanrolleghem, Peter A. (2007). *Uncertainty in the environmental modelling process – A framework and guidance*. Environmental Modelling & Software, 22(11), 1543-1556. doi:10.1016/j.envsoft.2007.02.004
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Uncertainty in the modelling process (§3.5 caution, §4.5)
- **Confidence/status:** High — verified

### 18. `smith1997comparison`
- **Citation:** Smith, P., Smith, J.U., Powlson, D.S., et al. (1997). *A comparison of the performance of nine soil organic matter models using datasets from seven long-term experiments*. Geoderma, 81(1-2), 153-225. doi:10.1016/S0016-7061(97)00087-6
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** SOM-model comparison using long-term experiments (§1, §4.1)
- **Confidence/status:** High — verified

### 19. `beven2006manifesto`
- **Citation:** Beven, Keith (2006). *A manifesto for the equifinality thesis*. Journal of Hydrology, 320(1-2), 18-36. doi:10.1016/j.jhydrol.2005.07.007
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Equifinality caution for non-converged sensitivity (§3.5, §4.5)
- **Confidence/status:** High — verified

## AMF, phosphorus, necromass & MAOC

### 20. `smith2011roles`
- **Citation:** Smith, Sally E., Jakobsen, Iver, Grønlund, Mette, Smith, F. Andrew (2011). *Roles of Arbuscular Mycorrhizas in Plant Phosphorus Nutrition: Interactions between Pathways of Phosphorus Uptake in Arbuscular Mycorrhizal Roots Have Important Implications for Understanding and Manipulating Plant Phosphorus Acquisition*. Plant Physiology, 156(3), 1050-1057. doi:10.1104/pp.111.174581
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** AMF role in plant phosphorus nutrition (§2.2)
- **Confidence/status:** High — verified

### 21. `godbold2006mycorrhizal`
- **Citation:** Godbold, Douglas L., Hoosbeek, Marcel R., Lukac, Martin, et al. (2006). *Mycorrhizal Hyphal Turnover as a Dominant Process for Carbon Input into Soil Organic Matter*. Plant and Soil, 281(1-2), 15-24. doi:10.1007/s11104-005-3701-6
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Mycorrhizal hyphal turnover as a carbon-input process (§2.2)
- **Confidence/status:** High — verified

### 22. `frey2019mycorrhizal`
- **Citation:** Frey, Serita D. (2019). *Mycorrhizal Fungi as Mediators of Soil Organic Matter Dynamics*. Annual Review of Ecology, Evolution, and Systematics, 50(1), 237-259. doi:10.1146/annurev-ecolsys-110617-062331
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Mycorrhizal fungi as mediators of SOM dynamics (§2.2, §4.5)
- **Confidence/status:** High — verified

### 23. `hawkins2023mycorrhizal`
- **Citation:** Hawkins, Heidi-Jayne, Cargill, Rachael I.M., Van Nuland, Michael E., et al. (2023). *Mycorrhizal mycelium as a global carbon pool*. Current Biology, 33(11), R560-R573. doi:10.1016/j.cub.2023.02.027
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Mycorrhizal mycelium as a carbon pool; concept not exact magnitude (§4.5)
- **Confidence/status:** High — verified

### 24. `cotrufo2013mems`
- **Citation:** Cotrufo, M. Francesca, Wallenstein, Matthew D., Boot, Claudia M., Denef, Karolien, Paul, Eldor (2013). *The Microbial Efficiency-Matrix Stabilization (MEMS) framework integrates plant litter decomposition with soil organic matter stabilization: do labile plant inputs form stable soil organic matter?*. Global Change Biology, 19(4), 988-995. doi:10.1111/gcb.12113
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** MEMS framework for SOM formation / fraction concept (§2.2)
- **Confidence/status:** High — verified

### 25. `cotrufo2015formation`
- **Citation:** Cotrufo, M. Francesca, Soong, Jennifer L., Horton, Andrew J., et al. (2015). *Formation of soil organic matter via biochemical and physical pathways of litter mass loss*. Nature Geoscience, 8(10), 776-779. doi:10.1038/ngeo2520
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Biochemical/physical SOM-formation pathways (§2.2)
- **Confidence/status:** High — verified

### 26. `lavallee2020conceptualizing`
- **Citation:** Lavallee, Jocelyn M., Soong, Jennifer L., Cotrufo, M. Francesca (2020). *Conceptualizing soil organic matter into particulate and mineral‐associated forms to address global change in the 21st century*. Global Change Biology, 26(1), 261-273. doi:10.1111/gcb.14859
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** POM vs MAOC operational distinction; supports protected_soc-proxy boundary (§2.2, claim boundaries)
- **Confidence/status:** High — verified

## Scientific machine learning

### 27. `kapoor2023leakage`
- **Citation:** Kapoor, Sayash, Narayanan, Arvind (2023). *Leakage and the reproducibility crisis in machine-learning-based science*. Patterns, 4(9), 100804. doi:10.1016/j.patter.2023.100804
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Leakage taxonomy in ML-based science (§1, §4.2)
- **Confidence/status:** High — verified

### 28. `roberts2021common`
- **Citation:** Roberts, Michael, Driggs, Derek, Thorpe, Matthew, et al. (2021). *Common pitfalls and recommendations for using machine learning to detect and prognosticate for COVID-19 using chest radiographs and CT scans*. Nature Machine Intelligence, 3(3), 199-217. doi:10.1038/s42256-021-00307-0
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Common ML pitfalls & recommendations (§1, §4.2)
- **Confidence/status:** High — verified

### 29. `geirhos2020shortcut`
- **Citation:** Geirhos, Robert, Jacobsen, Jörn-Henrik, Michaelis, Claudio, et al. (2020). *Shortcut learning in deep neural networks*. Nature Machine Intelligence, 2(11), 665-673. doi:10.1038/s42256-020-00257-z
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Shortcut learning / spurious signals; OOD framing (§1, §4.2)
- **Confidence/status:** High — verified

### 30. `prosperi2020causal`
- **Citation:** Prosperi, Mattia, Guo, Yi, Sperrin, Matt, et al. (2020). *Causal inference and counterfactual prediction in machine learning for actionable healthcare*. Nature Machine Intelligence, 2(7), 369-375. doi:10.1038/s42256-020-0197-y
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Causal vs predictive inference distinction (§1, §4.2-4.3)
- **Confidence/status:** High — verified

### 31. `gneiting2007strictly`
- **Citation:** Gneiting, Tilmann, Raftery, Adrian E (2007). *Strictly Proper Scoring Rules, Prediction, and Estimation*. Journal of the American Statistical Association, 102(477), 359-378. doi:10.1198/016214506000001437
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Proper scoring / calibration principle (§2.8, §4.5)
- **Confidence/status:** High — verified

### 32. `cranmer2020frontier`
- **Citation:** Cranmer, Kyle, Brehmer, Johann, Louppe, Gilles (2020). *The frontier of simulation-based inference*. Proceedings of the National Academy of Sciences, 117(48), 30055-30062. doi:10.1073/pnas.1912789117
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Simulation-based inference paradigm framing (§1, §4.2)
- **Confidence/status:** High — verified

## Reproducible scientific software & practice

### 33. `sandve2013ten`
- **Citation:** Sandve, Geir Kjetil, Nekrutenko, Anton, Taylor, James, Hovig, Eivind (2013). *Ten Simple Rules for Reproducible Computational Research*. PLoS Computational Biology, 9(10), e1003285. doi:10.1371/journal.pcbi.1003285
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Reproducible computational research practice (§2.9, §4.4)
- **Confidence/status:** High — verified

### 34. `peng2011reproducible`
- **Citation:** Peng, Roger D. (2011). *Reproducible Research in Computational Science*. Science, 334(6060), 1226-1227. doi:10.1126/science.1213847
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Reproducible research in computational science (§1, §4.4)
- **Confidence/status:** High — verified

### 35. `wilson2014best`
- **Citation:** Wilson, Greg, Aruliah, D. A., Brown, C. Titus, et al. (2014). *Best Practices for Scientific Computing*. PLoS Biology, 12(1), e1001745. doi:10.1371/journal.pbio.1001745
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Best practices for scientific computing (§2.9)
- **Confidence/status:** High — verified

### 36. `wilson2017good`
- **Citation:** Wilson, Greg, Bryan, Jennifer, Cranston, Karen, Kitzes, Justin, Nederbragt, Lex, Teal, Tracy K. (2017). *Good enough practices in scientific computing*. PLOS Computational Biology, 13(6), e1005510. doi:10.1371/journal.pcbi.1005510
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Good-enough practices in scientific computing (§2.9)
- **Confidence/status:** High — verified

### 37. `wilkinson2016fair`
- **Citation:** Wilkinson, Mark D., Dumontier, Michel, Aalbersberg, IJsbrand Jan, et al. (2016). *The FAIR Guiding Principles for scientific data management and stewardship*. Scientific Data, 3(1). doi:10.1038/sdata.2016.18
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** FAIR data principles; artifact/data availability (Data availability)
- **Confidence/status:** High — verified

### 38. `stodden2016enhancing`
- **Citation:** Stodden, Victoria, McNutt, Marcia, Bailey, David H., et al. (2016). *Enhancing reproducibility for computational methods*. Science, 354(6317), 1240-1241. doi:10.1126/science.aah6168
- **Source type:** Journal article
- **Verification source:** Crossref
- **Model/manuscript role:** Enhancing reproducibility for computational methods (§2.9, §4.4)
- **Confidence/status:** High — verified
