# How every derived number in this atlas is defined

Baseline vintage: **MICS 2021** (36 states + FCT = 37 admin-1 units).

## MPI

Published as-is by OPHI / UNDP Global MPI. No rescaling. MPI = H x A, where H is
the headcount ratio (% of people multidimensionally poor) and A is the intensity of
deprivation (average deprivation score among the poor).

Dimension figures are the **percentage contribution of each dimension to the MPI**
(Health, Education, Living Standards). They sum to 100 within each state. Nigeria's
MPI uses 9 indicators; Nutrition is excluded for every state, so the Health
dimension rests on child mortality alone.

## Conflict Exposure Index (0-100)

Per the project spec, step 4. Computed for each state and each MPI survey year:

```
events_per_100k      = events in year / population * 100000
fatalities_per_100k  = best-estimate fatalities in year / population * 100000
events_scaled        = 100 * (events_per_100k      - year_min) / (year_max - year_min)
fatalities_scaled    = 100 * (fatalities_per_100k  - year_min) / (year_max - year_min)
Conflict Exposure Index = (events_scaled + fatalities_scaled) / 2
```

**Scaling is done within each survey year, not pooled across years.** Two
consequences, both intentional:

1. The poverty/conflict comparison is always same-year, so a state is never
   measured against a different year's violence.
2. The index is **cross-sectionally relative**. 0 means "fewest events and
   fatalities per 100k of these 37 states that year"; 100 means "most". It is not
   an absolute risk level and values are **not comparable across survey years**.

Min/max anchors for every round are written to `data/processed/atlas_vintages.csv`
so the scale can be reproduced or re-anchored.

Source: UCDP Georeferenced Event Dataset, types 1-3, `best` fatality estimate.

## Climate

Annual values are aggregated from Open-Meteo daily series at the state capital
(GeoNames admin-1 seat coordinates, `data/reference/state_capitals.csv`):

- `temp_mean_c` = mean of daily mean temperature over the calendar year
- `precip_total_mm` = sum of daily precipitation over the calendar year
- `temp_anomaly_c` = `temp_mean_c` - mean of that capital's 1991-2020 mean temperature
- `precip_anomaly_pct` = 100 * (`precip_total_mm` - baseline annual precipitation) / baseline

Baseline period 1991-2020 (the WMO standard normal period). Anomalies are relative
to each capital's own baseline, so they compare capitals against their own climate,
not against a single national figure.

## Population denominators

Per-state population comes from the UNDP Global MPI subnational table
(`population_thousands`), summing to 227.9 million with state shares summing to
exactly 100%. The table does not state a year for this column; it sits alongside
its own "Population 2022" and "Population 2023" country columns (223.2 million for
2023), so the state figures run about 2% above the workbook's own 2023 national
total and are probably a later vintage.

Two documented approximations follow:

- Per-100k conflict rates for the 2021 baseline use a population vintage later than
  2021, biasing rates low by a few percent uniformly.
- The same denominator is reused for all four survey rounds. Because the index is
  min-max scaled within each round, a uniform bias cancels exactly; what does not
  cancel is *differential* population growth across states between 2013 and 2021.
