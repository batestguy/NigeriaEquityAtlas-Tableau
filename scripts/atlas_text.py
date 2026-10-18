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
    meaning: str


class Indicator(TypedDict):
    area: str
    need: str
    weight: str
    missing_if: str


class Section(TypedDict):
    heading: str
    paragraphs: list[str]


WORDS_TITLE = "What the words mean"
WORDS_INTRO = (
    "This atlas measures poverty as missing basic needs in daily life, not as low "
    "income. Here is what each word on the map means."
)

TERMS: list[Term] = [
    {"term": "Poor",
     "meaning": "A person counts as poor if their household is missing at least one third "
                "of the weighted list of basic needs below. Everyone in a household gets "
                "the same result."},
    {"term": "Missing a need (deprived)",
     "meaning": "The household lacks one item on the list, for example it has no "
                "electricity, or nobody old enough has finished six years of school."},
    {"term": "Deprivation score",
     "meaning": "How much of the weighted list a household is missing, from 0% (nothing "
                "missing) to 100% (everything missing). 33.3% or more means poor."},
    {"term": "Close to poverty (vulnerable)",
     "meaning": "Missing between 20% and 33.3% of the list. Not counted as poor, but near "
                "the line."},
    {"term": "Severe poverty",
     "meaning": "Missing 50% or more of the list."},
    {"term": "Share of people who are poor (H)",
     "meaning": "Out of every 100 people, how many count as poor. Nigeria in 2021: "
                "33.0%, about 1 in 3."},
    {"term": "How much poor people miss (A)",
     "meaning": "Among poor people only, the average deprivation score. Nigeria in 2021: "
                "52.9%, so a typical poor person was missing about half of the list."},
    {"term": "Poverty score (MPI)",
     "meaning": "The share of people who are poor multiplied by how much they miss "
                "(H × A). It runs from 0 (nobody poor) to 1 (everybody poor and missing "
                "everything). Nigeria's global MPI in 2021 (MICS 2021 survey): "
                "0.330 × 0.529 = 0.175."},
    {"term": "Likely range",
     "meaning": "Surveys talk to a sample of households, not everyone, so every figure "
                "has some uncertainty. The likely range is where the true value probably "
                "lies (statisticians call it a 95% confidence interval). When two states' "
                "ranges overlap, we cannot be sure which one is poorer."},
    {"term": "Poverty band",
     "meaning": "One of the five colour groups on the map: under 5%, 5%–10%, "
                "10%–20%, 20%–30%, and 30% or more. The score is a 0-to-1 index, so "
                "these read as percentages of the index, not as the share of people "
                "who are poor (that share is shown separately and is much higher). The "
                "map uses bands rather than a 1-to-37 ranking because the likely "
                "ranges of states next to each other in the ranking overlap."},
    {"term": "Poorest 12 and Other 25",
     "meaning": "The 12 states with a poverty score above 0.20, and the remaining 25 "
                "(including FCT)."},
    {"term": "Area of life (dimension)",
     "meaning": "The list is grouped into three areas: health, education and living "
                "standards. Each area counts for one third."},
    {"term": "Share from each area (contribution)",
     "meaning": "How much of a state's poverty score comes from health, from education "
                "and from living standards. The three add up to 100%."},
    {"term": "Survey round",
     "meaning": "One of the four large national household surveys used: 2013 (DHS), "
                "2016–17 (MICS), 2018 (DHS) and 2021 (MICS). DHS is the Demographic and "
                "Health Survey; MICS is the Multiple Indicator Cluster Survey. The map "
                "shows 2021."},
    {"term": "Comparable over time (harmonised)",
     "meaning": "A version of the four rounds prepared by Oxford University's poverty "
                "team (OPHI) so that changes between rounds can be compared fairly."},
    {"term": "Conflict exposure (0–100)",
     "meaning": "How many recorded violent events and deaths a state had per 100,000 "
                "people in a survey year, compared with the other states that same year. "
                "100 is the most of the 37 that year and 0 the fewest. It is relative, so "
                "50 in 2013 and 50 in 2021 are not the same amount."},
    {"term": "Recorded conflict event",
     "meaning": "An incident of organised violence in which at least one person is reported "
                "to have died, "
                "logged by the Uppsala Conflict Data Program from news and other reports. "
                "Violence that is never reported is missed."},
    {"term": "Climate baseline",
     "meaning": "A state capital's average yearly temperature and rainfall over "
                "1991–2020."},
    {"term": "Governor from the President's party",
     "meaning": "The state governor belonged to the same party as the President: the "
                "PDP (People's Democratic Party) until 29 May 2015, the APC (All "
                "Progressives Congress) after that."},
    {"term": "Party that won most often",
     "meaning": "The party that won the most governorship elections in the state from "
                "1999 to 2021. Ties are shown. It appears in the map's hover text only."},
    {"term": "FCT",
     "meaning": "The Federal Capital Territory (Abuja). It is shown like a state, but it "
                "has no elected governor, so it is left out of the party question."},
    {"term": "Neighbouring states",
     "meaning": "Two states that share a border on the map. Nothing more is meant by it: "
                "it is a fact about the map, not about people or traffic moving between "
                "the states."},
    {"term": "States that resemble each other (clustering)",
     "meaning": "When states that share a border tend to have similar poverty scores, "
                "more often than if the scores were scattered about at random. It "
                "describes the pattern on the map. It does not say that one state's "
                "poverty makes its neighbour poorer."},
    {"term": "Explained by how far north a state is",
     "meaning": "Because poverty rises steadily from south to north, a lot of states "
                "looking like their neighbours is just that steady slope. Once the slope "
                "is taken out, we can see how much resemblance is left over and above "
                "it."},
]

