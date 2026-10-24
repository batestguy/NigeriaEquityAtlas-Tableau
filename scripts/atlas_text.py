"""Plain-language reader text for the atlas: what the words mean, and how it was made.

One source for both outputs: stage 7 (interactive map) renders it as two page
sections, stage 6 (Tableau workbook) as two text dashboards. Edit the words here,
never in the generated files.

Rules every line must follow (docs/CLAIMS.md, docs/CAUSAL_DECISION.md):
- everyday words first; the technical name in brackets after, if at all;
- no cause-and-effect claims; "poorest states vs the rest", never north vs south;
- no single "poorest state" (ranges overlap), no comparison with other countries;
- every figure must trace to a file in this repo or to a cited source below.

Sources for the poverty definitions:
- Indicator cut-offs and weights: OPHI, "What is the global MPI?",
  https://ophi.org.uk/what-global-mpi
- Poor at 33.33%+, vulnerable 20-33.33%, severe 50%+: OPHI global MPI country
  briefings, e.g. https://ophi.org.uk/media/45990/download
- Nutrition missing for Nigeria, child mortality re-weighted to a full third:
  UNDP/OPHI subnational table (data/raw/undp_subnational_results_mpi.xlsx) and
  docs/CLAIMS.md section 1.
- Nigeria 2021 figures (MPI 0.175, 33.0% poor, 52.9% intensity): docs/CLAIMS.md.
"""

from __future__ import annotations

from typing import TypedDict


class Term(TypedDict):
    term: str
    formula: str
    meaning: str
    method: str


class Indicator(TypedDict):
    area: str
    need: str
    weight: str
    missing_if: str


class Section(TypedDict):
    heading: str
    paragraphs: list[str]


class TableRow(TypedDict):
    """One row of the merged reference tab: a word, its formula, its meaning, its making."""

    word: str
    formula: str
    meaning: str
    method: str


# The overview dashboard (stage 6): the one page that shows four sheets at once.
# Title and subtitle live here for the same reason every other page's do -- so a
# single constant drives both the workbook and anything that prints the page
# (the dashboard title run, and docs). The framing is the project's own (D6,
# docs/SESSION_HANDOFF.md): "one country, two realities", never "two zones".
OVERVIEW_TITLE = "Nigeria MPI Equity Atlas"
OVERVIEW_SUBTITLE = "one country, two realities \u00b7 2021"
WORDS_TITLE = "What the words mean"
WORDS_INTRO = (
    "Poverty here means missing basic needs, not low income. What each word on "
    "the map means."
)

