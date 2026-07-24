# Deterministic Scheduled Management Interventions (Phase 6)

## Scope and claim boundary

Phase 6 composes deterministic tillage, an AMF-compatible generic cover crop,
available-phosphorus application and farmyard manure around the verified Phase
5 soil--spring-barley--AMF kernel. It does not add populations, optimisation,
machine-learning recommendations, an API or a dashboard. Scenario directions
are encoded model implications, not field validation or causal agronomic
recommendations.

Carbon uses `t C ha-1`, available phosphorus uses `kg P ha-1`, cost uses
`GBP ha-1`, and the non-mechanistic emissions proxy uses `kg CO2e ha-1`.
Costs and emissions proxies are reported separately and never enter carbon or P
stocks. `protected_soc_c` remains a humified/protected model proxy and is not
measured MAOC.

## Immutable event schema and schedule validation

Every event records a unique typed ID; exactly one calendar date or zero-based
simulation month; a non-negative amount and event-specific units; cost and
emissions proxy; parameter provenance, source classification and event
provenance. Tillage uses `operation_ha^-1`, cover establishment/termination
uses `event`, P application uses `kg_P_ha^-1`, and manure uses `t_C_ha^-1`.
A tillage event also requires `conventional`, `reduced` or `no_till`.

Validation rejects events before the start or outside the horizon, duplicate
semantic events, multiple tillage operations in one month, unpaired cover
events, duplicate IDs and invalid units. Same-month execution is deterministic:

1. phosphorus application;
2. tillage;
3. cover-crop termination;
4. farmyard manure staging;
5. cover-crop establishment;
6. event ID as the final tie-breaker within a type.

The order is stored in results. Carbon staged by tillage incorporation, cover
termination or manure is added only after existing soil pools decompose,
preserving official RothC input timing.

## Tillage

For tillage level `j`, live AMF pulse mortality is an internal transfer:

\[
M_{AMF}=B_{AMF}m_j,\qquad B'_{AMF}=B_{AMF}-M_{AMF},\qquad
N'_{AMF}=N_{AMF}+M_{AMF}.
\]

During the configured duration, the unchanged Phase 5 turnover rate and RothC
annual rates are multiplied by `g_j` and `d_j`. Current shoot/root carbon is
incorporated at fraction `i_j`, then routed after decomposition using the
established crop DPM:RPM ratio of 1.44. A separate duration can force physical
soil cover to false.

All magnitudes and durations are provisional scenario assumptions A009/A027,
not calibrated effects. Defaults are conventional `m=0.25`, `g=1.50`,
`d=1.25`, two disturbance months, one cover-suppression month and `i=0.80`;
reduced `0.10`, `1.20`, `1.10`, one month, zero months and `0.40`; no-till uses
explicit null defaults. Bounds and qualifications accompany every value in
`model_defaults.yaml`. Bowles et al. (2017) supports direction, not magnitude.

## AMF-compatible cover crop

Establishment activates separate carried shoot, root and plant-P states;
termination is required. Active cover sets physical cover unless tillage
suppresses it and adds a provisional open-pan water-use proxy. Crop P uptake is
resolved first if crop and cover overlap. Cover growth then uses the verified
environmental modifiers, tissue-P demand, finite root/AMF uptake and high-P
allocation response:

\[
C_{preP}=C_{pot}f_Tf_W,\qquad C_{gross}=C_{preP}f_P,
\]

\[
C_{AMF}=q_{eff}C_{gross},\qquad C_{cover}=C_{gross}-C_{AMF}.
\]

Existing AMF CUE partitions `C_AMF` between growth and respiration. Cover P is
held explicitly until termination; the configured fraction returns to
available P and the remainder is exported. Returned biomass enters DPM/RPM
after decomposition, preventing P creation or double counting.

Defaults are provisional `0.15 t C ha-1 month-1` potential input, root fraction
`0.55`, complete carbon/P return and `5 mm month-1` additional open-pan demand
(A010/A028). Water use, P competition, fungal carbon cost, cost and emissions
mean no positive yield, carbon or overall outcome is automatic.

## Phosphorus application

An event amount is added exactly once before Phase 5 uptake:

\[
P^*=P_t+P_{event}.
\]

Existing stock-capped AMF and root pathways deplete `P*`; no efficiency factor
or hidden unavailable-P pool creates P. Higher `P*` can relieve P limitation
while lowering the smooth AMF allocation incentive.

## Farmyard manure

For event carbon `C_FYM`, official RothC routing occurs after decomposition:

\[
DPM=0.49C_{FYM},\quad RPM=0.49C_{FYM},\quad HUM_{proxy}=0.02C_{FYM}.
\]

Explicit P input is `P_FYM=C_FYM c_P,FYM`. The carbon split is established
model A011. Default `c_P,FYM=5 kg P (t C)-1`, range `0--30`, is provisional
A026 pending composition data. Carbon and P cannot decompose or support uptake
in their application month.

## Managed mass balance and reproducibility

The carbon boundary includes carried cover biomass:

\[
C_{start}+C_{crop}+C_{cover}+C_{FYM}
=C_{end}+R_{RothC}+R_{AMF}+R_{cover}+C_{exports}+\epsilon_C.
\]

The P boundary includes available and carried cover-plant P:

\[
P_{start}+P_{application}+P_{FYM}
=P_{end}+P_{crop/AMF\ withdrawal}+P_{cover\ AMF\ retained}
+P_{cover\ export}+\epsilon_P.
\]

Cover uptake/return is internal. Each month fails beyond configured tolerance.
Event, carbon and P records are immutable tuples. Results contain a combined
configuration/scenario hash, schedule hash, deterministic seed, units,
provenance and `provisional_phase_6_not_quantified` uncertainty.

## Unresolved scientific uncertainty

- Tillage pulses, durations, incorporation and cover effects are uncalibrated.
- Generic cover NPP, allocation, water use, return and competitive priority are
  not species-, site- or weather-calibrated.
- Cover P return has no mineralisation delay or unavailable-P chemistry.
- FYM P content is not composition-specific; N, water and quality are absent.
- Demonstration costs/emissions are not life-cycle or farm-budget estimates.
- Direction tests verify encoded behaviour only; no intervention is claimed to
  be universally optimal.