INDICATORS_TITLE = "The list of basic needs"
INDICATORS_INTRO = (
    "Each item has a weight. A household's deprivation score "
    "is the sum of the weights of the items it is missing."
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

# The five MPI bands in the order they run, each with the colour it draws.
# One list, three surfaces: stage 6 writes it into the workbook (a discrete field
# given a palette -- the grammar lives inside the <datasource>, between <layout/>
# and <semantic-values>), stage 5 draws the matplotlib QA gate from it, and stage
# 7 draws the offline HTML map from it. Two maps that colour the same field
# differently would read as two different findings.
#
# ColorBrewer YlOrBr, 5-class sequential: no red-green pair, so it survives
# colour-vision deficiency, and it darkens monotonically, so the band order is
# legible from the colour alone. The leading "N. " in each label is a sort key
# (the Tableau legend sorts alphabetically), not part of what the reader is meant
# to read -- stage 5 and stage 7 strip it.
MPI_BANDS: list[tuple[str, str]] = [
    ("1. under 5%", "#ffffd4"),
    ("2. 5% to 10%", "#fed98e"),
    ("3. 10% to 20%", "#fe9929"),
    ("4. 20% to 30%", "#d95f0e"),
    ("5. 30% and above", "#993404"),
]
# --- The spatial sheet: do poor states sit next to poor states? ---------------
# A diagnostic on sheet 1's map, not a second poverty map. Every word here is
# written for a reader who does not know any statistics: the statistic is named
# once, in the small technical line, and never in a headline. The wording of the
# four reading lines is frozen in docs/spatial_preregistration.md, which was
# committed before the analysis code existed; 09_spatial_diagnostics.py asserts
# that the figures these words state are still the figures in the data.
# The cluster map: sheet 1's own geometry, drawn a second time with the
# neighbourhood type as the fill. It is the "where" of the same question the scatter
# answers "how much" of, and it sits immediately after the poverty map in the tab
# order. The colours are descriptive and are never a significance map: only one
# state survives the correction (SPATIAL_READER_LINES line 4), so a map of what is
# statistically significant would be a single state and would re-import the
# per-state ordering the atlas withdrew (docs/FIX_LEDGER.md A1).
SPATIAL_MAP_TITLE = "Where poverty clusters"
SPATIAL_MAP_SUBTITLE = (
    "Each state coloured by its own poverty and its neighbours' \u2014 descriptive, "
    "not a significance test"
)
SPATIAL_MAP_READING = (
    "The colour says two things at once. Purple means this state is poorer than the "
    "average state, teal means it is better off than average. Deep means the states "
    "it borders are on the same side as it is, pale means they are not. Read it as a "
    "description of where poverty sits, not as a list of places that stand out: the "
    "lines below give the one number that says how much of this is more than the "
    "north being poorer than the south."
)
SPATIAL_TITLE = "Do poor states sit next to poor states?"
SPATIAL_SUBTITLE = (
    "States with similar poverty scores do tend to share a border \u2014 but most of that "
    "is simply that the north is poorer than the south"
)
SPATIAL_AXIS_OWN = "This state's poverty score (MPI, % of index)"
SPATIAL_AXIS_NEIGHBOURS = "Average poverty score of the states it borders (MPI, % of index)"
SPATIAL_LEGEND_TITLE = "Neighbourhood type"
SPATIAL_LEGEND_MEANING = "this state's poverty, beside its neighbours'"
SPATIAL_READING_HEADING = "The reading, in plain words"
# The scatter's own "how to read this surface" sentence: on the map the reading is
# colours, on the scatter it is two axes. Both surfaces carry the same four lines
# below and the same technical footer.
SPATIAL_AXIS_READING = (
    "A state above the middle line is poorer than the average state; one to the right "
    "of the upright line has poorer neighbours than average. So \u201chigh, beside "
    "high\u201d means poor among poor neighbours, and \u201clow, beside low\u201d means "
    "better off among better-off neighbours."
)
# The caveat that has to survive on both surfaces, because "neighbourhood type" is
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
# Hue says how poor *this* state is, shade says whether its neighbours are like it
# (verified against the hexes rather than asserted, 2026-10-18: the two pale tints
# were the wrong way round, which made the hue encode the neighbours instead):
# deep purple = poor among poor neighbours, pale purple = poor among better-off
# neighbours, pale teal = better off among poorer neighbours, deep teal = better off
# among better-off neighbours. That is the reading the map's own legend words need,
# and it is the one a reader can check against a map by eye -- purple states are the
# poor ones.
# Deliberately not the poverty ramp and not the dimension colours, so neither spatial
# sheet can be read as a second poverty map. Nominal fields otherwise draw in
# Tableau's default categorical palette.
SPATIAL_QUADRANTS: list[tuple[str, str, str]] = [
    ("HH", "high, beside high", "#54278f"),
    ("HL", "high, beside low", "#b3a2c7"),
    ("LH", "low, beside high", "#80cdc1"),
    ("LL", "low, beside low", "#01665e"),
]

# The two deep fills. A property of the hexes above, not of the data: a map label is
# drawn white over these and in ink over the two pale tints, in both maps' previews.
SPATIAL_DEEP_TYPES: list[str] = ["high, beside high", "low, beside low"]

METHOD_INTRO = (
    "In plain terms: where the numbers come from, how they are put together, how sure "
    "we can be, and what this atlas cannot tell you."
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
