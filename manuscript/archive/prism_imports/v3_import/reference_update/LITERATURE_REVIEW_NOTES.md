# LITERATURE_REVIEW_NOTES

Focused scholarly-context base for the manuscript's broader methodological claims. Selection favoured peer-reviewed reviews, standards, and foundational papers, and was kept deliberately tight — no padding with loosely related work. Every DOI was verified against Crossref (title, full author list, year, venue, volume/issue/pages confirmed).

**Scope discipline:** these references support *methodological framing and process existence* only. Per the manuscript's claim boundaries, none is used to support real-farm prediction, causal intervention effects, measured MAOC, carbon-credit quantities, or generalisable ML selection. Where a reference could be over-read, the qualification is noted below.

## A. Soil & process-based modelling (verification, validation, uncertainty, transferability)

- **`oreskes1994verification`** — Oreskes, Naomi, Shrader-Frechette, Kristin, Belitz, Kenneth (1994). *Verification, Validation, and Confirmation of Numerical Models in the Earth Sciences*. Science 263(5147): 641-646. doi:10.1126/science.263.5147.641
  - *Role:* Foundational argument that numerical models of open natural systems cannot be truly validated—only confirmed—grounding the paper's insistence on verification/audit rather than field validation.
  - *Qualification:* none — direct support

- **`refsgaard2004modelling`** — Refsgaard, Jens Christian, Henriksen, Hans Jørgen (2004). *Modelling guidelines––terminology and guiding principles*. Advances in Water Resources 27(1): 71-82. doi:10.1016/j.advwatres.2003.08.006
  - *Role:* Provides the terminology and guiding principles (verification vs validation) framing the framework's V&V and audit workflow.
  - *Qualification:* none — direct support

- **`refsgaard2007uncertainty`** — Refsgaard, Jens Christian, van der Sluijs, Jeroen P., Højberg, Anker Lajer, Vanrolleghem, Peter A. (2007). *Uncertainty in the environmental modelling process – A framework and guidance*. Environmental Modelling & Software 22(11): 1543-1556. doi:10.1016/j.envsoft.2007.02.004
  - *Role:* Supports the treatment of uncertainty as an explicit, staged part of the environmental modelling process.
  - *Qualification:* none — direct support

- **`smith1997comparison`** — Smith, P., Smith, J.U., Powlson, D.S., et al. (1997). *A comparison of the performance of nine soil organic matter models using datasets from seven long-term experiments*. Geoderma 81(1-2): 153-225. doi:10.1016/S0016-7061(97)00087-6
  - *Role:* Precedent for evaluating soil-organic-matter models (including RothC) against long-term experimental datasets, supporting the Hoosfield model-evaluation approach.
  - *Qualification:* none — direct support

- **`beven2006manifesto`** — Beven, Keith (2006). *A manifesto for the equifinality thesis*. Journal of Hydrology 320(1-2): 18-36. doi:10.1016/j.jhydrol.2005.07.007
  - *Role:* Supports the equifinality/diagnostic framing of parameter sensitivity and the caution that calibrated fit does not imply a unique correct model.
  - *Qualification:* Cited for methodological caution, not to claim the framework resolves equifinality.

- **`coleman1996rothc`** — Coleman, K., Jenkinson, D. S. (1996). *RothC-26.3 - A Model for the turnover of carbon in soil*. Evaluation of Soil Organic Matter Models None: 237-246. doi:10.1007/978-3-642-61094-3_17
  - *Role:* Primary description of the RothC-26.3 turnover model that the simulator's soil-carbon core implements.
  - *Qualification:* none — direct support

## B. AMF, phosphorus, fungal necromass & MAOC

- **`lavallee2020conceptualizing`** — Lavallee, Jocelyn M., Soong, Jennifer L., Cotrufo, M. Francesca (2020). *Conceptualizing soil organic matter into particulate and mineral‐associated forms to address global change in the 21st century*. Global Change Biology 26(1): 261-273. doi:10.1111/gcb.14859
  - *Role:* Defines particulate vs mineral-associated organic matter (MAOC), grounding the qualification that `protected_soc` is a model proxy, not measured MAOC.
  - *Qualification:* Supports the boundary that the model pool is not measured MAOC.

- **`cotrufo2013mems`** — Cotrufo, M. Francesca, Wallenstein, Matthew D., Boot, Claudia M., Denef, Karolien, Paul, Eldor (2013). *The Microbial Efficiency-Matrix Stabilization (MEMS) framework integrates plant litter decomposition with soil organic matter stabilization: do labile plant inputs form stable soil organic matter?*. Global Change Biology 19(4): 988-995. doi:10.1111/gcb.12113
  - *Role:* MEMS framework linking microbial products to stable soil organic matter, contextualizing carbon-stabilization representation.
  - *Qualification:* none — direct support