# Every entry carries four things, because the reference tab is one table and not two
# pages of prose: the word, its formula or rule (the column a reader scans first), the
# plain-language meaning, and how it was made -- the source, the computation and the
# caveat that would otherwise go unread. `meaning` is the sentence the old glossary
# carried; `formula` and `method` are what the tabular form adds.
TERMS: list[Term] = [
    {"term": "Poor",
     "formula": "a household is poor at 33.3% or more of the weighted list",
     "meaning": "A person counts as poor if their household is missing at least one third "
                "of the weighted list of basic needs below. Everyone in a household gets "
                "the same result.",
     "method": "OPHI's global rule. Because everyone in a household shares the result, a "
               "state's figure is a share of people, not of households."},
    {"term": "Missing a need (deprived)",
     "formula": "one item off the list, for example no electricity",
     "meaning": "The household lacks one item on the list, for example it has no "
                "electricity, or nobody old enough has finished six years of school.",
     "method": "Nine items in three areas. The list, each item's weight and what counts "
               "as missing are in the next section of this table."},
    {"term": "Deprivation score",
     "formula": "0% (nothing missing) to 100% (everything missing)",
     "meaning": "How much of the weighted list a household is missing, from 0% (nothing "
                "missing) to 100% (everything missing). 33.3% or more means poor.",
     "method": "Summed for each household from its survey answers. 33.3% is the line. The "
               "map's hover shows the state's average score among poor people under a "
               "different name (intensity)."},
    {"term": "Close to poverty (vulnerable)",
     "formula": "20% to 33.3% of the list",
     "meaning": "Missing between 20% and 33.3% of the list. Not counted as poor, but near "
                "the line.",
     "method": "OPHI's cut-off, carried through the pipeline as vulnerable_pct. It is not "
               "shown on the map."},
    {"term": "Severe poverty",
     "formula": "50% or more of the list",
     "meaning": "Missing 50% or more of the list.",
     "method": "OPHI's cut-off, carried through the pipeline as severe_pct. It is not "
               "shown on the map."},
    {"term": "Share of people who are poor (H)",
     "formula": "H = poor people \u00f7 all people",
     "meaning": "Out of every 100 people, how many count as poor. Nigeria in 2021: "
                "33.0%, about 1 in 3.",
     "method": "Published for each state by OPHI and UNDP. We use their figure as "
               "published and do not recalculate it. This is the headcount, and it is not "
               "the number the map's colour carries."},
    {"term": "How much poor people miss (A)",
     "formula": "A = the average score of the people who are poor",
     "meaning": "Among poor people only, the average deprivation score. Nigeria in 2021: "
                "52.9%, so a typical poor person was missing about half of the list.",
     "method": "Same source as H, published separately from it. The map's hover calls it "
               "the average deprivation among them."},
    {"term": "Poverty score (MPI)",
     "formula": "MPI = H \u00d7 A",
     "meaning": "The share of people who are poor multiplied by how much they miss "
                "(H \u00d7 A). It runs from 0 (nobody poor) to 1 (everybody poor and missing "
                "everything). Nigeria's global MPI in 2021 (MICS 2021 survey): "
                "0.330 \u00d7 0.529 = 0.175.",
     "method": "Our state figures are OPHI's harmonised series (Data Table 6, MN 63), "
               "checked numerically against Table 6.4 to 4 decimal places on all 148 "
               "admin-1 rows and against UNDP's published state figures. Earlier OPHI "
               "publications of the same years used un-harmonised estimates and differ by "
               "up to 0.17, so never compare these with an older release."},
    {"term": "Likely range",
     "formula": "the 95% confidence interval (the statisticians' term for it)",
     "meaning": "Surveys talk to a sample of households, not everyone, so every figure "
                "has some uncertainty. The likely range is where the true value probably "
                "lies (statisticians call it a 95% confidence interval). When two states' "
                "ranges overlap, we cannot be sure which one is poorer.",
     "method": "OPHI's design-based standard errors, published in the same UNDP workbook "
               "(table 5.4) and extracted to data/interim/mpi_se_ci.csv. The median "
               "relative standard error is 15%, and all 36 pairs of states adjacent in "
               "the ranking overlap at 95% -- which is why this atlas shows bands and "
               "never names a poorest state."},
    {"term": "Poverty band",
     "formula": "under 5% \u00b7 5\u201310% \u00b7 10\u201320% \u00b7 20\u201330% \u00b7 30% and above",
     "meaning": "One of the five colour groups on the map: under 5%, 5%\u201310%, "
                "10%\u201320%, 20%\u201330%, and 30% or more. The score is a 0-to-1 index, so "
                "these read as percentages of the index, not as the share of people "
                "who are poor (that share is shown separately and is much higher). The "
                "map uses bands rather than a 1-to-37 ranking because the likely "
                "ranges of states next to each other in the ranking overlap.",
     "method": "Cut from the MPI value, not from H. The five colours are the map's fill, "
               "and the band is the only place this atlas puts states in order."},
    {"term": "Poorest 12 and Other 25",
     "formula": "MPI above 0.20 \u2014 12 states",
     "meaning": "The 12 states with a poverty score above 0.20, and the remaining 25 "
                "(including FCT).",
     "method": "Written into the extract by stage 4 and used in the map's hover. It is "
               "also one of the robustness re-tests of the party question."},
    {"term": "Area of life (dimension)",
     "formula": "health + education + living standards, one third each",
     "meaning": "The list is grouped into three areas: health, education and living "
                "standards. Each area counts for one third.",
     "method": "OPHI's three dimensions. In Nigeria health rests on child deaths alone "
               "and takes the whole third, which is why cross-country comparison is not "
               "available (see the next section)."},
    {"term": "Share from each area (contribution)",
     "formula": "the three shares add to 100%",
     "meaning": "How much of a state's poverty score comes from health, from education "
                "and from living standards. The three add up to 100%.",
     "method": "Published for each state by OPHI, carried as contrib_health_pct, "
               "contrib_education_pct and contrib_living_standards_pct. Among the "
               "poorest 12 states the education share is about 40%, against 22% "
               "elsewhere."},
    {"term": "Survey round",
     "formula": "2013 DHS \u00b7 2016\u201317 MICS \u00b7 2018 DHS \u00b7 2021 MICS",
     "meaning": "One of the four large national household surveys used: 2013 (DHS), "
                "2016\u201317 (MICS), 2018 (DHS) and 2021 (MICS). DHS is the Demographic and "
                "Health Survey; MICS is the Multiple Indicator Cluster Survey. The map "
                "shows 2021.",
     "method": "Four rounds, taken from OPHI's published tables. The map shows 2021 only; "
               "the other three appear in the comparable-over-time series."},
    {"term": "Comparable over time (harmonised)",
     "formula": "one definition applied to all four rounds",
     "meaning": "A version of the four rounds prepared by Oxford University's poverty "
                "team (OPHI) so that changes between rounds can be compared fairly.",
     "method": "The harmonised series is the one this pipeline downloads and the one it "
               "verified against OPHI's own Table 6.4. Between rounds, states kept their "
               "positions relative to each other (rank persistence 0.87\u20130.92) even where "
               "levels fell."},
    {"term": "Conflict exposure (0\u2013100)",
     "formula": "events and deaths per 100,000 people, rescaled 0\u2013100 within each year",
     "meaning": "How many recorded violent events and deaths a state had per 100,000 "
                "people in a survey year, compared with the other states that same year. "
                "100 is the most of the 37 that year and 0 the fewest. It is relative, so "
                "50 in 2013 and 50 in 2021 are not the same amount.",
     "method": "UCDP GED 24.1 (CC BY-IGO), attributed to a state by the coordinates of "
               "each event, with the method recorded per event. Scaled within year by "
               "min-max; the anchors are in data/processed/atlas_vintages.csv. Borno "
               "takes 100 in 2021 and the other 36 states cluster near zero."},
    {"term": "Recorded conflict event",
     "formula": "one incident, at least one reported death",
     "meaning": "An incident of organised violence in which at least one person is reported "
                "to have died, "
                "logged by the Uppsala Conflict Data Program from news and other reports. "
                "Violence that is never reported is missed.",
     "method": "UCDP GED 24.1. In 2021, 10 of the 37 states recorded no event at all, "
               "including five of the poorest 12 (Bauchi, Jigawa, Kebbi, Katsina and "
               "Kano), so the variable undercounts most where poverty is highest."},
    {"term": "Climate baseline",
     "formula": "mean of 1991\u20132020, at the state capital",
     "meaning": "A state capital's average yearly temperature and rainfall over "
                "1991\u20132020.",
     "method": "Open-Meteo daily archive, 1990\u20132024, for the 37 capitals (GeoNames). Days "
               "with missing records are excluded and each state's contributing-day count "
               "is checked before use."},
    {"term": "Governor from the President's party",
     "formula": "PDP until 29 May 2015, APC after that",
     "meaning": "The state governor belonged to the same party as the President: the "
                "PDP (People's Democratic Party) until 29 May 2015, the APC (All "
                "Progressives Congress) after that.",
     "method": "From a sourced event table of every seating and every defection "
               "(data/reference/governorship_events.csv and governor_defections.csv), "
               "which stage 0 checks recomputes the state labels. Hover context only: "
               "party is never a colour anywhere in this atlas."},
    {"term": "Party that won most often",
     "formula": "the mode of the 1999\u20132021 elections",
     "meaning": "The party that won the most governorship elections in the state from "
                "1999 to 2021. Ties are shown. It appears in the map's hover text only.",
     "method": "Six states are ties and the FCT has no governor. 26 of the 36 states with "
               "a governor are PDP, so this label cannot test anything; the question that "
               "can is in the last section of this table."},
    {"term": "FCT",
     "formula": "no elected governor",
     "meaning": "The Federal Capital Territory (Abuja). It is shown like a state, but it "
                "has no elected governor, so it is left out of the party question.",
     "method": "Kept in every aggregate as if it were a state, because it is the most "
               "poverty-dense unit and dropping it is a classic silent error. Its "
               "exclusion from the party question is why that test has 108 "
               "state-intervals from 36 states."},
    {"term": "Neighbouring states",
     "formula": "two states that share a border on the map",
     "meaning": "Two states that share a border on the map. Nothing more is meant by it: "
                "it is a fact about the map, not about people or traffic moving between "
                "the states.",
     "method": "Queen contiguity, computed from the ADM1 boundaries in the same pipeline "
               "stage. Queen and rook give the same answer here, and the conclusion "
               "survives four nearest neighbours instead of shared borders and survives "
               "dropping the FCT."},
    {"term": "States that resemble each other (clustering)",
     "formula": "Moran's I",
     "meaning": "When states that share a border tend to have similar poverty scores, "
                "more often than if the scores were scattered about at random. It "
                "describes the pattern on the map. It does not say that one state's "
                "poverty makes its neighbour poorer.",
     "method": "A pre-registered test, frozen in docs/spatial_preregistration.md before "
               "the code existed. Moran's I is 0.80 (p \u2264 0.0001), but 0.24 once latitude "
               "is taken out, and 0.11 once latitude, conflict and climate are. The full "
               "numbers are in docs/spatial_analysis.md."},
    {"term": "Explained by how far north a state is",
     "formula": "latitude against MPI, R\u00b2 = 0.77",
     "meaning": "Because poverty rises steadily from south to north, a lot of states "
                "looking like their neighbours is just that steady slope. Once the slope "
                "is taken out, we can see how much resemblance is left over and above "
                "it.",
     "method": "How far north a state sits correlates with its MPI at +0.82, which is "
               "closer than rainfall does it (0.80). The atlas uses OPHI's word for it "
               "\u2014 overlap \u2014 and does not call climate a driver."},
]

