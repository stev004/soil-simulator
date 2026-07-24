# Deterministic Spring-Barley and Available-P Baseline (Phase 4)

## Scope and claim boundary

Phase 4 adds one scalar, deterministic spring-barley crop, available-phosphorus
accounting, harvest and residue return to the verified Phase 3 RothC core. It
does not add AMF biology, nutrient mineralisation/immobilisation, a general
crop water balance, management-policy effects, optimisation, populations, an
API or a dashboard. The crop equations are a deliberately simple provisional
baseline, not a calibrated cultivar model or evidence of field-scale causal
validity.

This no-AMF baseline remains callable and unchanged for regression use. Phase
5 composes it with explicit finite root/AMF P pathways and fungal carbon
accounting; see `AMF_EXTENSION.md`.

Carbon uses `t C ha-1`, dry matter uses `t DM ha-1`, available phosphorus uses
`kg P ha-1`, temperature uses degrees Celsius and water uses `mm month-1`.
Every parameter comes from the validated configuration and retains its source
classification and citation. Output uncertainty is explicitly
`provisional_phase_4_not_quantified`.

## Monthly potential and realised NPP

For calendar month (m), configured annual potential NPP (NPP_{annual}^{pot})
and configured 12-month profile (q_m):

\[
NPP_m^{pot}=NPP_{annual}^{pot}q_m, \qquad \sum_{m=1}^{12}q_m=1.
\]

The existing provisional spring-barley profile and annual potential NPP from
assumption A002 are activated without recalibration. Realised NPP is:

\[
NPP_m=NPP_m^{pot} f_T(T_m)f_W(b_m)f_P(P_m),
\]

where every factor and their product are bounded to ([0,1]) and are reported
separately. Multiplication is the explicit provisional limiting-factor
combination; no minimum or hidden interaction term is used.

### Temperature stress

The configuration holds WOFOST 7.2 `Spring_barley_301` `TMPFTB` points
`(0,0), (10,1), (30,1), (35,0)`. The implementation linearly interpolates
between points and uses the endpoint value outside the tabulated domain.
WOFOST defines this against average daytime temperature. Applying it to a
monthly mean air temperature is a scenario assumption and temporal-scale
transfer requiring validation.

### Water stress

Phase 4 reuses the verified RothC accumulated TSMD calculation; it does not
claim to implement a crop root-zone water balance. If (b_m) is RothC's
monthly moisture modifier and (b_{min},b_{max}) are its configured official
bounds:

\[
f_W=\operatorname{clip}\left(
\frac{b_m-b_{min}}{b_{max}-b_{min}},0,1\right).
\]

Thus field-capacity forcing maps to 1 and RothC's driest limit maps to 0. This
linear cross-module mapping is provisional assumption A016.

### Available-phosphorus stress and uptake

External available-P input is applied before crop uptake. Let (P^*_m=P_m+I_m),
(f_C) be the configured carbon fraction of dry matter, and (c_P) the
configured whole-plant P concentration. P demand for growth after temperature
and water stress but before P stress is:

\[
C_m^{preP}=NPP_m^{pot}f_Tf_W,
\]

\[
D_{P,m}=\frac{C_m^{preP}}{f_C}
\left(1000\ \frac{kg}{t}\right)c_P.
\]

The stress modifier and uptake are:

\[
f_P=\begin{cases}
1,&D_{P,m}=0\\
\min(1,P^*_m/D_{P,m}),&D_{P,m}>0,
\end{cases}
\]

\[
U_{P,m}=\min(P^*_m,D_{P,m}), \qquad P_{m+1}=P^*_m-U_{P,m}\ge0.
\]

The default (c_P=0.002\ kg\ P\ kg^{-1}\ DM) and its range are a provisional
whole-plant proxy transferred from the WOFOST manual's cereal organ-P values;
they are not a spring-barley tissue dataset. Uptake leaves the modelled
available-P boundary and is recorded as `available_p -> plant_p`; plant P,
residue P return, sorption, weathering and leaching are not state variables.

## Allocation, harvest and residue routing

Realised NPP is partitioned using configured root fraction (r):

\[
\Delta C_{root}=rNPP_m, \qquad
\Delta C_{shoot}=(1-r)NPP_m.
\]

On a scenario-scheduled harvest month, configured harvest index (HI),
above-ground retention (s), root-residue fraction (r_{res}), and carbon
fraction (f_C) give:

\[
C_{grain}=HI\,C_{shoot}, \qquad
Y_{grain}=C_{grain}/f_C,
\]

\[
C_{shoot,res}=s(C_{shoot}-C_{grain}), \qquad
C_{root,res}=r_{res}C_{root}.
\]

Grain and unretained above-ground biomass leave through `harvest_export`;
unretained root carbon leaves through `residue_export`. Retained residues are
internal transfers, then the configured RothC crop DPM:RPM ratio (R=1.44)
is applied:

\[
C_{DPM}=C_{res}\frac{R}{R+1}, \qquad
C_{RPM}=C_{res}\frac{1}{R+1}.
\]

Shoot and root transfers are recorded separately even though their reported
DPM/RPM totals are aggregated. The crop-development state and live shoot/root
stocks reset after harvest; cumulative dry-matter grain yield is retained.

## Residue-input timing and migration decision

Official RothC ordering decomposes the soil pools present at the start of a
month and adds that month's plant/FYM inputs afterwards. Phase 4 adopts
`post_decomposition` as the configuration default. Generated harvest residues
therefore cannot decompose until the following month.

Phase 3 used pre-decomposition external input timing. The standalone core now
supports explicit `legacy_pre_decomposition` compatibility for reproducing
those input-bearing trajectories. No-input trajectories are identical under
both modes, so the January 1852 Hoosfield parity case is unchanged. This is a
documented output migration: default runs containing external carbon inputs
change because new inputs no longer decay immediately.

## Immutable ledgers and mass balance

The carbon ledger records NPP entering shoot/root stocks, RothC transfers and
respiration, harvest exports, root exports, and every shoot/root DPM/RPM
transfer. Whole-system carbon conservation is checked monthly and cumulatively:

\[
C_{start}+NPP+C_{other\ external}
=C_{end}+C_{respired}+C_{harvested}+C_{other\ exports}+\epsilon_C.
\]

The available-P ledger independently checks:

\[
P_{start}+P_{external}=P_{end}+P_{uptake}+\epsilon_P.
\]

Both use configured absolute/relative numerical tolerances and fail rather
than silently accepting an excessive residual. Contracts are frozen, flux
collections are tuples, state is copied between steps, negative/non-finite
stocks are rejected, the deterministic seed is recorded, and results include
the canonical configuration SHA-256 hash plus process provenance.

## Unresolved scientific uncertainties

- The NPP profile, annual potential NPP, fixed root fraction and harvest index
  remain uncalibrated scenario assumptions.
- WOFOST's daytime temperature response is applied to monthly mean air
  temperature; aggregation bias has not been quantified.
- RothC TSMD is a decomposition control, not a crop root-zone water balance;
  its linear mapping to crop stress is intentionally provisional.
- A single whole-plant P concentration substitutes for organ-, stage- and
  cultivar-specific demand. No P recycling or soil-P chemistry is represented.
- Fixed carbon fraction and fixed harvest/residue fractions ignore organ and
  maturity differences.
- Scenario-direction tests verify encoded intent, not empirical validity.