- **`cotrufo2015formation`** — Cotrufo, M. Francesca, Soong, Jennifer L., Horton, Andrew J., et al. (2015). *Formation of soil organic matter via biochemical and physical pathways of litter mass loss*. Nature Geoscience 8(10): 776-779. doi:10.1038/ngeo2520
  - *Role:* Evidence that litter-derived compounds form mineral-associated organic matter, supporting the proxy-vs-MAOC distinction.
  - *Qualification:* none — direct support

- **`smith2011roles`** — Smith, Sally E., Jakobsen, Iver, Grønlund, Mette, Smith, F. Andrew (2011). *Roles of Arbuscular Mycorrhizas in Plant Phosphorus Nutrition: Interactions between Pathways of Phosphorus Uptake in Arbuscular Mycorrhizal Roots Have Important Implications for Understanding and Manipulating Plant Phosphorus Acquisition*. Plant Physiology 156(3): 1050-1057. doi:10.1104/pp.111.174581
  - *Role:* Primary evidence on arbuscular mycorrhizal contribution to plant phosphorus uptake, grounding the AMF/P extension.
  - *Qualification:* none — direct support

- **`godbold2006mycorrhizal`** — Godbold, Douglas L., Hoosbeek, Marcel R., Lukac, Martin, et al. (2006). *Mycorrhizal Hyphal Turnover as a Dominant Process for Carbon Input into Soil Organic Matter*. Plant and Soil 281(1-2): 15-24. doi:10.1007/s11104-005-3701-6
  - *Role:* Evidence that mycorrhizal hyphal turnover is a major pathway of carbon input to soil, supporting AMF carbon-allocation/turnover representation.
  - *Qualification:* none — direct support

- **`frey2019mycorrhizal`** — Frey, Serita D. (2019). *Mycorrhizal Fungi as Mediators of Soil Organic Matter Dynamics*. Annual Review of Ecology, Evolution, and Systematics 50(1): 237-259. doi:10.1146/annurev-ecolsys-110617-062331
  - *Role:* Review of mycorrhizal fungi as mediators of soil organic matter dynamics, contextualizing AMF carbon processes and their uncertainty.
  - *Qualification:* none — direct support

- **`hawkins2023mycorrhizal`** — Hawkins, Heidi-Jayne, Cargill, Rachael I.M., Van Nuland, Michael E., et al. (2023). *Mycorrhizal mycelium as a global carbon pool*. Current Biology 33(11): R560-R573. doi:10.1016/j.cub.2023.02.027
  - *Role:* Recent quantification of mycorrhizal mycelium as a global carbon pool with large uncertainty, supporting the caution around AMF carbon fluxes.
  - *Qualification:* Cited to convey magnitude and uncertainty, not to claim quantitative field fluxes in the model.

## C. Scientific machine learning (leakage, distribution shift, causality, calibration)

- **`kapoor2023leakage`** — Kapoor, Sayash, Narayanan, Arvind (2023). *Leakage and the reproducibility crisis in machine-learning-based science*. Patterns 4(9): 100804. doi:10.1016/j.patter.2023.100804
  - *Role:* Directly supports the fail-closed leakage/readiness gates by cataloguing data-leakage pitfalls behind the ML reproducibility crisis.
  - *Qualification:* none — direct support

- **`roberts2021common`** — Roberts, Michael, Driggs, Derek, Thorpe, Matthew, et al. (2021). *Common pitfalls and recommendations for using machine learning to detect and prognosticate for COVID-19 using chest radiographs and CT scans*. Nature Machine Intelligence 3(3): 199-217. doi:10.1038/s42256-021-00307-0
  - *Role:* Documents common ML pitfalls (leakage, biased evaluation) motivating the effect-only benchmarking and blocked deployment.
  - *Qualification:* none — direct support

- **`geirhos2020shortcut`** — Geirhos, Robert, Jacobsen, Jörn-Henrik, Michaelis, Claudio, et al. (2020). *Shortcut learning in deep neural networks*. Nature Machine Intelligence 2(11): 665-673. doi:10.1038/s42256-020-00257-z
  - *Role:* Supports the concern that predictive performance can exploit shortcuts rather than causal structure, motivating OOD gates.
  - *Qualification:* none — direct support

