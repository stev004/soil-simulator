# Empirical pilot evidence extraction

## Coordinate frame and acceptance

The executable frame is a literal ordered tuple of 64 IDs, regions and coordinates rounded to 0.1 degrees. The archive states only that they were predeclared and do not identify farms/fields. It does **not** state how the 64 coordinates were selected from a GB geographic frame; no selection algorithm, sampling probabilities, grid construction or frame source was found. Classification: `PARTIALLY_RESOLVED`. Sources: `src/soil_simulator/phase96/empirical.py:32-110` (`PilotLocation`, `PILOT_LOCATIONS`); `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json` (`coordinate_policy`, `sampling_frame_locations`).

| location | region | latitude (degrees) | longitude (degrees) |
|---|---|---:|---:|
| gb001 | south_west | 50.4 | -4.8 |
| gb002 | south_west | 50.7 | -3.7 |
| gb003 | south_west | 50.8 | -2.3 |
| gb004 | south_west | 51.1 | -2.7 |
| gb005 | south | 51.2 | -1.8 |
| gb006 | south | 51.1 | -1.2 |
| gb007 | south | 50.9 | -0.3 |
| gb008 | south_east | 51.2 | 0.8 |
| gb009 | south_east | 51.3 | -0.5 |
| gb010 | south | 51.5 | -1.0 |
| gb011 | south | 51.8 | -1.3 |
| gb012 | west_midlands | 51.9 | -2.2 |
| gb013 | west_midlands | 52.1 | -2.7 |
| gb014 | west_midlands | 52.2 | -2.2 |
| gb015 | west_midlands | 52.3 | -1.5 |
| gb016 | east_midlands | 52.3 | -0.8 |
| gb017 | east | 52.0 | -0.5 |
| gb018 | east | 52.3 | 0.0 |
| gb019 | east | 52.2 | 0.8 |
| gb020 | east | 52.7 | 1.0 |
| gb021 | south_east | 51.8 | 0.6 |
| gb022 | south_east | 51.9 | -0.2 |
| gb023 | east_midlands | 52.7 | -1.1 |
| gb024 | east_midlands | 53.0 | -1.0 |
| gb025 | east_midlands | 53.2 | -0.3 |
| gb026 | east_midlands | 53.0 | -1.6 |
| gb027 | west_midlands | 52.7 | -2.6 |
| gb028 | west_midlands | 52.9 | -2.0 |
| gb029 | north_west | 53.1 | -2.5 |
| gb030 | yorkshire | 53.8 | -1.2 |
| gb031 | yorkshire | 53.9 | -0.5 |
| gb032 | yorkshire | 54.2 | -1.4 |
| gb033 | north_west | 53.8 | -2.7 |
| gb034 | north_west | 54.5 | -2.8 |
| gb035 | north_east | 54.7 | -1.6 |
| gb036 | north_east | 55.1 | -1.8 |
| gb037 | wales | 51.8 | -4.8 |
| gb038 | wales | 51.9 | -4.2 |
| gb039 | wales | 52.2 | -4.0 |
| gb040 | wales | 52.3 | -3.3 |
| gb041 | wales | 51.5 | -3.4 |
| gb042 | wales | 51.8 | -2.9 |
| gb043 | wales | 53.1 | -3.0 |
| gb044 | scotland_south | 55.0 | -3.6 |
| gb045 | scotland_south | 55.6 | -2.7 |
| gb046 | scotland_south | 55.6 | -4.5 |
| gb047 | scotland_east | 55.9 | -3.3 |
| gb048 | scotland_east | 56.2 | -3.1 |
| gb049 | scotland_east | 56.6 | -2.9 |
| gb050 | scotland_east | 56.4 | -3.5 |
| gb051 | scotland_north_east | 57.2 | -2.2 |
| gb052 | scotland_north_east | 57.6 | -3.3 |
| gb053 | scotland_north | 57.6 | -4.2 |
| gb054 | scotland_south | 55.7 | -3.8 |
| gb055 | scotland_central | 56.1 | -4.0 |
| gb056 | scotland_north_east | 57.4 | -2.8 |
| gb057 | south_east | 51.0 | 0.6 |
| gb058 | east_midlands | 52.4 | -0.2 |
| gb059 | east | 52.8 | 0.2 |
| gb060 | yorkshire | 53.4 | -1.0 |
| gb061 | yorkshire | 53.5 | -0.3 |
| gb062 | north_west | 54.0 | -2.0 |
| gb063 | north_east | 55.0 | -2.5 |
| gb064 | scotland_east | 56.0 | -2.8 |

