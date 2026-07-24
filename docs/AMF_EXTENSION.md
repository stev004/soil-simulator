# Deterministic AMF Extension (Phase 5)

## Scope, units and claim boundary

Phase 5 adds explicit living AMF carbon, fungal necromass, plant-to-AMF
allocation, fungal growth and maintenance respiration, biomass turnover,
necromass routing, and AMF-mediated phosphorus acquisition to the verified
Phase 4 soil--crop simulator. Carbon uses `t C ha-1`; available phosphorus uses
`kg P ha-1`; rates state `month-1` or `year-1` explicitly.

The relationships are deterministic and uncertainty-ready but uncalibrated.
They support internally coherent beneficial, neutral and harmful outcomes; they
do not establish field-scale causal effects. `protected_soc_c` remains a
humified/protected model proxy and is not measured MAOC.

## Direct-root and fungal phosphorus acquisition

Phase 4 allowed direct roots to consume the complete available-P stock up to
demand in one time step. Under that assumption AMF could only replace direct
uptake, never provide a benefit. Phase 5 therefore makes both pathways finite
and explicit using the Michaelis--Menten form used for root and fungal uptake
by Schnepf, Roose and Schweiger (2008). The aggregate root half-saturation
value is a provisional scenario assumption, not a transferred measured rate.

After external input, let `P*` be available P and `D_P` the existing Phase 4
tissue-P demand. For an active host, start-of-month live AMF carbon `B`, plant
temperature modifier `f_T` and plant moisture modifier `f_W`:

\[
A_P=\min\left(P^*,V_{max,P}B\frac{P^*}{K_{m,P}+P^*}f_Tf_W\right).
\]

The plant transfer and fungal-retained amounts are:

\[
T_P=f_{transfer}A_P,\qquad P_{retained}=A_P-T_P.
\]

Direct-root uptake uses the remaining stock `P_r=P*-A_P` and unmet demand
`D_r=max(0,D_P-T_P)`:

\[
U_{root}=\min\left(P_r,D_r,D_r\frac{P_r}{K_{m,root}+P_r}\right).
\]

Plant P received is `T_P + U_root`; P stress is that amount divided by demand,
bounded to `[0,1]`. Available P closes exactly:

\[
P^*=P_{t+1}+A_P+U_{root}.
\]

Immutable records separately trace available-P input, AMF acquisition, fungal
transfer, fungal retention and direct-root uptake. No AMF flux is active when
the configured crop has no potential host growth. This is complete accounting
of the represented available-P boundary; fungal P storage/recycling and
unavailable soil-P pools remain outside Phase 5.

## Plant carbon cost and context response

Gross realised plant carbon first reflects temperature, moisture and total P
received. High available P smoothly suppresses allocation:

\[
f_{P,alloc}=f_{min}+(1-f_{min})\frac{K_P}{K_P+P^*}.
\]

For an active host:

\[
q_{eff}=\min(q_{max},q_0f_{P,alloc}f_Tf_W),
\]

\[
C_{plant\to AMF}=C_{gross}q_{eff},\qquad
C_{plant,net}=C_{gross}-C_{plant\to AMF}.
\]

The configured `q_0` prior remains bounded from 0.02 to 0.20 and centred at
0.062. The effective fraction may be zero without a host and approaches zero
under the configured high-P response. Only net plant carbon enters shoot/root
allocation; fungal P does not automatically raise production.

## Fungal growth, respiration and turnover

The existing provisional AMF carbon-use efficiency gives:

\[
G=C_{plant\to AMF}CUE_{AMF},\qquad R_{total}=C_{plant\to AMF}-G.
\]

Turnover acts on start-of-month live biomass:

\[
T_C=B_t(1-\exp(-k_{AMF})).
\]

Because no defensible universal AMF maintenance coefficient is available, the
implementation does not invent one. It splits the CUE-derived respiration
operationally: growth that replaces `min(G,T_C)` is assigned maintenance
respiration and the remainder is assigned growth respiration:

\[
G_{replace}=\min(G,T_C),
\]

\[
R_{maintenance}=\frac{G_{replace}}{CUE_{AMF}}(1-CUE_{AMF}),
\]

