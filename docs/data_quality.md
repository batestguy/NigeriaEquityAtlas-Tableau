# Data quality and caveats

Read this before quoting any number from the atlas.

## Sources and vintages

| Layer | Source | Licence | Vintage |
|---|---|---|---|
| Poverty | OPHI + UNDP Global MPI subnational database | CC0 / CC BY | MICS 2021 (+ 2013 DHS, 2016 MICS, 2018 DHS trends) |
| Conflict | UCDP Georeferenced Event Dataset | CC BY-IGO | 1990-2024 |
| Climate | Open-Meteo Archive API | free, keyless | 1990-2024 daily |
| Boundaries | geoBoundaries ADM1 | CC BY 4.0 | 2024 release |
| Capitals | GeoNames `cities5000` | CC BY 4.0 | gazetteer |

OPHI and UNDP are independent publications of the same 2021 survey. They are
reconciled state by state on every pipeline run and the run aborts if any MPI value
disagrees by more than 1e-3.

## Known limitations

1. **The Health dimension is narrower than the standard MPI.** All 37 states report
   Nutrition as excluded, so Health is carried by child mortality alone. Health is
   therefore comparable *between* Nigerian states but not directly comparable to
   published MPI figures from countries that do use a nutrition indicator.

2. **The Conflict Exposure Index is relative, not absolute.** See
   `normalisation.md`. Do not describe a state as having "a Conflict Exposure Index
   of 80" without saying it is the highest among these 37 states that year.

3. **Conflict and poverty are not matched samples.** UCDP events are media-reported
   and coverage is uneven across states; the MPI is survey-based. A correlation
   between them is an association between two differently-measured quantities, and
   reverse causation is at least as plausible as the reverse.

4. **UCDP, not ACLED.** The project spec asked for ACLED. ACLED was unobtainable in
   this environment (the API host does not resolve, and HDX only carries ACLED's
   country-year/month aggregates). UCDP covers the same period, is open, and is
   georeferenced per event, but it counts events on different criteria -- so
   conflict magnitudes here are not comparable to an ACLED-based figure.

5. **Zero conflict events is not zero conflict.** In 2021, 10 of 37 states recorded
   no UCDP event at all. That reflects reporting coverage as much as actual absence
   of violence. These are written as explicit zeros, not nulls.

6. **Gongola.** One UCDP event is attributed to "Gongola state", an administrative
   unit abolished in 1991 and since divided between Adamawa and Taraba. It is
   attributed to Adamawa; the row is retained in
   `data/interim/conflict_events_attributed.csv` with `attribution_method =
   obsolete_unit`.

7. **FCT is a state here.** It is included in every aggregate. Dropping it is a
   common and silent error -- it is also the territory whose OPHI PCode is blank in
   the source, so it is the row most likely to vanish in a join.

8. **Climate is sampled at capitals.** A capital's climate is a reasonable proxy for
   a state but not an areal average. Large states (Borno, Bauchi, Katsina) span
   several climate zones.
