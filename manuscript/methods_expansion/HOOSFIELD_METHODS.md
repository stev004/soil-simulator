# Hoosfield methods evidence extraction

## Treatment, forcing and reconstructed inputs

Treatments are `unfertilized`, `fym_annual` and `fym_1852_1871`; fallow years are 1912, 1933, 1943 and 1967. The source-corrected forcing is the fixed official v2.1.1 monthly normal in code. Source: `src/soil_simulator/phase96/validation.py:18-25` (`TREATMENTS`, `FALLOW_YEARS`, `OFFICIAL_*`).

The 1852 observation initializes each treatment. Active pools begin in the official ratio `(0.1533,4.4852,0.6671,25.8576)` scaled to `(observed total SOC - 2.7 IOM)`; AMF is zero. Source: `src/soil_simulator/phase96/validation.py:28-59` (`ValidationInputs`, `_initial_state`).

Non-fallow annual plant C is `1.6*plant_residue_factor` for unfertilized, and `2.8*factor` for annual FYM or cessation treatment through 1876. It is allocated to April-July as 0.10/0.20/0.30/0.40. Source: `src/soil_simulator/phase96/validation.py:72-92` (`_plant_inputs`).

FYM C is `3.0*fym_carbon_factor` in February through 1871 for cessation; annual FYM is February through 1930, both February and November in 1931, and November thereafter. Source: `src/soil_simulator/phase96/validation.py:95-103` (`_fym_input`).

For monthly plant C (C_p) and FYM C (C_f): (DPM=C_p(1.44/2.44)+0.49C_f), (RPM=C_p/2.44+0.49C_f), and direct protected input (=0.02C_f). Source: `src/soil_simulator/phase96/validation.py:106-138` (`_months`).

## Calibration and held-out allocation

Plant-residue factor grid is 0.80 to 1.20 inclusive in increments of 0.05 (9 values); FYM factor grid is 0.90 to 1.10 inclusive in increments of 0.05 (5 values), giving 45 candidates. Source: `src/soil_simulator/phase96/validation.py:232-245` (`calibrate_inputs`).

Calibration includes unfertilized and annual-FYM observations after initialization through 1965. All post-1965 observations for those treatments are held-out temporal data; the entire cessation treatment after its 1852 initialization is held-out treatment data. Source: `src/soil_simulator/phase96/validation.py:167-206` (`run_trajectory`); summary contract: `src/soil_simulator/phase96/validation.py:299-311`.

For treatment (j\in\{unfertilized,fym\_annual\}\), (RMSE_j=\sqrt{n_j^{-1}\sum_i(\hat y_{ij}-y_{ij})^2}). The objective is ((RMSE_{unfertilized}+RMSE_{fym\_annual})/2). Candidate selection uses Python `min` in generated grid order, so an exact objective tie retains the earliest plant then FYM grid candidate. Source: `src/soil_simulator/phase96/validation.py:147-159,246-269`.

## Existing complete two-dimensional objective data

The following 45 values are copied from `outputs/phase96_v0.9.6/long_term_diagnosis.json` (`optional_calibration.candidate_summary`); no model run or interpolation was performed.

| plant residue factor | FYM factor | mean treatment RMSE (t C ha-1) |
|---:|---:|---:|
| 0.80 | 0.90 | 5.929047179240693 |
| 0.80 | 0.95 | 5.1604139261154796 |
| 0.80 | 1.00 | 4.425769963344007 |
| 0.80 | 1.05 | 3.7494451359786125 |
| 0.80 | 1.10 | 3.1788314518649217 |
| 0.85 | 0.90 | 5.609438606051626 |
| 0.85 | 0.95 | 4.8637728128372695 |
| 0.85 | 1.00 | 4.168732363724446 |
| 0.85 | 1.05 | 3.5648214719429587 |
| 0.85 | 1.10 | 3.1287613079547087 |
| 0.90 | 0.90 | 5.353408919665942 |
| 0.90 | 0.95 | 4.642061704261051 |
| 0.90 | 1.00 | 4.009228218799983 |
| 0.90 | 1.05 | 3.5219939976711765 |
| 0.90 | 1.10 | 3.288506414289205 |
| 0.95 | 0.90 | 5.139649687985738 |
| 0.95 | 0.95 | 4.481747777689892 |
| 0.95 | 1.00 | 3.9494235944165865 |
| 0.95 | 1.05 | 3.6439783810586706 |
| 0.95 | 1.10 | 3.669171652923467 |
| 1.00 | 0.90 | 4.971220974258747 |
| 1.00 | 0.95 | 4.399526521089138 |
| 1.00 | 1.00 | 4.027743470087522 |
| 1.00 | 1.05 | 3.9705983444019015 |
| 1.00 | 1.10 | 4.251850819496044 |
| 1.05 | 0.90 | 4.866668518038315 |
| 1.05 | 0.95 | 4.434928079034955 |
| 1.05 | 1.00 | 4.295630762053426 |
| 1.05 | 1.05 | 4.505709539323533 |
| 1.05 | 1.10 | 4.983419016338798 |
| 1.10 | 0.90 | 4.862390490776205 |
| 1.10 | 0.95 | 4.6433503209497236 |
| 1.10 | 1.00 | 4.776054613696886 |
| 1.10 | 1.05 | 5.205336306137284 |
| 1.10 | 1.10 | 5.810955006887834 |
| 1.15 | 0.90 | 5.013209200242472 |
| 1.15 | 0.95 | 5.063749540353415 |
| 1.15 | 1.00 | 5.437337564554895 |
| 1.15 | 1.05 | 6.013831353250357 |
| 1.15 | 1.10 | 6.698009458538349 |
| 1.20 | 0.90 | 5.370060763205984 |
| 1.20 | 0.95 | 5.680285795846398 |
| 1.20 | 1.00 | 6.222674627687992 |
| 1.20 | 1.05 | 6.889790405280802 |
| 1.20 | 1.10 | 7.622547919471352 |

Phase 9.7 profiles FYM by minimizing over the plant factor at each FYM grid value; it does not replace the complete 2-D surface above. Source: `src/soil_simulator/phase97/calibration.py:20-94` (`calibration_boundary_profile`); `outputs/phase97_v0.9.7/calibration_profile.json`.

The fitted FYM factor is 1.10 at its upper bound, so the result is boundary-constrained and is not a general calibrated simulator parameter. Source: `outputs/phase97_v0.9.7/calibration_profile.json` (`estimate`, `boundary_constrained`, `general_calibration_success`); `docs/PHASE97_CALIBRATION_BOUNDARY.md:1-16`.