INDICATORS_TITLE = "The list of basic needs"
INDICATORS_INTRO = (
    "Each item has a weight; a household's score is the sum of the weights it "
    "is missing."
)

INDICATORS: list[Indicator] = [
    {"area": "Health", "need": "Child deaths", "weight": "1/3 (33.3%)",
     "missing_if": "A child under 18 in the household died in the five years before the "
                   "survey."},
    {"area": "Education", "need": "Years of school", "weight": "1/6 (16.7%)",
     "missing_if": "Nobody in the household who is old enough to have done so has finished "
                   "six years of school (primary school)."},
    {"area": "Education", "need": "Children in school", "weight": "1/6 (16.7%)",
     "missing_if": "A school-age child is not attending school, up to the age they would "
                   "finish class 8."},
    {"area": "Living standards", "need": "Cooking fuel", "weight": "1/18 (5.6%)",
     "missing_if": "The household cooks with wood, charcoal, coal, dung, crop waste or "
                   "shrubs."},
    {"area": "Living standards", "need": "Toilet", "weight": "1/18 (5.6%)",
     "missing_if": "No toilet, a toilet that does not safely separate waste, or a toilet "
                   "that is safe but shared with other households."},
    {"area": "Living standards", "need": "Drinking water", "weight": "1/18 (5.6%)",
     "missing_if": "The water source is not safe, or safe water is a 30-minute or longer "
                   "walk there and back."},
    {"area": "Living standards", "need": "Electricity", "weight": "1/18 (5.6%)",
     "missing_if": "No electricity."},
    {"area": "Living standards", "need": "Housing", "weight": "1/18 (5.6%)",
     "missing_if": "The floor, roof or walls are made of inadequate materials."},
    {"area": "Living standards", "need": "Belongings", "weight": "1/18 (5.6%)",
     "missing_if": "Owns no more than one of: radio, TV, phone, computer, animal cart, "
                   "bicycle, motorbike, fridge, and has no car or truck."},
]

INDICATORS_NOTE = (
    "Why health is a single item: the global measure normally splits health between "
    "child deaths and nutrition, but nutrition could not be included in Nigeria's "
    "published figures, so "
    "child deaths carry the whole health third. This is the same for every state, so "
    "comparing states within Nigeria is fair. It also means Nigeria's figures should "
    "not be compared with other countries'."
)

EXAMPLE_TITLE = "An example household"
EXAMPLE_LINES: list[tuple[str, str]] = [
    ("Nobody old enough has finished six years of school", "16.7%"),
    ("Cooks with wood", "5.6%"),
    ("No electricity", "5.6%"),
    ("Safe water is a 30-minute walk there and back", "5.6%"),
    ("Shares its toilet with other households", "5.6%"),
]
EXAMPLE_TOTAL = "38.9%"
EXAMPLE_VERDICT = (
    "38.9% is above the 33.3% line, so everyone in this household counts as poor. "
    "Because child deaths carry a full third in Nigeria, a household that lost a child "
    "in the past five years reaches the line from that one item alone. Percentages are "
    "rounded; the exact sum is 3/18 + 4/18 = 7/18. (An illustration, not a real "
    "household.)"
)

METHOD_TITLE = "How we did it"
MPI_LEGEND_TITLE = "MPI band"
# The acronym expanded, and what the index itself means. Used wherever a legend
# renders: the Tableau colour card (its title is the colour field's caption,
# which cannot be italic), the Plotly colour-bar title, the narrow-screen HTML
# legend (both italic there) and the tooltip's italic MPI line. The glossary's
# own MPI entry stays the long-form source of truth.
MPI_LEGEND_EXPANSION = "Multidimensional Poverty Index"
MPI_LEGEND_MEANING = (
    "the share of people who are poor multiplied by how deprived they are on "
    "average, as a percentage of the index"
)
# The poverty map's one-line statement of what the figure IS (2026-10-24 word
# budget). Sourced once so the sheet and the stage-5 gate print the same words:
# the gate used to carry its own longer sentence, which is exactly how a subtitle
# drifts. Meaning first ("how poor each state is"), then the encoding, then the
# one caveat the map cannot drop (bands, not ranks -- all 36 adjacent state
# intervals overlap at 95%, docs/CLAIMS.md). Hover guidance moved to the legend
# title, which already expands MPI, and to the tooltip itself.
MPI_MAP_SUBTITLE = (
    "How poor each state is, 2021 \u00b7 darker red = poorer "
    "\u00b7 5 bands, not 37 ranks"
)

