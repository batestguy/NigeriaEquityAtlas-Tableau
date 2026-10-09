# Claims ledger

What this atlas may and may not say, and why. Read this before writing any
caption, title, subtitle, alt text or tooltip.

The governing constraint: **everything here is an aggregate of ~37 units, and the
published estimates carry a median relative standard error of 15%.** Claims that
would be unremarkable about a national time series are not available at this
scale.

---

## 1. What the numbers actually are

| Measure | What it is | Precision |
|---|---|---|
| `mpi` | Global MPI = H × A, headcount-adjusted | SE 0.0016–0.0416, median relative 15% |
| `headcount_ratio_pct` | H — % of population poor | SE 0.9–4.2 pp |
| `intensity_pct` | A — % depth of poverty among the poor | no published SE |
| `contrib_*_pct` | % of the MPI attributable to each dimension | no published SE; sum to 100 by construction |
| `conflict_exposure_index` | 0–100 min-max of per-100k event and fatality rates **within each survey year** | relative, not absolute; one state takes 100 |
| `temp_mean_c`, `precip_total_mm` | ERA5-family gridded values sampled at 37 capitals, 1990–2024 | point sample, not an areal mean |
| `baseline_*` | 1991–2020 mean at those same points | as above |

**Health is child mortality alone.** Nutrition is excluded for all 37 states in
all four rounds. Under OPHI's rule the surviving health indicator takes the
**full one-third weight**, not one-sixth. So Nigeria's Health dimension is
structurally more influential than in a fully-specified country, and Nigeria's
0.175 is not on the same scale as a country that reports all ten indicators.

---

## 2. Permitted claims

| Claim | Wording to use |
|---|---|
| Nigeria's global MPI, 2021 | "Nigeria's global MPI was 0.175 (MICS 2021), headcount 33.0%, intensity 52.9%." Name the survey year and say *global* MPI. |
| A state sits above/below the national average | Permitted. OPHI MN 56 sanctions it via population-subgroup decomposability, within a country, same survey year. |
| Group-level ordering | "The north-west states occupy the top of the distribution" — **not** "Bauchi is poorest." Bauchi, Jigawa, Kebbi and Sokoto are statistically indistinguishable (z = 0.08). |
| Dimension contrast | "Lagos is 70% health-driven; Bauchi 15%." A 55-point spread dwarfs sampling noise. **Survives.** |
| Dimension contrast, weaker form | Do not rank *within* a group. Yobe 6% vs Bauchi 16% health is a 9-point gap. |
| Correlation between two state series | "State-level Spearman rho between MPI and X is Y, n = 37." Always with n, always with the power caveat. |
| The conflict finding | "We detect no stable cross-sectional association between state MPI and conflict exposure across four survey years." Then the power number. |
| Borno's exposure | "Borno records the most *reported* conflict exposure of the 37 states in 2021." |
| Zero-event states | "10 of 37 states recorded no UCDP event in 2021, which reflects reporting coverage as much as absence of violence." |
| Resolution limit | "State is the finest resolution at which the survey supports estimates." |
| Party and poverty | Only the pre-registered federal-alignment result, in the exact sentence `docs/party_alignment.md` §4 selected from §3. Within-state over 2013–2021, n = 36 (FCT has no governor). |

---

## 3. Blocked claims