- **`prosperi2020causal`** — Prosperi, Mattia, Guo, Yi, Sperrin, Matt, et al. (2020). *Causal inference and counterfactual prediction in machine learning for actionable healthcare*. Nature Machine Intelligence 2(7): 369-375. doi:10.1038/s42256-020-0197-y
  - *Role:* Distinguishes predictive from causal/counterfactual ML, supporting the refusal to make intervention-effect claims from predictive fit.
  - *Qualification:* none — direct support

- **`gneiting2007strictly`** — Gneiting, Tilmann, Raftery, Adrian E (2007). *Strictly Proper Scoring Rules, Prediction, and Estimation*. Journal of the American Statistical Association 102(477): 359-378. doi:10.1198/016214506000001437
  - *Role:* Provides the proper-scoring-rule basis for uncertainty calibration assessment used in the readiness evaluation.
  - *Qualification:* Supports calibration methodology; coverage claims remain within the synthetic framework.

- **`cranmer2020frontier`** — Cranmer, Kyle, Brehmer, Johann, Louppe, Gilles (2020). *The frontier of simulation-based inference*. Proceedings of the National Academy of Sciences 117(48): 30055-30062. doi:10.1073/pnas.1912789117
  - *Role:* Contextualizes simulator-generated data and simulation-based inference, framing the use of synthetic training/evaluation data.
  - *Qualification:* none — direct support

## D. Reproducible scientific software (provenance, testing, reproducibility, FAIR)

- **`sandve2013ten`** — Sandve, Geir Kjetil, Nekrutenko, Anton, Taylor, James, Hovig, Eivind (2013). *Ten Simple Rules for Reproducible Computational Research*. PLoS Computational Biology 9(10): e1003285. doi:10.1371/journal.pcbi.1003285
  - *Role:* Directly supports the reproducibility and deterministic-workflow design (frozen configs, provenance, replay).
  - *Qualification:* none — direct support

- **`peng2011reproducible`** — Peng, Roger D. (2011). *Reproducible Research in Computational Science*. Science 334(6060): 1226-1227. doi:10.1126/science.1213847
  - *Role:* Foundational statement of reproducible research as a standard for computational science.
  - *Qualification:* none — direct support

- **`wilson2014best`** — Wilson, Greg, Aruliah, D. A., Brown, C. Titus, et al. (2014). *Best Practices for Scientific Computing*. PLoS Biology 12(1): e1001745. doi:10.1371/journal.pbio.1001745
  - *Role:* Supports software engineering best practices (testing, version control) underpinning the framework's implementation.
  - *Qualification:* none — direct support

- **`wilson2017good`** — Wilson, Greg, Bryan, Jennifer, Cranston, Karen, Kitzes, Justin, Nederbragt, Lex, Teal, Tracy K. (2017). *Good enough practices in scientific computing*. PLOS Computational Biology 13(6): e1005510. doi:10.1371/journal.pcbi.1005510
  - *Role:* Supports the 'good enough' practical reproducibility practices adopted (data management, project organization).
  - *Qualification:* none — direct support

- **`wilkinson2016fair`** — Wilkinson, Mark D., Dumontier, Michel, Aalbersberg, IJsbrand Jan, et al. (2016). *The FAIR Guiding Principles for scientific data management and stewardship*. Scientific Data 3(1). doi:10.1038/sdata.2016.18
  - *Role:* Grounds the FAIR data/artifact-manifest and provenance approach.
  - *Qualification:* none — direct support

- **`stodden2016enhancing`** — Stodden, Victoria, McNutt, Marcia, Bailey, David H., et al. (2016). *Enhancing reproducibility for computational methods*. Science 354(6317): 1240-1241. doi:10.1126/science.aah6168
  - *Role:* Supports standards for enhancing reproducibility of computational methods, including artifact sharing and independent verification.
  - *Qualification:* none — direct support

## Notes on qualified citations

- **`beven2006manifesto`** — cited only for the equifinality/uncertainty *caution* accompanying the non-converged sensitivity result; not to claim the analysis converged.
- **`lavallee2020conceptualizing`** — reinforces the operational POM/MAOC distinction and thereby the `protected_soc`-is-a-proxy boundary; not evidence that MAOC was measured or predicted.
- **`hawkins2023mycorrhizal`** — supports the *existence* of a mycorrhizal carbon pool and its qualitative importance; the manuscript does not adopt its magnitudes.
- **`gneiting2007strictly`** — supports the calibration *principle*; the manuscript's residual-coverage evidence stays within synthetic evaluation regimes.

**Total context references: 25** (all Crossref-verified; zero unresolved).