# The five MPI bands in the order they run, each with the colour it draws.
# One list, three surfaces: stage 6 writes it into the workbook (a discrete field
# given a palette -- the grammar lives inside the <datasource>, between <layout/>
# and <semantic-values>), stage 5 draws the matplotlib QA gate from it, and the
# workbook's colour legend reads it back. Two surfaces that colour the same field
# differently would read as two different findings.
#
# A single-hue red ramp, pale at the low end and a bright red at the high end,
# stepping up in saturation so the band order is legible from the colour alone.
# It replaced the ColorBrewer YlOrBr ramp on 2026-10-18 at the user's direction
# ("bright red to light red"). The red is the *high* end of the scale: band 5,
# the poorest states, is the bright red, and the least poor are nearly white --
# the ramp's light end, where a reader's eye already expects "little of this".
# Colour-vision note: this ramp is one hue, so it carries no red/green contrast
# to lose; the ordering survives deuteranopia and protanopia through lightness
# alone, which is the channel every band is separated on.
#
# The leading "N. " in each label is a sort key (the Tableau legend sorts
# alphabetically), not part of what the reader is meant to read -- stage 5
# strips it for its own legend.
MPI_BANDS: list[tuple[str, str]] = [
    ("1. under 5%", "#ffe5e5"),
    ("2. 5% to 10%", "#ffb8b8"),
    ("3. 10% to 20%", "#ff8a8a"),
    ("4. 20% to 30%", "#f45555"),
    ("5. 30% and above", "#d80000"),
]
# --- The spatial sheet: do poor states sit next to poor states? ---------------
# A diagnostic on sheet 1's map, not a second poverty map. Every word here is
# written for a reader who does not know any statistics: the statistic is named
# once, in the small technical line, and never in a headline. The wording of the
# four reading lines is frozen in docs/spatial_preregistration.md, which was
# committed before the analysis code existed; 09_spatial_diagnostics.py asserts
# that the figures these words state are still the figures in the data.
# The cluster map: sheet 1's own geometry, drawn a second time with the
# neighbourhood type as the fill. It is the map form of the question the Moran
# scatter used to draw as a two-axis plot (withdrawn 2026-10-18, docs/FIX_LEDGER.md
# W1), and it sits immediately after the poverty map in the tab order. The colours are descriptive and are never a significance map: only one
# state survives the correction (SPATIAL_READER_LINES line 4), so a map of what is
# statistically significant would be a single state and would re-import the
# per-state ordering the atlas withdrew (docs/FIX_LEDGER.md A1).
SPATIAL_MAP_TITLE = "Where poverty clusters"
SPATIAL_MAP_SUBTITLE = (
    "Poverty beside the neighbours' \u00b7 a grouping, not a significance test"
)
SPATIAL_MAP_READING = (
    "The colour says two things at once. Grey is the poor block: this state is poorer "
    "than the average state, and so are the states it borders. Deep teal is the mirror "
    "image \u2014 better off than average, among better-off neighbours. Purple marks a "
    "state that does not fit its surroundings: poorer than average, with neighbours "
    "that are not. Read it as a description of where poverty sits, not as a list of "
    "places that stand out: the lines below give the one number that says how much of "
    "this is more than the north being poorer than the south."
)
SPATIAL_FIELD_OWN = "This state's poverty score (MPI, % of index)"
SPATIAL_FIELD_NEIGHBOURS = "Average poverty score of the states it borders (MPI, % of index)"
SPATIAL_LEGEND_TITLE = "Neighbourhood type"
# The caption is the legend's title text and the field's name in the data pane, so it
# has to say what is being compared, in words a reader can act on: a state against
# the states it borders. "Neighbourhood" alone invites a reading about people moving.
SPATIAL_LEGEND_MEANING = "this state's poverty, beside the states it borders'"
SPATIAL_READING_HEADING = "The reading, in plain words"
# The caveat that has to survive on the surface, because "neighbourhood type" is
# vocabulary that invites a spillover reading.
SPATIAL_NO_CAUSE = (
    "Nothing here shows that one state's poverty affects its neighbour's \u2014 "
    "neighbours resembling each other is a fact about the map."
)

# The four lines, in order. Frozen wording (docs/spatial_preregistration.md).
# They are static, and stage 09 fails if the data stops matching them, so the
# words and the numbers cannot drift apart silently.
SPATIAL_READER_LINES: list[str] = [
    "Yes. States with similar poverty scores do tend to share a border.",
    "But most of that is simply that the north is poorer than the south: how far "
    "north a state sits explains about three quarters of what looks like neighbouring "
    "states resembling each other.",
    "Think of a height map. Two neighbours are usually at similar heights because the "
    "land slopes steadily \u2014 not because one hill lifts the next. Take the slope "
    "out, and only a little resemblance between neighbours is left.",
    "Only 1 of the 37 states stands out on its own, once we allow for having looked at "
    "37 states at once.",
]

# The four neighbourhood types: (code, words for the reader, colour).
# The words name both ingredients, because that is what the classification is: a
# comparative ("poorer than average") and whether the states it borders agree. They
# are deliberately not "poor states" -- above-average is not the atlas's "poorest 12"
# (MPI above 0.20), and a legend that read "poor" would blur the two thresholds.
#
# The colours changed on 2026-10-18 at the user's direction: the poor-beside-poor
# block is now grey (it is the largest block, and grey recedes), and the state that
# does not fit its surroundings -- poorer than average among better-off neighbours --
# took the purple that block used to hold, so the one-off carries. Teal still marks
# better-off states: pale where the neighbours disagree, deep where they agree. The
# fourth pairing, better off beside poorer neighbours, does not occur in this data;
# its colour is only ever a legend entry.
# Deliberately not the poverty ramp, so the sheet cannot be read as a second poverty
# map. Nominal fields otherwise draw in Tableau's default categorical palette.
SPATIAL_QUADRANTS: list[tuple[str, str, str]] = [
    ("HH", "Poorer than average, neighbours poorer too", "#969696"),
    ("HL", "Poorer than average, neighbours better off", "#54278f"),
    ("LH", "Better off than average, neighbours poorer", "#80cdc1"),
    ("LL", "Better off than average, neighbours better off", "#01665e"),
]

# The fills that take white state labels. A property of the hexes above, not of the
# data: white over the purple and the deep teal, ink over the grey and the pale teal,
# in the stage 5 preview. Mid grey takes ink -- white on #969696 sits at about 2.8:1.
SPATIAL_DEEP_TYPES: list[str] = [
    "Poorer than average, neighbours better off",
    "Better off than average, neighbours better off",
]

