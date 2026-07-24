# Equations and process evidence

This is an extraction of implemented equations, not polished manuscript prose. `protected_soc_c` is the model humified/protected proxy and is not measured MAOC. Source: `docs/MODEL_SPEC.md:46-82` (RothC-inspired core and claim boundary); `AGENTS.md:28-29` (mandatory proxy qualification).

## RothC environmental modifiers and monthly transition

For monthly mean temperature (T), the implementation returns zero for (T<-5\,^{\circ}\mathrm{C}) or (T+18.27\le0); otherwise

\[
a(T)=\frac{47.91}{\exp(106.06/(T+18.27))+1}.
\]

Source: `src/soil_simulator/processes/rothc.py:43-61` (`temperature_modifier`); constants: `config/model_defaults.yaml:29-32`.

For clay percentage (C) and depth (z\) cm, the negative maximum topsoil-moisture deficit is

\[
M=-\left(20+1.3C-0.01C^2\right)z/23.
\]

The bare-soil limit is (M_b=0.556M), the monthly water increment is (P-0.75E_{pan}), and the candidate deficit is (q=\min(0,TSMD_t+P-0.75E_{pan})). Covered soil uses (TSMD_{t+1}=\max(M,q)); bare soil uses (TSMD_{t+1}=\max(\min(M_b,TSMD_t),q)). With threshold (H=0.444M),