The table is an exact transcription of the executable tuple, not a reconstructed sampling rule. Source: `src/soil_simulator/phase96/empirical.py:42-110` (`PILOT_LOCATIONS`).

Soil records are rejected if any required property (`bdod, cec, clay, nitrogen, phh2o, sand, silt, soc`) is absent, if a required 0-5/5-15/15-30 cm median is missing, or if the weighted texture total is non-positive. Climate records are rejected if any T2M/T2M_MAX/T2M_MIN/PRECTOTCORR value is non-finite or `<= -900`; complete 12-month years are required. Sources: `src/soil_simulator/phase96/empirical.py:122-160,248-342` (`_depth_values`, `harmonise_soilgrids`, `build_empirical_records`); `src/soil_simulator/phase96/empirical.py:406-413` (`to_empirical_dataset`).

The eight observed source-record rejections were:

- `gb009`: missing Q0.5 for bdod 0-5cm. Source: `outputs/phase96_v0.9.6/generated_population_manifest.json` (`empirical_record_rejections`).
- `gb014`: missing Q0.5 for bdod 0-5cm. Source: `outputs/phase96_v0.9.6/generated_population_manifest.json` (`empirical_record_rejections`).
- `gb017`: missing Q0.5 for bdod 0-5cm. Source: `outputs/phase96_v0.9.6/generated_population_manifest.json` (`empirical_record_rejections`).
- `gb022`: missing Q0.5 for bdod 0-5cm. Source: `outputs/phase96_v0.9.6/generated_population_manifest.json` (`empirical_record_rejections`).
- `gb035`: missing Q0.5 for bdod 0-5cm. Source: `outputs/phase96_v0.9.6/generated_population_manifest.json` (`empirical_record_rejections`).
- `gb046`: missing Q0.5 for bdod 0-5cm. Source: `outputs/phase96_v0.9.6/generated_population_manifest.json` (`empirical_record_rejections`).
- `gb047`: missing Q0.5 for bdod 0-5cm. Source: `outputs/phase96_v0.9.6/generated_population_manifest.json` (`empirical_record_rejections`).
- `gb057`: missing Q0.5 for bdod 0-5cm. Source: `outputs/phase96_v0.9.6/generated_population_manifest.json` (`empirical_record_rejections`).

All eight were missing `bdod` Q0.5 at 0-5 cm; 56 locations were accepted. Source: `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json` (`accepted_locations=56`, `rejected_locations=8`).

## Processed columns and units

The processed soil file has exactly: `location_id`, `region`, rounded latitude/longitude, climate-grid latitude/longitude, `soil_depth_cm`, clay/silt/sand percent, bulk density g cm-3, pH(H2O), CEC cmolc kg-1, total N percent, SOC concentration g kg-1, and SOC stock t C ha-1 for 0-23 cm. Source: `data/processed/phase96_empirical_soil_locations_v1.csv:1` (header).

For each SoilGrids layer, the median is `Q0.5 / unit_measure.d_factor`. Let layer thicknesses be 5, 10 and 8 cm for 0-5, 5-15 and the top 8 cm of 15-30 cm. Any intensive property is harmonised as (x_{0-23}=(5x_1+10x_2+8x_3)/23). Total N is subsequently divided by 10 to percent. Sources: `src/soil_simulator/phase96/empirical.py:26-29,127-142,169-174`.

SOC stock is computed layerwise and summed: (SOC_{stock}=\sum_d SOC_d[g\,kg^{-1}]BD_d[g\,cm^{-3}]z_d[cm]\times0.1) t C ha-1. Source: `src/soil_simulator/phase96/empirical.py:145-175` (`harmonise_soilgrids`).

Texture is first thickness-weighted independently, then each component is multiplied by `100 / (raw_clay+raw_silt+raw_sand)`. The manifest records pre-correction total, absolute closure correction and whether the raw total differed from 100 by more than 0.01. Source: `src/soil_simulator/phase96/empirical.py:156-181`; corrections: `outputs/phase96_v0.9.6/generated_population_manifest.json` (`texture_corrections`).

Climate columns are location, region, year, month, mean/min/max air temperature, monthly precipitation and monthly PET. PRECTOTCORR is converted from daily rate to monthly total by multiplying calendar days. Thornthwaite PET uses 12 monthly T2M values, heat index (I=\sum(max(T,0)/5)^{1.514}), exponent (a=6.75\,10^{-7}I^3-7.71\,10^{-5}I^2+1.792\,10^{-2}I+0.49239), latitude/daylength, and (PET=16(L/12)(d/30)(10T/I)^a). Sources: `data/processed/phase96_empirical_monthly_climate_v1.csv:1`; `src/soil_simulator/phase96/empirical.py:185-219,287-320`.