# --- The time panel: watch one state's measures across the four rounds ---------
# docs/SHEET_TIME_PANEL.md is the design freeze (amended 2026-10-21: the marks draw
# RANKS, not values). The list is a whitelist, one row per measure the sheet
# (workbook) and the pre-Tableau gate (stage 5) both draw: (column, caption,
# colour). The caption is what the workbook's field is called everywhere -- row
# header, colour legend entry, checklist item and tooltip field -- so each one
# names its measure.
#
# The columns are the panel CSV's rank fields (04_merge.py RANK_FIELDS): the
# state's position on that measure among the 37 states, in that round, with
# R1 = the measure's highest value (poorest MPI, most conflict, hottest capital)
# and ties sharing the better rank. The raw values stay in the CSV; the sheet's
# visible number is the rank. That is the rank-persistence finding made visible
# for one state -- and it is NOT an ordering claim: OPHI's published SEs leave
# every adjacent pair overlapping at 95%, which is printed on the sheet itself
# (PANEL_SUBTITLE below), so the sheet carries its own limit.
#
# Deliberately absent, per the freeze: `conflict_exposure_index` (its 0 and 100 are
# re-anchored within each survey round, so a line over time of it charts the
# re-anchoring, not violence), `temp_anomaly_c` and `precip_anomaly_pct` (four
# rounds of weather at one city is not a climate signal), and the raw `events` /
# `fatalities` counts (scale-dominated by population; the per-100k pair carries the
# defensible form). 06_build_twb.py refuses a schema that contains them -- the
# exclusion is asserted, not remembered. Since 2026-10-21 that refusal extends to
# every raw value column: the extract carries the ranks and the STRING hover
# annotations only (mpi_change_label / deaths_high_label, pre-formatted by
# 04_merge.py), so the Measure Names domain is ranks alone.
#
# The colours are six unrelated hues -- different measures, not an ordered scale;
# unlike MPI_BANDS the order of this list carries no meaning. The word "surveys"
# in captions: the four rounds are DHS and MICS harmonised by OPHI (Data Table 6,
# MN 63), so within-panel comparison holds. 2026-10-24 word budget: the headers
# read "<measure> . rank" and the direction key is stated ONCE in the subtitle
# ("1 = highest"), because repeating "(1 = highest)" in six row headers was six
# copies of the same three words on the row-header rail.
PANEL_MEASURES: list[tuple[str, str, str]] = [
    ("rank_mpi", "MPI \u00b7 rank", "#d62728"),
    ("rank_headcount", "H % poor \u00b7 rank", "#1f77b4"),
    ("rank_intensity", "Intensity A \u00b7 rank", "#ff7f0e"),
    ("rank_events", "Conflict events/100k \u00b7 rank", "#2ca02c"),
    ("rank_deaths", "Conflict deaths/100k \u00b7 rank", "#9467bd"),
    ("rank_temp", "Capital temp \u00b7 rank", "#17becf"),
]
# The key sentence on the sheet: ranks replaced the values on the marks, so the
# direction has to be on the canvas. Wording stays inside docs/CLAIMS.md's rules:
# it describes what the label IS (position on the published point estimate) and
# what it is NOT (a separation claim between states).
PANEL_SUBTITLE = (
    "One state's rank of 37 on six measures, four rounds \u00b7 1 = highest "
    "\u00b7 stars = significant change \u00b7 ranks overlap at 95%, so no trend"
)
# The state the sheet opens on: the hover example everywhere else in the atlas, so
# the sheet never loads blank. Asserted to exist in the panel before the workbook
# is built (stage 6) and before the gate draws (stage 5).
PANEL_DEFAULT_STATE = "Bauchi"

# ---------------------------------------------------------------------------
# "How measures pair" -- the bivariate exploration board (docs/SHEET_PAIRS.md,
# frozen 2026-10-21 before build; the two selectors are Tableau parameters whose
# grammar was proven in packets A1-A6, docs/FIX_LEDGER.md section P).
#
# This sheet exists to LOOK, not to claim. It draws any two continuous measures
# as one point per state-round, split into the two 2021 poverty-group panes.
# What it must never do is compute: no fit, no per-pane slope, no correlation,
# no size channel; the panes cut on the outcome itself, so anything computed
# within them is range-restricted arithmetic, not evidence. The subtitle and the
# hover caveat both say it; the guardlist is in the freeze doc ("may not say").
PAIRS_TITLE = "How measures pair"
PAIRS_SUBTITLE = (
    "Any two measures, one point per state-round \u00b7 panes split on the "
    "poorest 12: compare within a pane \u00b7 the line describes its pane only "
    "\u00b7 logged axes, 0 = none \u00b7 points, not a test"
)
# The board's circle fill: the atlas's Okabe-Ito green (the same green the
# living-standards share prints), single-sourced so the two sheets agree.
PAIRS_POINT_COLOUR = "#009E73"
# The trend line's paint (2026-10-24). Asked for as white; white on this sheet's
# white pane is invisible -- verified by render, not assumed: built with
# stroke-color='#FFFFFF', the line and both CI band edges vanished from the pane
# while every mark and gridline stayed, and painting it '#4D4D4D' brought them
# back (docs/SHEET_PAIRS.md "Trend line"). The shipped value is a neutral dark
# ink: it reads as an overlay the marks sit on top of, not as a second series,
# and it cannot be confused with the green fill. Going white is this one hex.
PAIRS_TREND_COLOUR = "#4D4D4D"
# The hover caveat was withdrawn with the hover simplification (2026-10-22):
# the tooltip prints the state name alone, and the caveat sentences live where
# a reader actually sees them -- in the subtitle. (Was: PAIRS_TOOLTIP_CAVEAT.)

# ---------------------------------------------------------------------------
# "How poverty is made up" -- the three-area decomposition sheet
# (docs/SHEET_DIMENSIONS.md, frozen 2026-10-22 before build).
#
# The one claim this sheet makes is the atlas's strongest: the dimension
# CONTRAST, never a per-state ranking. "Lagos is 70% health-driven; Bauchi 15%"
# is a 55-point spread that survives sampling noise (docs/CLAIMS.md section 2,
# "Dimension contrast"), and the 17.6-point education-share gap between the
# poorest 12 and the rest (p = 1e-5) is the headline finding the atlas leads
# with. What the sheet must never do is name a state as worst: the bars are
# ordered by each state's MPI, but all 36 adjacent pairs of those MPI values
# overlap at 95%, so the subtitle and the hover both say read the partition,
# not the order. (The orderings the atlas withdrew in docs/FIX_LEDGER.md A1
# were naming claims; the same withdrawal is why the map bands instead of
# ranking, and the wording rule is identical here.)
#
# The shares are an IDENTITY, not an inference: MPI decomposes exactly into the
# three dimension contributions, so every bar sums to 100 (stage 4 asserts it,
# stage 6 re-asserts it against the same rows). No standard error is published
# for the shares and none is needed for an identity -- the CAUTION is that a
# share of a tiny MPI is a share of very little (Abia's 57.7% health describes
# 0.002 of index weight), which is what the hover's MPI line is for.
#
# The colours are three colourblind-safe hues (Okabe-Ito blue / orange / green),
# deliberately absent from the map palettes -- the maps' ramps mean geography
# and poverty level, this palette means the three areas and nothing else. It is
# read by this sheet's workbook palette and by the stage-5 QA gate from this one
# list, the single-source rule MPI_BANDS and SPATIAL_QUADRANTS already follow.
# The list order was the freeze's stacking intent, Education first from the
# axis -- what Tableau actually does with it is recorded in
# docs/SHEET_DIMENSIONS.md ("Built"): 2026.2 stacks the LAST listed measure
# nearest the axis, so the first render showed Living standards, Health,
# Education left-to-right. The gate stacks the same way (reversed off this
# list); the colours bind by measure key, so no surface can disagree about
# which colour is which area.
DIMENSIONS_TITLE = "How poverty is made up"
DIMENSIONS_SUBTITLE = (
    "What each state's poverty is made of \u00b7 shares of the MPI, adding to "
    "100 \u00b7 MPI order, not a ranking \u00b7 17 of 37 bars: the left card "
    "adds the rest"
)
DIMENSION_SHARES: list[tuple[str, str, str]] = [
    ("contrib_education_pct", "Education", "#0072B2"),
    ("contrib_health_pct", "Health", "#E69F00"),
    ("contrib_living_standards_pct", "Living standards", "#009E73"),
]
# The hover line and the italic caveat, single-sourced like every other surface.
DIMENSION_HOVER_PREFIX = "of the state's MPI: "
# The poverty-group labels: what stage 4 stamps into `poverty_group` (rank
# i <= 12 → "Poorest 12", else "Other 25"). Sourced here so the composition
# sheet's header labels and its manual sort dictionary cannot drift from the
# data values.
POVERTY_GROUP_TOP = "Poorest 12"
POVERTY_GROUP_REST = "Other 25"

