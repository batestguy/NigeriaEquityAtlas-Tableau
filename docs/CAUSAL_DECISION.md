# The causal question: decision and reasoning

Asked: choose the best possible and defensible path for a causal argument, and give
reasons why it should be so.

**Decision: do not make a causal argument. Make a decomposition argument.**

Not a hedge — a positive choice, and a better one. A causal claim in this atlas is
undefendable on five independent grounds, any one of which is fatal on its own.
Meanwhile the decomposition claim is defensible *because* it needs no causal
identification, and it is the more interesting finding.

---

## 1. Why every causal path is closed

I tested each one rather than reasoning about it. All five fail.

### 1a. Geography and poverty level are collinear — cannot be separated

At n = 37, the 12 states with MPI > 0.20 are:

| latitude band | poor | not poor |
|---|---|---|
| S | 0 | 9 |
| S-C | 0 | 9 |
| C-N | 4 | 5 |
| N | 8 | 1 |

**All 12 poor states are in the two northern bands. Zero are in the southern two.**
"Poor" and "northern" are, at this sample size, the same 12 observations. Any
contrast between them is equally well described as a north-south contrast or a
high-poverty contrast, and nothing in this dataset adjudicates between the two
readings.

### 1b. The within-poor trend reverses

| Sample | corr(latitude, education contribution) |
|---|---|
| All 37 | **+0.850** |
| Not-poor states (n = 25) | **+0.794** |
| **Poor states (n = 12)** | **−0.252** |

The headline gradient is carried entirely by the not-poor southern states.
Within the poor group — the group that actually matters for the claim — latitude
explains nothing, and the sign is mildly wrong.

**This falsifies the project's own current headline** ("the north-west is driven
by education and living standards; the south-east by health", asserted in
`AGENTS.md` and `HANDOFF.md` §5). That sentence is a poverty-level contrast
mislabelled as a geographic one.

### 1c. No temporal ordering helps

The one thing a cross-section cannot give is ordering. Testing it directly —
MPI in year *t* against conflict in year *t+1*:

| | → CEI | → fatalities/100k |
|---|---|---|
| 2013 → 2016 | −0.073 (p = 0.67) | −0.049 (p = 0.78) |
| 2016 → 2018 | +0.107 (p = 0.53) | +0.113 (p = 0.50) |
| 2018 → 2021 | +0.017 (p = 0.92) | +0.127 (p = 0.45) |

Nothing. Fearon & Laitin's poverty→recruitment channel and Abidoye & Calì's
income-shock→conflict identification both predict a signal here. There isn't one.

### 1d. Panel fixed effects would absorb 91% of the variance

Within-state change 2013→2021 averages 0.0398 — **9.1% of the cross-state spread**.
SD of the within-state change is 0.0453 against 0.1545 for the levels. Fixed
effects would leave ~9% of variance to explain, and it is noise.

The usual escape from cross-section — move to a panel and add fixed effects — is
the one available design here, and it is empty. That is not a judgment call, it
is arithmetic.

### 1e. No instrument, no discontinuity, no exogenous shock

- **No valid instrument.** Lags fail (1c). Predetermined geography *is* an
  instrument for rainfall, but that only identifies a climate effect, and see 2c.
- **No regression discontinuity.** State boundaries are administrative and
  arbitrary — the opposite of a sharp design.
- **No natural experiment** in the 2013–2021 window on this data. The insurgency
  escalation is not exogenous to poverty; it is arguably *caused* by it.
- **Aggregates only.** Robinson (1950): between-state relationships need not hold
  for individuals. This forbids the person-level claim regardless of
  identification.

---

## 2. Claim by claim

### 2a. Conflict → poverty: **withdraw the claim entirely**

Beyond low power (0.75 at rho = 0.4; nothing survives Bonferroni), the
measurement error is *correlated with the treatment*:

| Year | zero-event states | their mean MPI | mean MPI elsewhere |
|---|---|---|---|
| 2013 | 16 | 0.137 | 0.243 |
| 2016 | 13 | 0.218 | 0.137 |
| 2018 | 14 | 0.213 | 0.156 |
| 2021 | **10** | **0.218** | **0.142** |