| Claim | Why blocked | If you want it anyway |
|---|---|---|
| "Bauchi has the highest MPI" | 95% CIs overlap for all 36 adjacent rank pairs | State the band |
| "Conflict and poverty are not associated" | Power is 0.75 at rho = 0.4, 0.87 at 0.5 — the design cannot see a moderate effect. And the conflict variable undercounts *worst* where poverty is highest | "No detectable association at \|rho\| ≲ 0.4" |
| "Wetter states have lower MPI (rho = −0.80)" | Precipitation is latitude (rho = −0.90); latitude predicts MPI *better* (+0.82) than precipitation does | "Consistent with a north–south development gradient of which baseline precipitation is one component; not identified as a climate effect" |
| "Climate drives poverty in Nigeria" | The identified literature uses panels and instruments; this is one cross-section | Use OPHI's word: *overlap* |
| "MPI fell 0.230 → 0.175" | **Confirmed:** the downloaded rounds are the *standardised* series (HDX resource description says so), which OPHI says "may not be comparable across time" | Re-source from the harmonised series, or drop the word "fell" |
| "Nigeria's MPI is low compared with DRC/Ethiopia" | Nutrition-missing re-weighting. UNDP's own table footnote says caution | Prohibit cross-country comparison outright |
| "Nigeria's national average is 0.175" | Nigeria also has an official NBS national MPI of 0.257 (63% headcount, four dimensions incl. work-and-shocks) | Always say "**global-MPI** national average" |
| "Zero-conflict states are peaceful" | 2021's zero-event states are the *poorest* states. It is a coverage statement | "No *reported* event" |
| "Borno's high poverty follows from the insurgency" | Ecological fallacy, and Borno's 2021 MPI samples 29% of its population | Forbidden outright |
| Any household, LGA or person-level statement | Aggregate-of-37 only | Forbidden outright |
| Any WCAG-conformance claim | Tableau Public is not on the Server/Cloud conformance path; Salesforce's own report records partial support | Don't claim it |
| "PDP/APC/ANPP states are poorer" (dominant party as explanation) | 26 of 36 states have mode PDP; the ANPP group is 3 northern poorest states, so a party gap is the latitude gradient again; no time alignment, and poor states electing a party is indistinguishable from a party governing poor states | Hover context only. The tested question is federal alignment: `docs/party_alignment.md` |
| "Party is not associated with poverty" | A null result is bounded by the test's minimum detectable effect | Use the §3 "not detected" sentence with its MDE |
| Colouring the map by party | Invites reading poverty geography as party geography | Forbidden; MPI band only |

---

## 4. Why the conflict and climate layers are weaker than they look

Worth understanding, because both are attacked by the same move.

**The conflict layer.** UCDP GED is built from newswire reporting; its own
codebook says media reporting "is not consistent across time or space". Nigerian
farmer–herder conflict, banditry and communal violence are rural, frequently
reported without reliable death tolls, and often without a state name. The
result lands where we need it not to: the five poorest states all record zero
events in 2021. That is not evidence of peace; it is evidence the instrument was
looking elsewhere.

Meanwhile **the authors of our own poverty index published the opposite
finding.** OPHI/UNDP's 2024 global MPI report is titled *Poverty amid conflict*
and reports 34.8% poverty in conflict-affected countries against 10.9%
elsewhere. They used UCDP. A reviewer will notice that you used UCDP too and got
the other answer. The difference is design — they compare countries, we compare
states within one country, at n = 37 — and that must be stated, not left
unexplained.

The literature cuts both ways, which is worth saying: Djankov & Reynal-Querol
(2008) show the strong-looking cross-sectional conflict–poverty correlation
disappears under country fixed effects. Our null is the same finding one level
down. It is not evidence of absence, and it is not evidence of presence.

**The climate layer.** Three separate problems. Baseline rainfall is geography
(A2). Annual totals at 37 capital points discard the hazard — onset date,
dry-spell length, flood — which is what the Nigerian literature says matters.
And Open-Meteo serves ERA5-family grids, which carry a documented wet bias
(Lavers & Villarini 2022) and miss orographic enhancement; the Jos/Plateau "coolest
result" we currently treat as QC validation is more likely elevation bias.

OPHI's 2025 report already did this properly — gridded hazards on a harmonised
administrative geometry across 1,657 regions — and they chose *hazards* (heat,
drought, flood, air pollution), not precipitation levels. Two of their four are
absent here entirely. Being a weaker version of a flagship analysis published by
the same people whose index we use is an unavoidable comparison; pre-empt it.

---

## 5. Wording rules for the viz