# ---------------------------------------------------------------------------
# "Where Nigeria stands" -- the KPI board against WHO / SDG reference standards
# (docs/SHEET_KPI.md, frozen 2026-10-23). National-level only: it compares
# Nigeria with published 2021 international reference values, so it touches no
# state-level claim (documented in docs/kpi_benchmarks.md and stage 7, which
# fetches the values and asserts them against OPHI's national row).
#
# What the sheet is allowed to say is proportionate ("Nigeria sits this far from
# the standard") and never causal; what it must NOT do, and what the freeze doc
# pins, is compare Nigeria's Health *dimension share* with other countries
# (structurally heavier: child mortality alone -- docs/CAUSAL_DECISION.md).
# The raw under-5 mortality indicator against WHO standards is the comparison
# that is available. The "world" line for the headcount is UNDP/OPHI's total
# across 109 developing countries, and every surface must carry that caveat.
KPI_TITLE = "Where Nigeria stands"
KPI_SUBTITLE = (
    "How Nigeria compares with Africa, the world and the SDG target, 2021 "
    "\u00b7 each row is its own scale \u00b7 \u25bc lower is better, \u25b2 "
    "higher is better"
)
# One shape mark per reference point, three members, the shapes ARE the
# series identity (a map of Nigeria / Africa / the world -- KPI_SHAPE_FILES
# below). Members other than Nigeria carried greys (receding reference points)
# until the 2026-10-23 render pass, whose user pass pinned the three
# identification hues explicitly: Nigeria green, sub-Saharan Africa the
# Tableau categorical blue, world the Tableau categorical orange on a globe.
# The next pass on the same day went further: the world's globe draws in
# purple with white coastlines and a lat/long grid, so it reads as a globe
# rather than a flat map cut into a disc.
# 2026-10-24 pass: the world went from that purple to OKABE-ITO AMBER
# (#E69F00) and the globe lost its coastlines, keeping its vertical meridians
# only. The reasoning, because this is a colour question the user asked
# outright: the two hues the board already spends are a GREEN landmass (one
# country) and a BLUE one (one continent), so the third mark cannot be blue or
# green without colliding with them; amber is the one hue that stays clear of
# both for a colour-blind reader as well (Okabe-Ito pairs it with #009E73), and
# it is the project's existing Okabe-Ito family (the composition sheet's
# Education share is the same hex). On a disc with vertical meridians it reads
# as sand/land under a graticule -- "the planet" -- rather than as a fourth
# brand colour. Purple is the one-hex revert if the amber reads wrong.
# Colours are single-sourced so the workbook's palette block and the stage-5
# QA gate cannot drift apart, like MPI_BANDS and SPATIAL_QUADRANTS before it.
KPI_SERIES: list[tuple[str, str]] = [
    ("Nigeria (2021)", "#009E73"),
    ("sub-Saharan Africa (2021)", "#4E79A7"),
    ("World (2021)", "#E69F00"),
]
# The marks are map silhouettes (2026-10-23): each member draws as its own
# shape -- a map of Nigeria, a map of Africa, a map of the world -- so the
# reader identifies the reference points by geometry, not by hue. The images
# are stage 7's silhouettes (data/reference/kpi_shapes, drawn from the atlas's
# own ADM1 rings and Natural Earth 110m, transparent PNGs on one square
# canvas); stage 6 embeds them in the workbook's <external><shapes> under the
# KPI_Geo palette and maps them member-by-member, and the stage-5 gate pastes
# the same files at the same positions. Keyed by member, so the three surfaces
# cannot disagree on which image belongs to which series.
KPI_SHAPE_FILES: dict[str, str] = {
    "Nigeria (2021)": "nigeria.png",
    "sub-Saharan Africa (2021)": "africa.png",
    "World (2021)": "world.png",
}
# Row labels: what the sheet's row header prints. Keyed to the kpi names the
# benchmarks CSV carries (stage 7), with the unit written out, because a bare
# "117.6" means nothing without it and the axis numbers are abstract shares.
#
# The trailing glyph is the per-row direction arrow (2026-10-24 user pass: "an
# arrow indicating if high values are good or bad, per row"). It rides the ROW
# HEADER TEXT -- a data value, so the manual sort dictionary still matches and
# no new encoding, column or mark is needed. Nothing per MARK is flagged: the
# guardlist (docs/SHEET_KPI.md) forbids a good/bad badge on a data point, and
# the arrow describes the row's reading, not the value's quality. The glyph is
# derived from KPI_DIRECTION_ARROW below, and stage 7 ASSERTS it against the
# benchmarks CSV's `direction` column, so the arrows cannot drift from the data.
#
# Length matters: the header column is 230 px (stage 6 sets it) and a longer
# label wraps to a second and third line, which eats the board's vertical room.
# 2026-10-24 shortened four labels for exactly that reason ("Child deaths under
# 5 (per 1,000 births)" -> "Under-5 deaths per 1,000 births", "At least basic
# drinking water (% of people)" -> "Basic drinking water (% of people)",
# "Access to electricity" -> "Electricity access", "Safely managed sanitation
# (% of people)" -> "... (%)"), the same units, fewer words.
KPI_ROW_LABELS: dict[str, str] = {
    "Multidimensional poverty headcount (national)":
        "Poverty headcount (% of people) \u25bc",
    "Under-five mortality rate": "Under-5 deaths per 1,000 births \u25bc",
    "Open defecation": "Open defecation (% of people) \u25bc",
    "Safely managed sanitation": "Safely managed sanitation (%) \u25b2",
    "At least basic drinking water": "Basic drinking water (% of people) \u25b2",
    "Access to electricity": "Electricity access (% of people) \u25b2",
    "Access to clean cooking fuels and technologies":
        "Clean cooking fuel (% of people) \u25b2",
}
# The two glyphs, keyed to the benchmarks CSV's `direction` values.
KPI_DIRECTION_ARROW: dict[str, str] = {
    "lower_is_better": "\u25bc",
    "higher_is_better": "\u25b2",
}
# Short source names for the hover line, keyed to the WDI code. The full
# provenance (fetch date, licence, exact series) stays in the benchmarks CSV
# and docs/kpi_benchmarks.md; the hover carries the one a reader can act on.
KPI_SOURCE: dict[str, str] = {
    "SI.POV.MPUN": "OPHI / UNDP global MPI",
    "SH.DYN.MORT": "UN IGME",
    "SH.STA.ODFC.ZS": "WHO / UNICEF JMP",
    "SH.STA.SMSS.ZS": "WHO / UNICEF JMP",
    "SH.H2O.BASW.ZS": "WHO / UNICEF JMP",
    "EG.ELC.ACCS.ZS": "SE4All / UN statistics",
    "EG.CFT.ACCS.ZS": "SE4All / UN statistics",
}
# The static second line of the hover: the direction key is on the sheet
# because interpretation flips row by row, and no per-row flag lifts it: the
# reader is told the rule, not a per-mark "good/bad" badge. Trimmed hard in
# the third 2026-10-23 pass ("reduce the amount of words") -- the causal
# disclaimer stays, because docs/CAUSAL_DECISION.md forbids losing it.
KPI_TOOLTIP_NOTE = (
    "\u25bc lower is better \u00b7 \u25b2 higher is better \u00b7 point "
    "estimates \u00b7 other countries' figures, comparison only \u2014 no view "
    "of what makes any row its size."
)