In 2021 the five poorest states in Nigeria — Bauchi, Jigawa, Kebbi, Katsina,
Kano — all record zero UCDP events. UCDP GED is newswire-built; its own codebook
says reporting "is not consistent across time or space". Rural farmer–herder and
banditry violence is what it misses. **The instrument fails hardest where the
outcome is highest.** That is not noise around zero; it is bias toward zero.

Claim permitted: *"we detect no association, and our design could not have
detected |rho| below ~0.4."* Never "conflict does not affect poverty" and never
"conflict and poverty are unrelated."

### 2b. Poverty → conflict: **withdraw, and say why**

Tested directly in 1c. No signal in any lag. This is a genuine null on the
channel the literature most often invokes for Nigeria, and it is worth saying —
but as a null with power attached, not as a finding.

### 2c. Climate → poverty: **withdraw, and it is worse than a correlation problem**

Baseline precipitation ↔ latitude is **−0.903** (82% of variance). Latitude ↔
MPI is **+0.821** — better than precipitation ↔ MPI at −0.801. The predictor is
the outcome's twin.

Burke, Hsiang & Miguel (2015) survey the literature: baseline rainfall has
essentially **no** cross-sectional relationship with income; the identified work
uses panels and instruments. Dell, Jones & Olken (2009) show cross-sectional
estimates exceed panel estimates because cross-section omits unobserved
heterogeneity correlated with climate. Here that heterogeneity *is* the
north–south development gradient.

And reverse causality is not a caveat, it is the better-fitting mechanism: the
MPI contains electricity, water, sanitation, fuel and housing — the exact
indicators that mediate adaptation. Poor states have less capacity to absorb the
same rainfall.

Compounding: 37 capital point-samples, not areal means; annual totals discard
onset date, dry-spell length and flood, which is what the Nigerian literature
says matters; ERA5 carries a documented wet bias and misses orographic
enhancement — so the Jos/Plateau "coolest" QC result is more likely elevation
bias than climate.

Permitted: *"baseline precipitation is a proxy for latitude; the association
with MPI reflects a north–south development gradient, not a climate effect."*
Useful word from OPHI's 2025 report: **overlap**.

### 2d. Party → poverty: **association only, and a fragile one** (added 2026-10-09)

The dominant (mode) governorship party cannot carry any claim: 26 of 36 states are
PDP, and the three ANPP states are northern poorest states, so a cross-state party
gap is the latitude problem of 1a again. The question was therefore asked
*within states over time* — federal–state alignment against the pace of MPI change,
2013–21 — and pre-registered before any result (`docs/party_alignment.md`).