## Descendants and latent priors

The requested population size is 112, and the generator first forces at least one accepted descendant per sorted empirical seed, then cycles through seeds until 112 fields pass QC. Consequently descendant counts are not exactly two after candidate rejection, although the mean is two; exact counts are in `DATA_SPLIT_REGISTER.csv`. Source: `config/populations/phase96_population.yaml:3`; `src/soil_simulator/population/generator.py:439-484` (`generate_population`).

Texture uses two independent Normal(0,0.08) additive-log-ratio perturbations for clay/sand and silt/sand, followed by exact inverse closure. SOC uses `seed_SOC*exp(Normal(0,0.06))`, bounded to ±20% of the seed and then [5,250] t C ha-1; the shared Normal factor has SD 0 and is disabled. Bulk density adds Normal(0,0.04), `-0.002*clay_shift`, is bounded ±12% of its seed, then [0.7,1.8]. pH adds Normal(0,0.08) and `0.003*clay_shift`, then clamps [4,8.5]. Sources: `config/populations/phase96_population.yaml:15-20,23,28-33`; `src/soil_simulator/population/generator.py:45-57,255-302`.

Available P is anchored at 20 kg P ha-1, multiplied by `exp(Normal(0,0.18)+0.20*shared)`, bounded ±20% and then [0.1,200]. CEC is `max(0.1,seed_CEC*exp(0.45*shared+0.012*clay_shift))`; N is `max(0.01,seed_N*(SOC/seed_SOC)^0.8)`. Sources: `src/soil_simulator/phase96/empirical.py:383-391`; `src/soil_simulator/population/generator.py:303-322`; `config/populations/phase96_population.yaml:21,34-35`.

AMF live/necromass anchors are 0.20/0.10 t C ha-1. With (e\sim Normal(0,0.40)) and (p=\log(P/20)), live AMF is `0.20*exp(e-0.25p)` and necromass is `0.10*exp(0.6e)`. Drainage and management history are the literal label `not_observed_scenario_assumption`, not sampled distributions. Sources: `src/soil_simulator/phase96/empirical.py:388-402`; `src/soil_simulator/population/generator.py:323-326`; `config/populations/phase96_population.yaml:22`.

Each field also carries seven biological draws: scaled Beta(2,8) allocation [0.02,0.20], triangular CUE [0.30,0.65] mode 0.45, log-uniform turnover [0.1,6], scaled Beta(2,5) stabilisation [0.02,0.50], triangular P Vmax [0.2,3] mode 1, triangular conventional-tillage mortality [0,0.60] mode 0.25, and Beta(8,2) cover establishment success. Source: `src/soil_simulator/population/generator.py:83-168` (`_latent_draws`).

Pool allocation is not a Dirichlet prior. IOM is `0.049*SOC^1.139`; the residual target after IOM and AMF is allocated by a periodic complete-weather RothC spin-up with annual reference input 2.5 t C ha-1, 1.44 DPM:RPM split, maximum 3000 years and relative-cycle tolerance 1e-6, then linearly scaled to target active SOC. Sources: `src/soil_simulator/population/spinup.py:28-170`; `config/populations/phase96_population.yaml:25-27`; RothC IOM constants: `config/model_defaults.yaml:27-28`.

## Splits and OOD construction

Four region IDs—`gb051`, `gb052`, `gb053`, `gb056`—are assigned `weather_ood`; the archetype-OOD configuration is an empty list. All other accepted seed IDs are deterministically shuffled with a SHA-256-derived seed from generation seed 209600, then rounded 60%/20%/20% into train/validation/test. Descendants inherit their seed's group and a seed cannot be both OOD types. Sources: `config/populations/phase96_population.yaml:4,7-11`; `src/soil_simulator/population/generator.py:171-203` (`_split_by_seed`).

This final pilot does not perturb weather to create OOD. The OOD label selects four empirical location regions; each field resamples ten complete 2001-2020 years with replacement from its own region. The repository does not document why these four region IDs were chosen. Sources: `src/soil_simulator/population/generator.py:206-235`; `config/populations/phase96_population.yaml:11`.

The archived result contains 59/21/26/6 descendants in train/validation/test/weather-OOD, representing 31/10/11/4 locations. No location crosses groups. Source: `outputs/phase96_v0.9.6/generated_population_manifest.json` (`split_counts`, `location_group_leakage`); complete assignments: `DATA_SPLIT_REGISTER.csv`.