DIMENSIONS_CAVEAT = (
    "Read the split, not the bar order. The bars follow each state's MPI, but "
    "neighbouring states' MPI intervals overlap at 95%, so the order is the "
    "point estimate's, not a finding. Health = child deaths only here (no "
    "nutrition, for any state), so it carries the full one-third."
)
METHOD_INTRO = (
    "Where the numbers come from, how they are combined, how sure we can be, and "
    "what this atlas cannot say."
)

METHOD: list[Section] = [
    {"heading": "1. Where the numbers come from",
     "paragraphs": [
         ("Poverty figures come from large national household surveys (MICS 2021, plus "
         "DHS 2013, MICS 2016–17 and DHS 2018). Oxford University's poverty team (OPHI) "
         "and the UN Development Programme turn the survey answers into state poverty "
         "scores and publish them. We used their published figures as they are and did "
         "not recalculate them."),
         ("Other layers: violent events from the Uppsala Conflict Data Program, weather "
         "records for each state capital from Open-Meteo, state borders from "
         "geoBoundaries, capital locations from GeoNames, and governorship election "
         "results checked against cited sources. Every download is logged with its date."),
         ("Licences, as their publishers state them: the poverty figures are CC0 / CC BY "
         "(OPHI and UNDP); the violent-event data is CC BY-IGO (UCDP); the weather "
         "records are CC BY 4.0 (Open-Meteo); and the state borders and capital "
         "coordinates are CC BY 4.0 (geoBoundaries, GeoNames)."),
     ]},
    {"heading": "2. How a state's poverty score is built",
     "paragraphs": [
         ("Step 1: for each surveyed household, check each of the nine needs on the list. "
         "Step 2: add up the weights of the needs it is missing; that is its deprivation "
         "score. Step 3: if the score is 33.3% or more, everyone in the household counts "
         "as poor. Step 4: for the state, work out the share of people who are poor and "
         "how much they miss on average, then multiply the two to get the poverty score."),
         ("Multiplying the two matters: a state where fewer people are poor, but those "
         "people miss a lot, can score as high as a state where more people are poor but "
         "miss less."),
     ]},
    {"heading": "3. How sure we can be",
     "paragraphs": [
         ("Because the surveys use samples, each state's score has a likely range. For a "
         "typical state the range runs about 30% above and below the score itself. The "
         "ranges of every pair of states that sit next to each other in the ranking "
         "overlap, so the atlas never names a single poorest state. "
         "It shows five bands instead, and the poorest 12 states as a group."),
     ]},
    {"heading": "4. Comparing over time",
     "paragraphs": [
         ("The four survey rounds are used in OPHI's version made comparable over time. "
         "Between rounds, states mostly kept their positions relative to each other, even "
         "where poverty levels changed."),
     ]},
    {"heading": "5. The conflict layer",
     "paragraphs": [
         ("We counted recorded violent events and deaths in each state for each survey "
         "year, divided by population, and scaled them from 0 to 100 within that year."),
         ("Limits: events that are not reported are missed, and reporting may be weakest "
         "in some of the poorest areas. In 2021, 10 of the 37 states recorded no events at "
         "all, including five of the poorest 12 (Bauchi, Jigawa, Kebbi, Katsina and "
         "Kano). We could not detect a link between conflict and poverty, but this design "
         "could only have seen a fairly strong one, so that is not proof there is none."),
     ]},
    {"heading": "6. The climate layer",
     "paragraphs": [
         ("We took daily weather for each state capital from 1990 to 2024 and worked out "
         "the 1991–2020 averages."),
         ("Rainfall goes down as you move north, and poverty is higher in the states "
         "further north, so the two line up. That overlap does not show that weather "
         "causes poverty: how far north a state is matches poverty about as closely as "
         "rainfall does."),
     ]},
    {"heading": "7. The party question",
     "paragraphs": [
         ("We asked one question: between 2013 and 2021, did poverty fall faster in states "
         "whose governor was from the President's party? We wrote down the main test and "
         "the wording of the possible answers before running it. A few of the re-tests "
         "were added afterwards, and the technical details say which."),
         ("Each state was compared with itself across three periods (2013–16, 2016–18, "
         "2018–21). To check the gap was not luck, we shuffled the party records between "
         "states 10,000 times and counted how often a gap that big appeared by chance, "
         "then re-tested it in other ways. The answer, and how many re-tests it "
         "survived, is in the party-question section."),
     ]},
    {"heading": "8. Do poor states sit next to poor states?",
     "paragraphs": [
         *SPATIAL_READER_LINES,
         ("How we checked: for each state we compared its poverty score with the average "
         "of the states it borders. If poor states really do sit together, that comparison "
         "lines up more closely than it would if the same scores had been dealt out across "
         "the map at random. Statisticians call this resemblance between neighbours "
         "clustering. The sheet draws the comparison itself; the exact figures are in the "
         "small technical line on the sheet and in docs/spatial_analysis.md."),
         ("What it does not say: that poverty spreads from one state to the next, or that "
         "one state's poverty is caused by its neighbour's. Sharing a border is a fact "
         "about the map. Nor can it tell 37 states apart: the ranges of any two states "
         "that sit next to each other in the ranking overlap, so this atlas names no "
         "poorest state and no worst neighbourhood."),
     ]},
    {"heading": "9. What this atlas cannot tell you",
     "paragraphs": [
         ("It cannot show cause and effect: it describes patterns between 37 places. It "
         "says nothing about individual households, towns or local government areas, "
         "only whole states. It should not be compared with other countries' figures. And "
         "it is not the same as Nigeria's official national poverty measure from the "
         "National Bureau of Statistics (0.257), which uses a different list of needs, "
         "including work and shocks."),
     ]},
]