\[
R_{growth}=R_{total}-R_{maintenance}.
\]

This conservative split is provisional assumption A022. Total respiration is
still exactly the specified CUE complement. Live biomass and new necromass are:

\[
B_{t+1}=B_t+G-T_C,\qquad N^*=N_{remaining}+T_C.
\]

## Necromass timing and routing

Only necromass present at the start of the month decays:

\[
D_N=N_t\left(1-\exp(-k_Nab/12)\right),
\]

where `a` and `b` are the verified RothC temperature and moisture modifiers.
New turnover cannot route until the next month. Decomposed necromass is split
by three validated fractions that must sum exactly to one:

\[
D_N=f_{DPM}D_N+f_{RPM}D_N+f_{protected}D_N.
\]

These transfers are added after the current RothC decomposition step, matching
official post-decomposition residue timing. The default protected fraction is
the existing provisional 0.15 assumption. The remaining 0.85 is provisionally
split using the established RothC 1.44 crop DPM:RPM ratio; this is not an
observed fungal-necromass partition and is registered as A021. See et al.
(2021) supports fast and slow fungal-necromass fractions but not these values.

Living fungal biomass has no direct protected-carbon equation. Protected proxy
formation requires pre-existing necromass decay and a nonzero configured
protected routing fraction, so more live fungi cannot automatically imply more
persistent carbon.

## Beneficial, neutral and harmful outcomes

The simulator advances a parallel no-AMF counterfactual with the same weather,
root P kinetics, crop equations, initial soil/P state and seed, but zero AMF
stocks and fluxes. Monthly and cumulative effects compare net plant carbon and
harvest yield between the two paths.

- `beneficial`: additional AMF-transferred P supports more plant carbon than is
  spent on the fungal allocation;
- `neutral`: the net difference is within the configured absolute numerical
  tolerance, including effectively sufficient-P cases where allocation tends
  to zero;
- `harmful`: plant carbon cost exceeds the realised P benefit.

This classification reports an encoded model implication, not an agronomic
recommendation or empirical causal result.

## Ordering and accounting

The concrete monthly order is:

1. resolve potential NPP and environmental modifiers;
2. add external available P;
3. withdraw AMF P, transfer a configured share, then withdraw direct-root P;
4. compute gross realised carbon, AMF carbon cost and net shoot/root growth;
5. compute CUE growth/respiration and start-of-month fungal turnover;
6. decay pre-existing necromass;
7. decompose the RothC pools present at the start of the step;
8. add necromass routes and scheduled harvest residues after decomposition;
9. validate finite/non-negative state and monthly carbon/P balances;
10. advance the parallel no-AMF counterfactual for reported net effects.

Whole-system carbon closes as:

\[
C_{start}+C_{gross}=C_{end}+R_{RothC}+R_{AMF}+C_{harvest}+C_{other\ exports}.
\]

Configuration hash, package/configuration version, deterministic seed, units,
uncertainty status and process provenance are included in results.

## Sources and unresolved uncertainty

- Hawkins et al. (2023), DOI `10.1016/j.cub.2023.02.027`: broad plant-carbon
  allocation synthesis.
- Staddon et al. (2003), DOI `10.1126/science.1084269`: rapid AMF hyphal
  turnover.
- Grimoldi et al. (2006), DOI `10.1111/j.1469-8137.2006.01853.x`: AMF carbon
  flow and CUE formulation.
- Landis and Fraser (2008), DOI `10.1111/j.1469-8137.2007.02268.x`: independent
  C/P transfer efficiencies and mutualistic-to-parasitic outcomes.
- Schnepf et al. (2008), DOI `10.1007/s11104-008-9749-3`: distinct root and
  fungal Michaelis--Menten P uptake pathways.
- See et al. (2021), DOI `10.1111/1365-2435.13728`: fast/slow fungal-necromass
  decomposition.

AMF CUE, aggregate root/AMF P kinetic scales, transfer efficiency, necromass
decay and routing remain uncalibrated. There is no fungal P stock/recycling,
soil-P sorption/desorption, protection capacity, management disturbance,
species structure or empirical spring-barley AMF validation in Phase 5.
