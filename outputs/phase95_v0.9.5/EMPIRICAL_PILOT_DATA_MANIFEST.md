# Phase 9.5 empirical-pilot data manifest

Status: **blocked** on 2026-07-21. Completed empirical locations: **0 of 50**.

No empirical fixture was created and no coordinates are stored. The required
pilot needs coarsened, non-sensitive location/grid identifiers; harmonized
0--23 cm clay, silt, sand, SOC stock, bulk density and pH; and monthly
temperature, precipitation and potential evapotranspiration with explicit
source versions, depths and units.

Sources assessed:

- SoilGrids 2.0: the official point REST service was paused and no reliable,
  immutable 50-location extraction was available.
- LUCAS 2018 topsoil: access requires registration; no authenticated,
  version-pinned extraction was available.
- ERA5-Land monthly means: documented climate data were available, but climate
  alone cannot satisfy the paired soil-climate pilot.

The existing ten-seed fixture remains a hand-authored synthetic demonstration
fixture, SHA-256
`e4be837e544d2fe30c31ad7a4ec527baf13ce8cb120dccbfdf69424bbd744210`.
It is not empirical evidence.