- **Lead with the negative result.** "Conflict and poverty are not associated"
  lives only in `AGENTS.md` today. A viewer of the published scatter will assume
  a relationship was found.
- **Never quote one round.** State the range and the sign flip.
- **Every correlation carries n and the power floor.**
- **Every ordering claim is a band, not a name.**
- **Every zero is "no reported event."**
- **Every index is described as relative within its year.**
- **State is stated as the survey's resolution limit**, not as a fact about
  Nigeria's natural geography.
- **Alt text describes, it does not interpret.** No "shows the troubling
  north–south divide."

---

## 6. The strongest defensible story

If the atlas has to be one thing, it should be this — because it survives every
criticism above.

**Poverty in Nigeria has fallen while its geography has not changed.** Rank
persistence between consecutive rounds is 0.867–0.924; the median state moves 2–3
positions. And the *reason* differs by region: in the north-west states poverty
is driven by education and living standards (Bauchi 15% health-driven, Yobe 6%),
while in the south-east it is driven by health (Lagos 70%, Abia 58%). That
contrast is 55–64 points wide, far beyond sampling noise at a 15% relative SE.

The equality finding survives the fact that no single state's rank is
statistically resolvable — because it is a contrast *between groups*, not an
ordering *within* a group. Level fell; structure held; and structure differs by
region in a way that points at different interventions.

The conflict and climate layers are honest negatives with documented power and
coverage limits. That is worth more than a correlation we cannot defend.

---

## 7. Sources behind these judgements

- Alkire, S., Mishra, R., Selden, L. & Suppa, N. (2025). *Global MPI 2025:
  disaggregation results and methodological note.* OPHI Methodological Note 62.
  — source of Table 5.4, the standard errors, and the disaggregation criteria.
  `Nigeria 2021 MICS` on HDX, resource "Nigeria MPI Trends Over Time", states
  its rounds are *standardised* estimates — the basis for the A4 finding.
- Alkire, S. & Foster, J.E. (2011). "Counting and multidimensional poverty
  measurement." *Journal of Public Economics* 95(7–8): 476–487.
- OPHI Methodological Note 58 (2024) — "may not be comparable across time."
- OPHI Methodological Note 56 (2023) — decomposability, state vs national.
- UNDP & OPHI (2024). *Global MPI 2024: Poverty amid conflict.*
- UNDP & OPHI (2025). *Global MPI 2025: Overlapping Hardships.* Plus Alkire et
  al., OPHI RP 70a.
- NBS/UNICEF (2022). *Nigeria 2021 MICS Survey Findings Report*, §2.2 — the
  Borno 7-of-27-LGA sampling limitation.
- Sbarra, N. et al. (2023). *Scientific Reports* 13:11085 — Borno
  non-representativeness.
- Djankov, S. & Reynal-Querol, M. (2008). "Poverty and Civil War: Revisiting
  the Evidence." CEPR DP 6980.
- Burke, M., Hsiang, S. & Miguel, E. (2015). *Nature* 527: 235–239.
- Lavers, A. & Villarini, G. (2022). *QJRMS* — ERA5 precipitation bias.
- UCDP GED Codebook v24.1 — media-construction and spatial-coverage limits.
- Robinson, W.S. (1950). *American Sociological Review* 15: 351–357.
- Openshaw, S. (1983). *The Modifiable Areal Unit Problem.* CATMOG 38.
- Beconytė, V. et al. (2022). "Where Maps Lie." *ISPRS IJGI* 11(1): 64.
- Schiewe, J. (2019). *CaGIS* — small-area detection rates.
- Cleveland, W.S. & McGill, R. (1985). *Science* 229: 828–833.
- Crameri, F., Kok-Slok, S. & Le Blanc, S. (2020). *Nature Communications* 11:5444.
- W3C. WCAG 2.1 SC 1.4.1 (Use of Color), SC 1.4.11 (Non-text Contrast).

Full audit trail with per-finding verdicts and quotes: `docs/FIX_LEDGER.md`.