Even within states this is not causal: alignment is chosen by voters and governors
(selection), the 2015 federal change coincides with everything else that happened
in 2015, and four survey rounds give three changes per state. The result (aligned
states' MPI fell slower, p = 0.036) rests on one interval and does not survive the
sitting-party check. Permitted: the §3 sentence of `docs/party_alignment.md`,
verbatim, with its robustness line beside it. Never "alignment slowed poverty
reduction" and never "party does not matter".

---

## 3. What is left, and it is better

The MPI is H × A by construction, and the dimension contributions are an exact
algebraic decomposition of the published index. This is an **identity, not an
inference**. It requires no instrument, no ordering, no exogenous variation — and
that is precisely why it is defensible.

**Headline:** *level fell, structure held, and structure differs.*

| Finding | Value | Survives? |
|---|---|---|
| Rank persistence, consecutive rounds | 0.922, 0.924, 0.867 | Yes — within-file comparison, unaffected by harmonisation |
| Education share: poorest 12 vs other 25 | 39.9% vs 22.3% (**17.6 pts**) | Yes, Mann-Whitney p = 1e-5 |
| Health share: poorest 12 vs other 25 | 16.3% vs 31.3% (**15.0 pts**) | Yes, p = 0.006 |
| Any within-group ordering | all 36 adjacent pairs overlap | **No** |

The 17.6-point gap is the point. The median 95% CI width is 81% of the median MPI
— so no *ordering* survives — but a 17.6-point difference in a percentage is a
comparison *between groups*, and group contrasts are exactly what survives large
relative standard errors. That is the whole argument for leading with this.

Three constraints on how it gets stated:

1. **Say "poor" and "not poor", not "north" and "south".** Per 1a they are the
   same observations; only the first is supported by the index.
2. **Health is child mortality alone**, with Nutrition excluded and the health
   dimension re-weighted to a full one-third. In the richest states the
   "health-driven" share describes a tiny absolute weight — Imo's 60.3% is 0.011
   of index weight. Contribution shares are interpretable only where MPI > 0.05.
3. **State it as composition, not cause.** "The poorest states' poverty is
   education-weighted; the others' is health-weighted." Not "education
   deprivation causes poverty in the north."

### The one genuinely causal claim available

Conditional on being poor, **which deprivation dominates** is itself a
structural fact about the index — and it points at different interventions. That
is a policy-relevant claim that requires no causal identification, because it is
arithmetic on published figures.

---

## 4. Why this is the better path, not the safe one

- **It is the finding.** A null you cannot power is a null you cannot interpret.
  A 17.6-point group contrast at p = 1e-5 is a result.
- **It is unfalsifiable by the obvious attack.** The obvious attack is "that's
  just geography." Rebuttal: latitude does not vary within the poor group
  (−0.252) while the education share does. The contrast is orthogonal to
  geography in the group where it matters. The attack lands on the *naming*, and
  the naming is fixed by 1a.
- **The specs asked for overlays, not causal claims.** The original spec wants a
  choropleth, a stacked bar, two scatters and a radar. Nothing in it promises
  identification. Adopting a causal framing we cannot support would be
  volunteering for a fight nobody asked us into.
- **The critique surface is smaller.** A decomposition claim invites one
  question ("is it geography?"). A causal claim invites identification,
  endogeneity, instrument validity, spatial dependence and the ecological
  fallacy — five discussions, none winnable at n = 37.
- **It is the most publishable form of an honest result.** The reproducibility
  work — two independent reconciliations, 37/37 at every stage, 7,418 events with
  0 unattributed, a sign flip that killed a single-year approach — supports a
  methodological claim. That is a defensible viz on Tableau Public, and it is
  currently invisible to a viewer.

---

## 5. Consequence: what changes

**Withdraw:** every causal verb. "Driven by", "explains", "because of", "affects",
"leads to". `AGENTS.md`'s north-west/south-east sentence must be rewritten to
"poorest states vs the rest" — see 1b, it is currently a poverty contrast wearing
a geographic label.

**Relabel:** `Poverty vs conflict` → something stating the null. Climate layer →
gradient, or drop it. This costs two sheets of the spec's five, which is the real
price and worth paying: a viz with one defensible finding beats one with three
undefendable ones.

**Promote:** the stacked bar from tab 2 to the headline, and lead the dashboard
with the group contrast and the rank-persistence finding.

**Add:** one KPI tile for the power floor. It turns "no result" into "a result
about the limits of the design," which is the honest version and the defensible
one.

---

## 6. If you want a real causal claim later

The only route is different data, and it is worth knowing what:

1. **LGA-level poverty + LGA-level conflict.** NBS's Nigeria MPI 2022 survey was
   designed for 109 senatorial districts and was establishing an LGA baseline.
   Both the outcome and the treatment then vary at the same fine unit, which
   dissolves the 1a collinearity.
2. **Harmonised indicator definitions** so the panel is a real panel (currently
   blocked by the standardised-series problem, `FIX_LEDGER.md` A4).
3. **UCDP low–best–high fatality bands** so measurement error can be propagated
   rather than assumed.
4. **Agricultural shocks, not rainfall levels** — onset date, dry-spell length.
   Rainfall levels are geography; shocks are variation.

None is a stage-7 change. All are a different project. Record the finding, do not
stake the atlas on it.