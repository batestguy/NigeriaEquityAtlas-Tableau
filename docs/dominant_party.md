# Dominant governorship party, 1999–2021 — audit note

Display column lives in `data/reference/state_dominant_party.csv`
(`dom_party`: mode acronym, `/`-joined on ties, `—` for FCT; `win_years`:
the mode party's winning years, `PARTY:years|PARTY:years` on ties).
Shown in the interactive map hover ONLY (no on-map labels, never colour). **Context only:
never colour by party, never read party as an explanation of poverty**
(see `docs/CAUSAL_DECISION.md` — every causal path is closed at n=37).

**Whether party is associated with poverty is tested separately**, as a pre-registered
within-state federal-alignment test (`docs/party_alignment.md`). The mode label below
cannot answer that question: 26 of 36 states have mode PDP, and the non-PDP groups
are 1–3 states each. The event matrix below is the source for
`data/reference/governorship_events.csv`.

## Counting rule

One entry per governorship **seating event** 1999–2021 (scheduled cycles
1999/2003/2007/2011/2015/2019, off-cycle elections, court-ordered reruns and
court-installed winners). Party = the platform the winner ran on **in that
event**. Successions without an election (deputy takeovers, acting governors,
impeachment fill-ins) excluded. Post-election defections do NOT rewrite the
winning label (e.g. Ebonyi 2015/2019 stay PDP although Umahi defected to APC
in Nov 2020). Display = mode; ties list every tied label.

## Full event matrix (verified, not from memory)

| State | Events (year:winner) | Mode |
|---|---|---|
| Abia | 1999:PDP, 2003:PDP, 2007:PPA, 2011:PDP, 2015:PDP, 2019:PDP | PDP 5/6 |
| Adamawa | 1999:PDP, 2003:PDP, 2007:PDP, 2008:PDP, 2012:PDP, 2015:APC, 2019:PDP | PDP 6/7 |
| Akwa Ibom | 1999–2019 all PDP (6) | PDP 6/6 |
| Anambra | 1999:PDP, 2003:PDP, 2003-court:APGA, 2007:PDP, 2007-court:APGA, 2010:APGA, 2013:APGA, 2017:APGA, 2021:APGA | APGA 6/9 |
| Bauchi | 1999:PDP, 2003:PDP, 2007:ANPP, 2011:PDP, 2015:APC, 2019:PDP | PDP 4/6 |
| Bayelsa | 1999:PDP, 2003:PDP, 2007:PDP, 2008:PDP, 2012:PDP, 2016:PDP, 2019:PDP | PDP 7/7 |
| Benue | 1999:PDP, 2003:PDP, 2007:PDP, 2011:PDP, 2015:APC, 2019:PDP | PDP 5/6 |
| Borno | 1999:APP, 2003:ANPP, 2007:ANPP, 2011:ANPP, 2015:APC, 2019:APC | ANPP 3/6 |
| Cross River | 1999:PDP, 2003:PDP, 2007:PDP, 2008:PDP, 2012:PDP, 2015:PDP, 2019:PDP | PDP 7/7 |
| Delta | 1999:PDP, 2003:PDP, 2007:PDP, 2011:PDP, 2011-rerun:PDP, 2015:PDP, 2019:PDP | PDP 7/7 |
| Ebonyi | 1999–2019 all PDP (6) | PDP 6/6 |
| Edo | 1999:PDP, 2003:PDP, 2007:PDP, 2008:ACN, 2012:ACN, 2016:APC, 2020:PDP | PDP 4/7 |
| Ekiti | 1999:AD, 2003:PDP, 2007:PDP, 2009:PDP, 2010:ACN, 2014:PDP, 2018:APC | PDP 4/7 |
| Enugu | 1999–2019 all PDP (6) | PDP 6/6 |
| FCT | no elected governor (minister-appointed) | — |
| Gombe | 1999:APP, 2003:PDP, 2007:PDP, 2011:PDP, 2015:PDP, 2019:APC | PDP 4/6 |
| Imo | 1999:PDP, 2003:PDP, 2007:PPA, 2011:APGA, 2015:APC, 2019:PDP, 2019-court:APC | PDP 3/7 |
| Jigawa | 1999:APP, 2003:ANPP, 2007:PDP, 2011:PDP, 2015:APC, 2019:APC | **PDP/APC tie** 2/6+2/6 |
| Kaduna | 1999–2011 PDP (4), 2015:APC, 2019:APC | PDP 4/6 |
| Kano | 1999:PDP, 2003:ANPP, 2007:ANPP, 2011:PDP, 2015:APC, 2019:APC | **PDP/ANPP/APC 3-way tie** 2/6 each |
| Katsina | 1999–2011 PDP (4), 2015:APC, 2019:APC | PDP 4/6 |
| Kebbi | 1999:APP, 2003:ANPP, 2007:PDP, 2011:PDP, 2012:PDP, 2015:APC, 2019:APC | PDP 3/7 |
| Kogi | 1999:APP, 2003:PDP, 2007:PDP, 2008:PDP, 2011:PDP, 2015:APC, 2019:APC | PDP 4/7 |
| Kwara | 1999:APP, 2003:PDP, 2007:PDP, 2011:PDP, 2015:APC, 2019:APC | PDP 3/6 |
| Lagos | 1999:AD, 2003:AD, 2007:AC, 2011:ACN, 2015:APC, 2019:APC | **AD/APC tie** 2/6+2/6 |
| Nasarawa | 1999:PDP, 2003:PDP, 2007:PDP, 2011:CPC, 2015:APC, 2019:APC | PDP 3/6 |
| Niger | 1999–2011 PDP (4), 2015:APC, 2019:APC | PDP 4/6 |
| Ogun | 1999:AD, 2003:PDP, 2007:PDP, 2011:ACN, 2015:APC, 2019:APC | **PDP/APC tie** 2/6+2/6 |
| Ondo | 1999:AD, 2003:PDP, 2007:PDP, 2009:LP, 2012:LP, 2016:APC, 2020:APC | **PDP/LP/APC 3-way tie** 2/7 each |
| Osun | 1999:AD, 2003:PDP, 2007:PDP, 2010:ACN, 2014:APC, 2018:APC | **PDP/APC tie** 2/6+2/6 |
| Oyo | 1999:AD, 2003:PDP, 2007:PDP, 2011:ACN, 2015:APC, 2019:PDP | PDP 3/6 |
| Plateau | 1999–2011 PDP (4), 2015:APC, 2019:APC | PDP 4/6 |
| Rivers | 1999:PDP, 2003:PDP, 2007:PDP, 2007-court:PDP, 2011:PDP, 2015:PDP, 2019:PDP | PDP 7/7 |
| Sokoto | 1999:APP, 2003:ANPP, 2007:PDP, 2008:PDP, 2012:PDP, 2015:APC, 2019:PDP | PDP 4/7 |
| Taraba | 1999–2019 all PDP (6) | PDP 6/6 |
| Yobe | 1999:APP, 2003:ANPP, 2007:ANPP, 2011:ANPP, 2015:APC, 2019:APC | ANPP 3/6 |
| Zamfara | 1999:APP, 2003:ANPP, 2007:ANPP, 2011:ANPP, 2015:APC, 2019:PDP | ANPP 3/6 |

Ties (6): Jigawa PDP/APC · Kano PDP/ANPP/APC · Lagos AD/APC ·
Ogun PDP/APC · Ondo PDP/LP/APC · Osun PDP/APC.

## Lineage notes (labels counted as-won, never merged)

- **APP→ANPP (~2002 rename):** 1999 winners shown APP, 2003+ ANPP
  (Jigawa, Kebbi, Sokoto, Yobe, Borno, Zamfara, Gombe, Kogi; Kwara 1999
  corrected APP→ANPP per rename although the governor list prints ANPP).
- **SW lineage AD→AC→ACN→APC:** one political machine under four labels.
  The Lagos AD/APC "tie" is this lineage split by the no-merge rule, not a
  genuine two-party contest — same for the AC/ACN/APC fragments inside the
  Ogun, Osun and Oyo counts. Read "AD/APC" as "same camp, different eras".
- **Edo 2008:** recorded ACN (governor-list label); contemporary 2007–2008
  sources print AC. Mode unaffected (PDP 4/7 either way).
- **Court-installed winners counted:** Anambra 2003-court APGA, Edo 2008 ACN,
  Osun 2010 ACN, Ekiti 2010 ACN, Ondo 2009 LP, Imo 2019-court APC.
  INEC-plurality winners never sworn are NOT counted (Zamfara 2019 APC
  voided → PDP; Bayelsa 2019 APC disqualified → PDP).
- **2015 Kogi:** Audu (APC) won the vote but died before declaration; Bello
  (APC) substituted and declared — one APC event either way.

## Sources

Per-state governor lists + per-cycle election pages (English Wikipedia),
Channels TV (Kebbi 2012 rerun), INEC declaration (Zamfara 2019), BBC/Sahara
(Rivers 2007), sokotostate.gov.ng (Sokoto 2008). Full URLs held in the
research record; spot-checks: 1999/2003 Jigawa election pages (APP vs ANPP),
2011 Borno election page (ANPP, not APC), 2015 Kwara/Nasarawa/Oyo pages
(APC as-won vs list lump), 2019 Sokoto/Zamfara pages.