\[
b=\begin{cases}1,&TSMD_{t+1}>H\\0.2+0.8\frac{M-TSMD_{t+1}{M-H},&\text{otherwise.}\end{cases}
\]

Source: `src/soil_simulator/processes/rothc.py:64-138` (`maximum_topsoil_moisture_deficit_mm`, `moisture_modifier`); constants: `config/model_defaults.yaml:33-41`.

The cover modifier is (c=0.6) when covered and (c=1.0) when bare. Source: `src/soil_simulator/processes/rothc.py:141-143` (`soil_cover_modifier`); `config/model_defaults.yaml:42-43`.

For active pool (Y\in\{DPM,RPM,BIO,HUM\}), with annual (k_Y\), (m=abc),

\[
D_Y=Y_t\left[1-\exp(-k_Ym/12)\right],\qquad Y^{rem}=Y_t-D_Y.
\]

The implementation uses `expm1` for numerical stability. Rates are 10.0, 0.3, 0.66 and 0.02 year(^{-1}), while IOM does not decay. Source: `src/soil_simulator/processes/carbon.py:22-48` (`first_order_decay`); `src/soil_simulator/simulator/carbon_core.py:166-186` (`step_carbon_core`); `config/model_defaults.yaml:17-20`.

For clay (C), (x=1.67[1.85+1.60\exp(-0.0786C)]\), (f_{CO2}=x/(x+1)), (f_R=1/(x+1)), (f_{BIO}=0.46f_R), and (f_{HUM}=0.54f_R). Each pool's decomposition is routed explicitly to atmosphere, BIO and the protected proxy. Source: `src/soil_simulator/processes/rothc.py:146-170` (`clay_carbon_partition`); `src/soil_simulator/simulator/carbon_core.py:184-224`.

External inputs are added after decomposition in the authoritative mode; the explicit compatibility mode adds them before decay. Final pools are remaining DPM/RPM plus post-decomposition input, remaining BIO/HUM plus retained transfers, and unchanged IOM. Source: `config/model_defaults.yaml:14-16` (`external_input_timing`); `src/soil_simulator/simulator/carbon_core.py:154-164,215-225`.

## Crop growth, P demand, harvest and residues

Potential monthly NPP is (NPP^{pot}_m=NPP^{annual}p_m), where annual potential is 6.0 t C ha(^{-1}) yr(^{-1}) and the 12-value profile is `[0,0,0.03,0.10,0.20,0.27,0.25,0.12,0.03,0,0,0]`. Source: `src/soil_simulator/processes/plant.py:35-42` (`prescribed_potential_npp`); `config/model_defaults.yaml:52-64`.

Plant temperature stress is piecewise-linear interpolation of `(0,0),(10,1),(30,1),(35,0)`. Plant moisture stress is (f_W=clip[(b-0.2)/(1.0-0.2),0,1]). The baseline growth equation is (NPP=NPP^{pot}f_Tf_Wf_P). Source: `src/soil_simulator/processes/plant.py:45-84` (`plant_temperature_modifier`, `plant_moisture_modifier`, `combine_stress_modifiers`); `src/soil_simulator/simulator/plant_baseline.py:204-230`.

For pre-P carbon growth (G=NPP^{pot}f_Tf_W), carbon fraction (f_C), and tissue P concentration (c_P), demand is (P_d=(G/f_C)1000c_P) kg P ha(^{-1}). Baseline stress is (f_P=1) if demand is zero and otherwise (\min(1,P_{avail}/P_d)); baseline uptake is (\min(P_{avail},P_d)). Source: `src/soil_simulator/processes/phosphorus.py:10-48`; ordering: `src/soil_simulator/simulator/plant_baseline.py:219-232`.

The AMF extension uses direct-root kinetic capacity (U_r=P_dP/(K_r+P)), capped by demand and stock. AMF acquisition occurs first, and direct roots address remaining demand from remaining P. Source: `src/soil_simulator/processes/phosphorus.py:51-70` (`direct_phosphorus_uptake_kg_p_ha`); `src/soil_simulator/simulator/amf_extension.py:138-167`.

Realised plant carbon after fungal allocation is split as root (=NPP_{net}f_r), shoot (=NPP_{net}(1-f_r)). At harvest, grain C (=C_{shoot}h), non-grain shoot (=C_{shoot}-C_{grain}), retained shoot residue (=(C_{shoot}-C_{grain})r_s), root residue (=C_{root}r_r), and grain dry-matter yield (=C_{grain}/f_C). Source: `src/soil_simulator/processes/plant.py:87-132` (`allocate_npp`, `harvest_plant`).

For residue (R) and DPM:RPM ratio (q=1.44), (DPM=Rq/(1+q)) and (RPM=R/(1+q)). Residues are routed after the month's RothC step. Source: `src/soil_simulator/processes/plant.py:135-144`; `src/soil_simulator/simulator/plant_baseline.py:349-356`; `config/model_defaults.yaml:21`.

## AMF allocation, P acquisition, CUE, respiration, turnover and necromass

High-P allocation feedback is (f_P^{alloc}=f_{min}+(1-f_{min})K_P/(K_P+P)). When a host is active, effective allocation is (f_A=\min(f_{max},f_{base}f_P^{alloc}f_Tf_W)), allocated carbon is (C_A=NPP_{gross}f_A), and net plant carbon is (NPP_{gross}-C_A); otherwise allocation is zero. Source: `src/soil_simulator/processes/amf.py:69-123` (`phosphorus_allocation_feedback`, `allocate_plant_carbon_to_amf`).

AMF P acquisition potential is

\[
U_A=V_{max}B_AP/(K_A+P)f_Tf_W,
\]

with acquired (=\min(P,U_A)), transferred (=f_{transfer}U_{acquired}), and the remainder labelled AMF-retained P. Source: `src/soil_simulator/processes/amf.py:207-243` (`acquire_amf_phosphorus`).

Turnover is (T=B_A[1-\exp(-k_{turn})]). AMF growth is (G_A=C_A\,CUE), total fungal respiration is (R_A=C_A-G_A), replacement growth is (\min(G_A,T)), replacement substrate is replacement growth/CUE, maintenance respiration is the smaller of total respiration and replacement substrate times (1-CUE), and growth respiration is the remainder. This maintenance/growth split is explicitly operational and has no separate empirical coefficient. Source: `src/soil_simulator/processes/amf.py:126-162` (`fungal_turnover_t_c_ha`, `fungal_growth_and_respiration`); assumption qualification: `docs/ASSUMPTIONS_REGISTER.csv:23` (A022).

Live AMF updates as (B_{t+1}=B_t+G_A-T), and necromass before its next decay is remaining pre-existing necromass plus current turnover. Source: `src/soil_simulator/simulator/amf_extension.py:221-233`.

Pre-existing necromass decomposes as (D_N=N_t[1-\exp(-k_Na(T)b/12)]) and routes (D_Nf_D,D_Nf_R,D_Nf_H), whose fractions must sum to one. Defaults are 0.5016393442622951, 0.3483606557377049 and 0.15. Source: `src/soil_simulator/processes/amf.py:165-204` (`decay_and_route_necromass`); `config/model_defaults.yaml:199-240`.

## Status distinction

- Authoritative RothC constants: every `rothc.*` scientific constant in `config/model_defaults.yaml:9-47`, classified `established_model` and sourced to RothC_Py v1.0.0. Input timing is recorded separately as operational compatibility behaviour.
- Literature-informed priors: plant carbon fraction, plant P concentration, AMF photosynthate allocation and AMF turnover. Source: `config/model_defaults.yaml:94-113,145-156,188-198`.
- Provisional assumptions: remaining plant, AMF, management and empirical-descendant relationships. Source: `config/model_defaults.yaml:49-270`; `config/populations/phase96_population.yaml:12-35`.
- Calibrated parameters: Hoosfield plant-residue and FYM reconstruction multipliers only, restricted to that diagnostic and not retained in the simulator configuration. Source: `src/soil_simulator/phase96/validation.py:232-333`.
- Purely operational/software settings: model version/horizon, seeds, tolerances, worker counts, sample counts, alpha grid and gate thresholds. Sources are enumerated row-by-row in `COMPLETE_PARAMETER_REGISTER.csv`.