# --- The reference tab: one table where two prose pages used to be --------------
# "What the words mean" and "How we did it" are the same material seen from two sides
# -- a word, and how the thing behind it was made -- so they are one tabular sheet:
# one row per word, need and worked step, in three columns. The words are never
# retyped here: every meaning is the string above, so the table cannot drift from the
# prose it replaced.
#
# The table ships as three tabbed parts, one per group it already had (see
# docs/FIX_LEDGER.md W2): rendered as one dashboard it measured 2000 x 8720 px, which
# is thirteen screens on a 687 px window and not a tab anyone reads. The columns do
# not change between parts -- only the rows do -- so this is pagination, not a split
# back into two pages.
TABLE_TITLE = "Words, formulas and method"
TABLE_INTRO = (
    "The reference, in three parts. Every row: the term and its formula or "
    "weight, what it means, how it was made. No figure here is new."
)
TABLE_HEADERS: list[str] = [
    "Word, and its formula or weight",
    "What the words mean",
    "How we did it",
]

# The left column for the nine worked steps, keyed by the section heading. A section
# with no formula of its own still gets the notation or the count that identifies it,
# and the guard in table_rows() fails loudly if a heading is ever added without one.
METHOD_FORMULA: dict[str, str] = {
    "1. Where the numbers come from": "survey answers \u2192 OPHI's published state figures",
    "2. How a state's poverty score is built": "missing weights \u2265 1/3 \u2192 poor; MPI = H \u00d7 A",
    "3. How sure we can be": "\u00b1 about 30% of the score (median relative SE 15%)",
    "4. Comparing over time": "four rounds, one harmonised definition",
    "5. The conflict layer": "events and deaths per 100,000, rescaled 0\u2013100 within each year",
    "6. The climate layer": "1991\u20132020 baseline at the state capital",
    "7. The party question": "\u0394MPI per year on aligned share \u2014 108 state-intervals",
    "8. Do poor states sit next to poor states?": "Moran's I on shared borders (queen weights)",
    "9. What this atlas cannot tell you": "37 states, one country",
}
# Only for the sections that are a single paragraph: the others carry their making in
# their second and later paragraphs, which is where that text already lives.
METHOD_NOTE: dict[str, str] = {
    "3. How sure we can be": (
        "The standard errors are OPHI's design-based ones (UNDP table 5.4), extracted "
        "to data/interim/mpi_se_ci.csv."
    ),
    "4. Comparing over time": (
        "The four rounds and their values are in data/processed/atlas_vintages.csv, and "
        "the round-by-round panel is data/processed/mpi_trends_panel.csv."
    ),
    "9. What this atlas cannot tell you": (
        "Sources and licences are listed in docs/CLAIMS.md, and every download is logged "
        "with its date under data/raw/."
    ),
}

# The two rows that belong to the needs section but are not needs themselves.
HEALTH_ROW: TableRow = {
    "word": "Why health is a single item",
    "formula": "health = child deaths alone, weight 1/3",
    "meaning": INDICATORS_NOTE,
    "method": (
        "The UNDP subnational table flags Nutrition as missing for all 37 states: a "
        "country-wide exclusion, not a per-state gap. Comparing states with each other "
        "inside Nigeria therefore holds; comparing Nigeria with another country does not."
    ),
}
EXAMPLE_ROW: TableRow = {
    "word": "An example household",
    "formula": "16.7 + 5.6 + 5.6 + 5.6 + 5.6 = 38.9%",
    "meaning": EXAMPLE_VERDICT,
    "method": (
        "The five items: nobody old enough finished six years of school; cooks with "
        "wood; no electricity; safe water a 30-minute walk away; shares its toilet. The "
        "exact sum is 3/18 + 4/18 = 7/18 and the percentages are rounded."
    ),
}


def table_rows() -> list[tuple[str, str, list[TableRow]]]:
    """The reference tab in row order: (group heading, group intro, rows).

    Three groups, because the tab has three kinds of row: the words the atlas uses,
    the nine needs that produce them, and the nine steps of the making. Every string
    is taken from the structures above -- this function arranges, it does not author.
    """
    missing = [s["heading"] for s in METHOD if s["heading"] not in METHOD_FORMULA]
    assert not missing, f"method sections with no formula for the table: {missing}"

    words: list[TableRow] = [
        {
            "word": t["term"],
            "formula": t["formula"],
            "meaning": t["meaning"],
            "method": t["method"],
        }
        for t in TERMS
    ]
    needs: list[TableRow] = [
        {
            "word": i["need"],
            "formula": f"weight {i['weight']}",
            "meaning": i["missing_if"],
            "method": (
                f"Area: {i['area']}. The cut-off is OPHI's, the same for every state and "
                "every survey round."
            ),
        }
        for i in INDICATORS
    ]
    needs += [HEALTH_ROW, EXAMPLE_ROW]
    steps: list[TableRow] = [
        {
            "word": s["heading"].split(". ", 1)[1],
            "formula": METHOD_FORMULA[s["heading"]],
            "meaning": s["paragraphs"][0],
            "method": " ".join(s["paragraphs"][1:]) or METHOD_NOTE[s["heading"]],
        }
        for s in METHOD
    ]

    groups = [
        (WORDS_TITLE, WORDS_INTRO, words),
        (INDICATORS_TITLE, INDICATORS_INTRO, needs),
        (METHOD_TITLE, METHOD_INTRO, steps),
    ]
    # A row with an empty cell would render as a hole in the table, and nothing
    # downstream would complain -- so it is checked here, where the table is built.
    for heading, intro, rows in groups:
        assert intro.strip(), f"empty intro for the table group {heading!r}"
        for row in rows:
            for column, text in row.items():
                assert text.strip(), f"empty {column!r} in the table row {row['word']!r}"
    return groups

