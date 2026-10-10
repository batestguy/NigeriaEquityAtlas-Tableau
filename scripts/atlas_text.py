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
     "meaning": "One of the five colour groups on the map: under 0.05, 0.05–0.10, "
                "0.10–0.20, 0.20–0.30, and 0.30 or more. The map uses bands rather than "
                "a 1-to-37 ranking because the likely ranges of states next to each other "
                "in the ranking overlap."},
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
    {"heading": "8. What this atlas cannot tell you",
     "paragraphs": [
         ("It cannot show cause and effect: it describes patterns between 37 places. It "
         "says nothing about individual households, towns or local government areas, "
         "only whole states. It should not be compared with other countries' figures. And "
         "it is not the same as Nigeria's official national poverty measure from the "
         "National Bureau of Statistics (0.257), which uses a different list of needs, "
         "including work and shocks."),
     ]},
]
