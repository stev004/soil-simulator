# Verified RothC-Style Monthly Carbon Core (Phase 3)

## Scope, units and claim boundary

The scalar kernel advances five soil-carbon pools monthly:

- decomposable plant material (`dpm_c`);
- resistant plant material (`rpm_c`);
- microbial biomass (`microbial_c`, RothC BIO);
- humified/protected SOC proxy (`protected_soc_c`, RothC HUM);
- inert organic matter (`iom_c`, RothC IOM).

Stocks and fluxes use `t C ha-1`; annual rate constants use `year-1`; water
uses `mm month-1`; and temperature uses degrees Celsius. Carbon mass, not CO2
mass, is tracked. `protected_soc_c` is a model proxy and is not measured MAOC.

The implemented equations and constants are traced to Coleman, Milne and Prout
(2024), *RothC_Py v1.0.0*, the official Rothamsted Research Python release,
[DOI 10.5281/zenodo.10732265](https://doi.org/10.5281/zenodo.10732265), and
its included February 2024 model description. The standalone core contains no
crop or phosphorus equations; Phase 4 composes it with a separate plant/P
kernel. AMF, management-policy, population, optimisation, API and dashboard
behaviour remain absent.

## Environmental rate modifiers

For each active pool `Y` with annual rate `k`, remaining and decomposed carbon
are:

\[
Y_{remaining}=Y\exp(-kabc/12), \qquad
D_Y=Y-Y_{remaining}.
\]

The implementation uses `expm1` for stable evaluation. The three modifiers are
multiplied once and the same combined value is applied to DPM, RPM, BIO and
HUM. A combined modifier of zero produces exactly zero decomposition.

### Temperature

The official Python implementation is:

\[
a(T)=\frac{47.91}{1+\exp(106.06/(T+18.27))}
\]

for `T >= -5 deg C`; below `-5 deg C`, `a=0`. The cutoff is part of the
official code and prevents evaluation near the singularity at `-18.27 deg C`.

### Accumulated topsoil moisture deficit

The sign convention is explicit and enforced: `TSMD = 0 mm` is field capacity,
and increasingly negative TSMD means progressively drier soil.

For the reference 0–23 cm layer:

\[
TSMD_{max}=-(20+1.3C-0.01C^2),
\]

where `C` is clay percentage. At another depth `d`, this is multiplied by
`d/23`. The monthly water increment is:

\[
\Delta W=Rain-0.75E_{pan}.
\]

Accumulated TSMD cannot exceed zero. Covered soil is capped at `TSMD_max`.
Bare soil uses the official-code dry limit `0.556 TSMD_max`; if it is already
drier than that limit, it cannot dry further during a bare month but rainfall
can wet it.

The narrative model description expresses this limit as division by `1.8`
(`0.555...`), while the official executable Python release uses `0.556`. This
implementation follows the executable release exactly and records the small
source discrepancy as an unresolved documentation detail.

Let `TSMD_1bar = 0.444 TSMD_max`. The moisture modifier is:

\[
b=1 \quad \text{when } TSMD_{acc}>TSMD_{1bar},
\]

otherwise:

\[
b=0.2+0.8\frac{TSMD_{max}-TSMD_{acc}}
{TSMD_{max}-TSMD_{1bar}}.
\]

Monthly forcing accepts open-pan evaporation. If only PET is available it must
be converted to open-pan equivalent before entering the core; RothC then
applies the configured 0.75 factor internally.

### Soil cover

The official cover modifier is `c=0.6` for covered soil and `c=1.0` for bare
soil. Physical soil cover is not treated as AMF host presence.

## Clay-dependent partition and internal routing

For each active pool's decomposed carbon, RothC calculates:

\[
x=1.67(1.85+1.60\exp(-0.0786C)),
\]

where `x` is the `CO2 / (BIO + HUM)` ratio. Therefore:

\[
f_{CO2}=\frac{x}{x+1}, \qquad f_{retained}=\frac{1}{x+1}.
\]

Retained carbon is routed using the configured official fractions:

\[
f_{BIO}=0.46f_{retained}, \qquad
f_{HUM}=0.54f_{retained}.
\]

Every source pool consequently records explicit immutable transfers to the
atmosphere, microbial biomass and protected/humified pool. BIO-to-BIO and
HUM-to-HUM recycling remain explicit rather than hidden. Higher clay lowers
the CO2/retained ratio and increases the retained fraction.

## Step order and accounting

Phase 4 resolves external-input timing in favour of official RothC ordering:
existing pools decompose first, then configured external DPM, RPM and direct
protected-pool inputs are added. Harvest residues composed by the Phase 4
kernel use the same post-decomposition ordering and cannot decay until the
following month.

The prior Phase 3 default added external inputs before decomposition. Explicit
`legacy_pre_decomposition` configuration remains available to reproduce those
input-bearing trajectories. No-input months are identical under both modes, so
the published January 1852 parity calculation is unaffected. Default outputs
with positive external input have intentionally migrated because fresh input
no longer decomposes immediately.

IOM has no decay or transfers and is invariant. Each month and complete
trajectory verify:

\[
C_{initial}+C_{external}=C_{final}+C_{respired},
\]

with signed residual:

\[
r=(C_{initial}+C_{external})-(C_{final}+C_{respired}).
\]

Internal transfers cancel. Pools, forcing, modifiers and fluxes must be finite;
pools and external inputs cannot be negative; TSMD cannot be positive. Results
include units, source/version provenance and the explicit uncertainty status
`not_quantified_in_phase_3`.

## Official worked-example parity

Source: Coleman, K., Prout, J. M. and Milne, A. E. (February 2024), *RothC – A
model for the turnover of carbon in soil: Model Description*, section 2.2,
January 1852 Hoosfield unmanured plot, distributed with official RothC_Py
v1.0.0.

Inputs reported by the source:

- initial DPM `0.1533`, RPM `4.4852`, BIO `0.6671`, HUM `25.8576`, IOM `2.7000 t C ha-1`;
- no January plant or FYM input;
- clay `23.4%`;
- combined environmental modifier `abc=0.3561`;
- rates DPM `10.0`, RPM `0.3`, BIO `0.66`, HUM `0.02 year-1`;
- CO2/(BIO+HUM) reported as `3.51`, followed by 46%/54% BIO/HUM routing.

The source does not report the component January weather values in section 2.2.
The parity test therefore inverts the official temperature equation to produce
`a=0.3561` and uses wet bare forcing so `b=c=1`. This exercises the integrated
modifier path without inventing an undocumented environmental factor.

| Output pool/flux (`t C ha-1`) | Published expected | Observed | Tolerance |
|---|---:|---:|---:|
| DPM | 0.1140 | 0.1139371278 | absolute `1e-4` |
| RPM | 4.4455 | 4.4454477169 | absolute `1e-4` |
| BIO | 0.6651 | 0.6651053396 | absolute `1e-4` |
| HUM/protected proxy | 25.8551 | 25.8551050324 | absolute `1e-4` |
| CO2-C | 0.0836 (sum of published rounded components) | 0.0836047833 | absolute `1e-4` |

The tolerance reflects the source's four-decimal printed inputs and outputs.
This is implementation verification, not calibration or external validation.
