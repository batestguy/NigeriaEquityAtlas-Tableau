"""Stage 6 -- generate a Tableau workbook (.twb) and package it as a .twbx.

What is generated, and why it is deliberately lean
---------------------------------------------------
Hand-authored Tableau XML cannot be opened and checked on this machine: Tableau
Desktop 2019.4 is too old to open a modern workbook and needs interactive
licensing, and Tableau Public has no write API. So the workbook is built to a
schema taken from a real, working Nigeria state-level Public viz
(``ClimatechangeprofileNigeria``, 69.9k views), downloaded and unpacked via the
Tableau MCP server, and every column reference it emits is verified against the
columns it declares.

The datasource is a CSV textscan connection with the data files packaged inside
the .twbx. That is the lowest-risk option: no Hyper file to generate, and
Tableau converts a local extract on publish. A live Google Sheets connection, as
the original spec assumed, is unnecessary -- it would add a refresh dependency
the data does not need, since the MPI survey updates annually.

Sheet inventory
---------------
  1  Where poverty sits            filled map on the geographic role
  2  Dimension breakdown     stacked bar, three dimension contributions
  3  Poverty vs conflict     scatter
  4  Poverty over time       line across the four survey rounds
  5  Incidence x intensity   scatter with quadrant labels

The spec's fifth visual, a radar chart, is *not* generated. A radar needs a
polygon mark driven by computed path fields, which is the most fragile part of
the Tableau grammar to hand-write and the part least likely to survive first
contact with the application. It is left as a documented five-minute GUI step in
docs/PUBLISH.md, with the matplotlib preview as the design reference.
"""

from __future__ import annotations

import csv
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from common import PROCESSED, REPO_ROOT

DS_NAME = "federated.0mpiatlas2021"
DS_CAPTION = "Nigeria MPI Atlas"
CONN_NAME = "hyper.0mpiatlas2021"
OUT_DIR = REPO_ROOT / "tableau"
VERSION = "18.1"

# datatype, role, type prefix used in field references
MEASURES = [
    ("mpi", "real"),
    ("headcount_ratio_pct", "real"),
    ("intensity_pct", "real"),
    ("vulnerable_pct", "real"),
    ("severe_pct", "real"),
    ("contrib_health_pct", "real"),
    ("contrib_education_pct", "real"),
    ("contrib_living_standards_pct", "real"),
    ("population_thousands", "real"),
    ("mpi_poor_thousands", "real"),
    ("events", "integer"),
    ("fatalities", "real"),
    ("fatalities_low", "real"),
    ("fatalities_high", "real"),
    ("events_per_100k", "real"),
    ("fatalities_per_100k", "real"),
    ("fatalities_per_100k_high", "real"),
    ("conflict_exposure_index", "real"),
    ("temp_mean_c", "real"),
    ("precip_total_mm", "real"),
    ("temp_anomaly_c", "real"),
    ("precip_anomaly_pct", "real"),
    ("baseline_temp_c", "real"),
    ("baseline_precip_mm", "real"),
    # OPHI's design-based standard error and 95% bounds (UNDP 5.4). Carried so
    # the map can show an uncertainty interval instead of implying that 37 point
    # estimates are 37 distinguishable values.
    ("mpi_se", "real"),
    ("mpi_ci_lo", "real"),
    ("mpi_ci_hi", "real"),
    ("headcount_se", "real"),
    ("mpi_rank", "integer"),
    ("mpi_poor_rank", "integer"),
    ("lat", "real"),
    ("lon", "real"),
]
DIMENSIONS = [
    "pcode",
    "state",
    "capital",
    "quadrant",
    "mpi_band",
    "poverty_group",
    "indicators_missing",
    "survey",
    "n_indicators",
    "survey_year",
]

PANEL_MEASURES = ["mpi", "headcount_ratio_pct", "intensity_pct", "events", "fatalities",
                  "fatalities_low", "fatalities_high", "events_per_100k",
                  "fatalities_per_100k", "fatalities_per_100k_high",
                  "conflict_exposure_index", "temp_mean_c",
                  "temp_anomaly_c", "precip_anomaly_pct", "mpi_change_since_prev"]
PANEL_DIMS = ["pcode", "state", "survey_year", "survey", "mpi_change_significant"]


def ref(column: str, kind: str) -> str:
    """Build a Tableau field reference such as [ds].[sum:mpi:qk]."""
    if kind == "dim":
        return f"[{DS_NAME}].[none:{column}:nk]"
    agg = "sum" if kind == "sum" else "avg"
    return f"[{DS_NAME}].[{agg}:{column}:qk]"





def col_block(name: str, datatype: str, role: str, *, geographic: bool = False,
              default_agg: str = "") -> str:
    """One <column> declaration.

    Two schema rules learned the hard way, by loading the workbook in Tableau:

    * A column carrying a geographic role must declare ``semantic-role``. Without it
      Tableau refuses to load with "missing required attribute 'semantic-role'".
    * ``<semantic-values>`` is **not** a legal child of ``<column>``. It belongs on
      the datasource, once. Putting it inside the column produces the same
      "missing required attribute" error, because the schema parser trips over the
      unexpected child before it ever reads the attributes.
    """
    extra = f" default-aggregation-type='{default_agg}'" if default_agg else ""
    if datatype == "string":
        type_attr = "nominal"
    elif datatype == "integer":
        type_attr = "ordinal"
    else:
        type_attr = "quantitative"
    # The coordinate columns need their own semantic roles. Verified in the
    # application 2026-10-06: with [Geographical].[Latitude] and
    # [Geographical].[Longitude] absent, Tableau treats lat and lon as two
    # unrelated measures and draws a text table or a bar chart, never a map.
    if name == "lat":
        semantic_role = " semantic-role='[Geographical].[Latitude]'"
    elif name == "lon":
        semantic_role = " semantic-role='[Geographical].[Longitude]'"
    elif geographic:
        semantic_role = " semantic-role='[State].[Name]'"
    else:
        semantic_role = ""
    return (
        f"      <column caption='{escape(name)}' datatype='{datatype}' name='[{escape(name)}]' "
        f"role='{role}' type='{type_attr}'{semantic_role}{extra} />\n"
    )


# Hyper spells 64-bit floats "DOUBLE PRECISION"; bare DOUBLE collides with a
# domain of that name. The catalog reports the type back as DOUBLE, which is why
# the DDL spelling and the read-back spelling are kept apart.
HYPER_DDL_TYPE = {"string": "TEXT", "integer": "BIGINT", "real": "DOUBLE PRECISION"}
HYPER_CATALOG_TYPE = {"string": "TEXT", "integer": "BIG_INT", "real": "DOUBLE"}

ATLAS_HYPER = "mpi_atlas_2021.hyper"
PANEL_HYPER = "mpi_trends_panel.hyper"


def build_hyper(csv_path: Path, out_path: Path,
                columns: list[tuple[str, str, str]]) -> int:
    """Write a CSV to a Hyper extract at Extract.Extract, returning the row count.

    Tableau Public will only publish workbooks backed by extracts, and it expects
    the packaged file to hold a single table named Extract in a schema named
    Extract -- the same layout Tableau itself writes.

    This build of the Hyper API has no parameter binding, so values go into the
    INSERT as literals. That is fine at 37 and 148 rows; it is not the shape to
    use if this ever runs over a table large enough for statement limits to bite.
    """
    from tableauhyperapi import (
        Connection,
        CreateMode,
        HyperProcess,
        Telemetry,
    )

    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    out_path.parent.mkdir(parents=True, exist_ok=True)

    def literal(value: str, datatype: str) -> str:
        if value == "":
            return "NULL"
        if datatype == "integer":
            return str(int(value))
        if datatype == "real":
            return repr(float(value))
        return "'" + value.replace("'", "''") + "'"

    definition = ", ".join(
        f'"{name}" {HYPER_DDL_TYPE[datatype]}' for name, datatype, _role in columns
    )

    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as process:
        with Connection(
            endpoint=process.endpoint,
            database=out_path,
            create_mode=CreateMode.CREATE_AND_REPLACE,
        ) as conn:
            conn.execute_command('CREATE SCHEMA IF NOT EXISTS "Extract"')
            conn.execute_command(f'CREATE TABLE "Extract"."Extract" ({definition})')
            for row in rows:
                values = ", ".join(literal(row[name], datatype) for name, datatype, _ in columns)
                conn.execute_command(f'INSERT INTO "Extract"."Extract" VALUES ({values})')
    return len(rows)


def datasource_xml(columns: list[tuple[str, str, str]], hyper_filename: str, row_count: int,
                   instances: str = "", extra_columns: str = "") -> str:
    """One datasource over a packaged Hyper extract, with every column declared.

    Tableau Public refuses any workbook whose datasource is not an extract
    ("Workbooks saved to Tableau Public must use extracts", error 3C242D89), so
    the packaged data is a Hyper file rather than the source CSV. Tableau reads
    the column types from that file, which is why no <metadata-records> are
    written here: they are a cache Tableau maintains, and hand-writing them
    against the old textscan type codes would only contradict the real schema.

    ``instances`` are the <column-instance> elements for the fields the worksheets
    place on shelves. They belong on the datasource, not only in the worksheets:
    Tableau builds a datasource's field list from its <column> and
    <column-instance> children, and a shelf reference with no instance behind it
    loads as "the field does not exist in your database" (error 9CA7205B).
    """
    cols = []
    for name, datatype, role in columns:
        cols.append(col_block(name, datatype, role, geographic=(name == "state")))

    col_blocks = "".join(cols)
    dbname = f"Data/{hyper_filename}"
    return f"""    <datasource caption='{DS_CAPTION}' inline='true' name='{DS_NAME}' version='{VERSION}'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='Extract' name='{CONN_NAME}'>
            <connection access_mode='readonly' author-locale='en' class='hyper' dbname='{dbname}' default-settings='hyper' schema='Extract' sslmode='' tablename='Extract'>
              <relation name='Extract' table='[Extract].[Extract]' type='table' />
            </connection>
          </named-connection>
        </named-connections>
        <relation connection='{CONN_NAME}' name='Extract' table='[Extract].[Extract]' type='table' />
      </connection>
      <aliases enabled='yes' />
{extra_columns}{col_blocks}{instances}      <extract count='-1' enabled='true' units='records'>
        <connection access_mode='readonly' author-locale='en' class='hyper' dbname='{dbname}' default-settings='hyper' schema='Extract' sslmode='' tablename='Extract'>
          <relation name='Extract' table='[Extract].[Extract]' type='table' />
        </connection>
      </extract>
      <layout dim-ordering='alphabetic' dim-percentage='0.5' measure-ordering='alphabetic' measure-percentage='0.4' show-structure='true' />
      <semantic-values>
        <semantic-value key='[Country].[Name]' value='&quot;Nigeria&quot;' />
      </semantic-values>
    </datasource>
"""


FIELD_REF = re.compile(
    r"\[[A-Za-z0-9_.]+\]\.\[(?P<agg>[a-z]+):(?P<field>[^\]:]+):(?P<kind>[a-z]+)\]"
)

DERIVATION = {"none": "None", "sum": "Sum", "avg": "Avg", "min": "Min", "max": "Max",
              "cnt": "Count", "attr": "Attribute", "usr": "User"}
KIND_TYPE = {"nk": "nominal", "ok": "ordinal", "qk": "quantitative"}


def column_instances(*texts: str) -> str:
    """A <column-instance> for every field the worksheet actually places.

    Tableau will not resolve a shelf reference such as [ds].[sum:lat:qk] unless
    the worksheet also declares that instance. Declaring the <column> is not
    enough: the reference alone loads as "the field does not exist in your
    database" (error 9CA7205B), one field at a time.

    Deriving these from the finished shelves keeps the two in step, so a field
    cannot be added to a shelf without its instance following automatically.
    """
    ordered: list[tuple[str, str, str]] = []
    for text in texts:
        for match in FIELD_REF.finditer(text or ""):
            item = (match.group("field"), match.group("agg"), match.group("kind"))
            if item not in ordered:
                ordered.append(item)

    out = []
    for field, agg, kind in ordered:
        derivation = DERIVATION.get(agg, agg.capitalize())
        field_type = KIND_TYPE.get(kind, "quantitative")
        out.append(
            f"      <column-instance column='[{escape(field)}]' derivation='{derivation}' "
            f"name='[{agg}:{escape(field)}:{kind}]' pivot='key' type='{field_type}' />\n"
        )
    return "".join(out)


def deps_xml(columns: list[tuple[str, str, str]]) -> str:
    """The per-worksheet column block real Tableau writes.

    Tableau repeats the datasource's columns inside every worksheet that uses it
    (<datasource-dependencies>). The matching <column-instance> elements are added
    by worksheet_xml, which can see which fields the shelves actually reference.
    """
    body = "".join(
        col_block(name, datatype, role, geographic=(name == "state")) for name, datatype, role in columns
    )
    return f"""          <datasource-dependencies>
{body}          </datasource-dependencies>
"""


def worksheet_xml(name: str, *, rows: str, cols: str, mark: str = "Automatic",
                  encodings: str = "", ds_name: str = DS_NAME,
                  ds_caption: str = DS_CAPTION,
                  deps: str = "", subtitle: str = "") -> str:
    pane = f"""      <panes>
        <pane selection-relaxation-option='selection-relaxation-allow'>
          <view>
            <breakdown value='auto' />
          </view>
          <mark class='{mark}' />
          <encodings>
{encodings}          </encodings>
          <style>
            <style-rule element='mark'>
              <format attr='mark-labels-show' value='true' />
            </style-rule>
          </style>
        </pane>
      </panes>
"""
    instances = column_instances(rows, cols, encodings)
    if instances:
        closing = "          </datasource-dependencies>"
        if closing in deps:
            deps = deps.replace(closing, f"{instances}{closing}")
        else:
            deps = (
                "          <datasource-dependencies>\n"
                f"{instances}{closing}\n{deps}"
            )
    return f"""    <worksheet name='{escape(name)}'>
      <layout-options>
        <title>
          <formatted-text>
            <run bold='true' fontsize='13'>{escape(name)}</run>{f"<run fontsize='9'>  {escape(subtitle)}</run>" if subtitle else ""}
          </formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{ds_caption}' name='{ds_name}' />
          </datasources>
{deps}          <aggregation value='true' />
        </view>
        <style />
{pane}        <rows>{rows}</rows>
        <cols>{cols}</cols>
      </table>
    </worksheet>
"""


PANEL_DS_NAME = "federated.0mpipanel2021"
PANEL_DS_CAPTION = "Nigeria MPI trends panel"
PANEL_CONN = "hyper.0mpipanel2021"


def build_workbook(atlas_columns: list[tuple[str, str, str]], atlas_rows: int,
                   panel_columns: list[tuple[str, str, str]], panel_rows: int) -> str:
    atlas_deps = deps_xml(atlas_columns)
    panel_deps = deps_xml(panel_columns)

    # ---- sheet 1: geographic view -------------------------------------------
    # Verified 2026-10-06 by opening the workbook in Tableau Public and LOOKING at
    # it -- the first time this has been done. Four attempts, recorded because the
    # next person will otherwise repeat them:
    #
    #   1. cols = state / SUM(lat) + SUM(lon)  ->  74 small lat/lon BAR CHARTS.
    #      The old handoff called this "opens and renders"; the workbook loaded,
    #      the map did not exist. This is the defect nobody checked.
    #   2. Hand-written [Latitude (generated)] / [Longitude (generated)] on the
    #      shelves, WITH matching <column> declarations -> red unresolved pill on
    #      Columns, blank canvas. Those fields are synthesised by Tableau; declaring
    #      them by hand conflicts with the real definition.
    #   3. No coordinates on the shelves at all, geographic role on `state` alone
    #      -> renders 37 coloured numbers as a text table. The role is not enough
    #      on its own; Tableau needs the coordinate fields present too.
    #   4. This: raw lat/lon as AVG on Rows/Columns. state on Detail carries the
    #      [State].[Name] role and the raw lat/lon carry [Geographical] roles, so
    #      Tableau treats the two measures as a coordinate pair and draws the map.
    #
    # Colour is the *band*, not the continuous MPI: with a median 95% CI width of
    # 0.075 against a median MPI of 0.092, a ramp invites the reader to resolve
    # differences the data cannot support. All 36 adjacent rank pairs overlap at
    # 95%, so there is no ordering to show.
    #
    # Explorer upgrade: label with the state NAME (fun to read), and carry the
    # numbers on Detail so hover shows MPI + 95% CI + H + intensity + poor
    # thousands + group. Detail fields surface in the tooltip by default, so no
    # fragile <tooltip> tag is needed -- <lod> is the proven-safe encoding here.
    # poverty_group drives the Poorest-12-vs-rest toggle (filter in GUI).
    sheet_map = worksheet_xml(
        "Where poverty sits",
        subtitle="MICS 2021 · 5 bands, not 37 ranks · hover for MPI + 95% CI",
        rows=ref("lat", "avg"),
        cols=ref("lon", "avg"),
        # A filled map is not its own mark class -- it is an Automatic mark over a
        # geographic field. 'Map' is not in Tableau's mark enumeration and is
        # rejected on load with "value 'Map' not in enumeration".
        mark="Automatic",
        encodings=(
            f"            <lod column='{ref('state', 'dim')}' />\n"
            f"            <color column='{ref('mpi_band', 'dim')}' />\n"
            f"            <text column='{ref('state', 'dim')}' />\n"
            f"            <lod column='{ref('mpi', 'sum')}' />\n"
            f"            <lod column='{ref('mpi_se', 'sum')}' />\n"
            f"            <lod column='{ref('mpi_ci_lo', 'sum')}' />\n"
            f"            <lod column='{ref('mpi_ci_hi', 'sum')}' />\n"
            f"            <lod column='{ref('headcount_ratio_pct', 'sum')}' />\n"
            f"            <lod column='{ref('intensity_pct', 'sum')}' />\n"
            f"            <lod column='{ref('mpi_poor_thousands', 'sum')}' />\n"
            f"            <lod column='{ref('poverty_group', 'dim')}' />\n"
        ),
        deps=atlas_deps,
    )

    # ---- sheet 2: dimension breakdown ---------------------------------------
    # Verified 2026-10-06 in the application. The Measure Names / Measure Values
    # pair was tried first, because that is what a stacked bar needs, and it did
    # NOT work from hand-written XML: without a Measure Values filter Tableau sums
    # every measure on the shelf, so the sheet drew one 18,000-tall bar per state
    # with all three dimension shares stacked into it. Reproducing that pair
    # correctly needs the <measure-values> filter element as well.
    #
    # So this is reverted to three separate measures on Rows, which renders as three
    # aligned panes. That is a real change from the old single-measure layout but
    # it is NOT a stacked bar, and the sheet title says so. Finishing this properly
    # is a five-click GUI step (Analysis > Measure Names/Values), documented in
    # docs/PUBLISH.md alongside the radar chart.
    #
    # What IS fixed here: each measure is on the shelf separately so all three are
    # visible and comparable, and the colour binding no longer carries a different
    # measure than bar length.
    sheet_bar = worksheet_xml(
        "Dimension breakdown (three panels, not stacked)",
        rows=f"{ref('contrib_health_pct', 'sum')} + {ref('contrib_education_pct', 'sum')} "
             f"+ {ref('contrib_living_standards_pct', 'sum')}",
        cols=ref("state", "dim"),
        mark="Bar",
        # No text encoding. The MPI label was inherited from the old layout and it
        # reads as a data label on a bar whose length is a dimension SHARE, which
        # is exactly the confusion this sheet should not have. The value is on the
        # map and in the tooltip instead.
        encodings="",
        deps=atlas_deps,
    )

    # ---- sheet 3: poverty vs conflict --------------------------------------
    # No size encoding: fatalities is a raw count on a plot whose axes are an index
    # and a per-100k relative scale, and Borno's 2,027 deaths dominate the size
    # scale so every other state collapses to a dot. quadrant goes on Shape as well
    # as Colour, because colour alone fails WCAG 1.4.1.
    sheet_scatter = worksheet_xml(
        "Poverty vs conflict",
        rows=ref("conflict_exposure_index", "sum"),
        cols=ref("mpi", "sum"),
        mark="Circle",
        encodings=(
            f"            <lod column='{ref('state', 'dim')}' />\n"
            f"            <color column='{ref('quadrant', 'dim')}' />\n"
            f"            <shape column='{ref('quadrant', 'dim')}' />\n"
            f"            <text column='{ref('state', 'dim')}' />\n"
        ),
        deps=atlas_deps,
    )

    # ---- sheet 4: poverty over time ----------------------------------------
    # state must come off Columns. As a second discrete field on Columns it
    # produces 37 side-by-side single-point panes and the trend is invisible; on
    # Colour it produces 37 lines on one shared axis, which is the actual finding.
    sheet_trend = worksheet_xml(
        "Poverty over time",
        rows=f"[{PANEL_DS_NAME}].[sum:mpi:qk]",
        cols=f"[{PANEL_DS_NAME}].[none:survey_year:nk]",
        mark="Line",
        encodings=(
            f"            <lod column='[{PANEL_DS_NAME}].[none:state:nk]' />\n"
            f"            <color column='[{PANEL_DS_NAME}].[none:state:nk]' />\n"
        ),
        deps=panel_deps,
        ds_name=PANEL_DS_NAME,
        ds_caption=PANEL_DS_CAPTION,
    )

    # ---- sheet 5: incidence x intensity ------------------------------------
    # Size dropped: corr(headcount_ratio, mpi_poor_thousands) is +0.942, so the size
    # channel was encoding the x-axis a second time and telling the reader nothing.
    sheet_quadrant = worksheet_xml(
        "Incidence vs intensity",
        rows=ref("intensity_pct", "sum"),
        cols=ref("headcount_ratio_pct", "sum"),
        mark="Circle",
        encodings=(
            f"            <lod column='{ref('state', 'dim')}' />\n"
            f"            <color column='{ref('quadrant', 'dim')}' />\n"
            f"            <shape column='{ref('quadrant', 'dim')}' />\n"
            f"            <text column='{ref('state', 'dim')}' />\n"
        ),
        deps=atlas_deps,
    )

    # The methodology text lives on the dashboard canvas, not in the viz
    # description. Every caveat the atlas depends on -- the Nutrition exclusion,
    # the cross-sectionally relative conflict index, zero-reported-event states,
    # the unresolvable rank ordering -- is otherwise invisible to a reader, and a
    # reviewer looking at the published viz would have to find it in the repo.
    method_text = (
        "Poverty: OPHI / UNDP Global MPI, harmonised series (Data Table 6, MN 63). "
        "Nutrition was not collected in any Nigerian round, so Health rests on child "
        "mortality alone and takes the full one-third dimension weight; within-Nigeria "
        "comparison holds, cross-country does not. "
        "Standard errors are OPHI's design-based ones: the median relative SE is 15%, "
        "and all 36 adjacent state rank pairs overlap at 95%, so no single state is "
        "statistically 'the highest'. Map colours are bands, not a continuous ramp. "
        "Conflict: UCDP GED 24.1, CC BY-IGO. The exposure index is scaled within each "
        "survey year, so 100 means most of these 37 states that year, not an absolute "
        "level. Ten states recorded no UCDP event in 2021, which reflects reporting "
        "coverage as much as absence of violence; the conflict variable undercounts "
        "most in the poorest states, so the absence of a detected association is a "
        "limit of the design (n=37, power 0.75 at rho=0.4) and not evidence of none. "
        "Climate: Open-Meteo Archive API at state capitals, CC BY. Baseline rainfall is "
        "a north-south gradient rather than a driver -- latitude predicts MPI better "
        "than precipitation does -- so it is shown for context only. "
        "Boundaries: geoBoundaries ADM1, CC BY 4.0. Capitals: GeoNames, CC BY 4.0. "
        "Pipeline: reproducible, 37/37 states at every stage."
    )

    kpi_text = (
        "National MPI 0.175 (2021)   |   Median relative SE 15%   |   "
        "All 36 adjacent rank pairs overlap at 95%   |   "
        "Rank persistence 0.87-0.92   |   "
        "Poorest 12 states 40% education-driven vs 22% elsewhere"
    )

    text_zone = (
        "          <zone h='9000' id='20' type-v2='text' w='160000' x='0' y='0'>\n"
        f"            <formatted-text><run fontcolor='#3b3b3b' fontsize='10'>{escape(method_text)}"
        "</run></formatted-text>\n"
        "          </zone>\n"
    )
    kpi_zone = (
        "          <zone h='7000' id='21' type-v2='text' w='160000' x='0' y='9000'>\n"
        f"            <formatted-text><run bold='true' fontcolor='#1a1a1a' fontsize='12'>"
        f"{escape(kpi_text)}</run></formatted-text>\n"
        "          </zone>\n"
    )

    dashboards = f"""  <dashboards>
    <dashboard name='Equity Atlas'>
      <layout-options>
        <title>
          <formatted-text>
            <run bold='true' fontsize='16'>Nigeria Multidimensional Poverty Equity Atlas</run>
            <run fontsize='10'>  MICS 2021 &#183; 36 states + FCT &#183; OPHI harmonised series</run>
          </formatted-text>
        </title>
      </layout-options>
      <style />
      <size maxheight='1500' maxwidth='1600' minheight='1500' minwidth='1600' />
      <zones>
        <zone h='150000' id='3' type-v2='layout-basic' w='160000' x='0' y='0'>
{text_zone}{kpi_zone}          <zone h='51000' id='4' name='Where poverty sits' w='160000' x='0' y='57000' />
          <zone h='51000' id='5' name='Dimension breakdown (three panels, not stacked)' w='58000' x='0' y='16000' />
          <zone h='51000' id='6' name='Poverty vs conflict' w='52000' x='58000' y='16000' />
          <zone h='51000' id='7' name='Incidence vs intensity' w='50000' x='110000' y='16000' />
          <zone h='77000' id='8' name='Poverty over time' w='160000' x='0' y='73000' />
        </zone>
      </zones>
    </dashboard>
  </dashboards>
"""

    windows = """  <windows source-height='1500'>
    <window class='worksheet' name='Where poverty sits'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='2147483647'>
            <card type='columns' />
          </strip>
        </edge>
      </cards>
    </window>
    <window class='worksheet' name='Dimension breakdown (three panels, not stacked)'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
      </cards>
    </window>
    <window class='worksheet' name='Poverty vs conflict'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
      </cards>
    </window>
    <window class='worksheet' name='Poverty over time'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
      </cards>
    </window>
    <window class='worksheet' name='Incidence vs intensity'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
      </cards>
    </window>
    <window class='dashboard' name='Equity Atlas'>
      <viewpoints>
        <viewpoint name='Where poverty sits' />
        <viewpoint name='Dimension breakdown (three panels, not stacked)' />
        <viewpoint name='Poverty vs conflict' />
        <viewpoint name='Poverty over time' />
        <viewpoint name='Incidence vs intensity' />
      </viewpoints>
      <active id='-1' />
    </window>
  </windows>
"""

    atlas_sheets = " ".join([sheet_map, sheet_bar, sheet_scatter, sheet_quadrant])
    panel_sheets = " ".join([sheet_trend])
    atlas_instances = column_instances(atlas_sheets)
    atlas_ds = datasource_xml(
        atlas_columns, ATLAS_HYPER, atlas_rows, atlas_instances,
    )
    panel_ds = datasource_xml(
        panel_columns, PANEL_HYPER, panel_rows, column_instances(panel_sheets)
    )
    # The caption must change too: Tableau keys datasource identity on it, and two
    # datasources sharing one caption trips UniqueDataSource on open.
    panel_ds = (
        panel_ds.replace(DS_NAME, PANEL_DS_NAME)
        .replace(CONN_NAME, PANEL_CONN)
        .replace(f"caption='{DS_CAPTION}'", f"caption='{PANEL_DS_CAPTION}'", 1)
    )

    return f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook original-version='{VERSION}' source-build='2024.1.0 (20241.24.0212.1000)' source-platform='win' version='{VERSION}' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>
  <datasources>
{atlas_ds}{panel_ds}  </datasources>
  <worksheets>
{sheet_map}{sheet_bar}{sheet_scatter}{sheet_trend}{sheet_quadrant}  </worksheets>
{dashboards}{windows}</workbook>
"""


def validate(xml: str, declared: set[str]) -> list[str]:
    """Parse the XML and confirm every bracketed field reference resolves."""
    problems: list[str] = []
    try:
        ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        return [f"XML is not well formed: {exc}"]

    import re

    for match in re.finditer(r"\[federated\.[^\]]+\]\.\[[^\]]+\]", xml):
        token = match.group(0)
        tail = re.search(r"\.\[([^\]]+)\]$", token)
        if tail is None:
            problems.append(f"unparseable field reference {token}")
            continue
        parts = tail.group(1).split(":")
        # Tableau's generated geographic fields are synthesised, not columns in
        # the extract, so they cannot resolve against `declared` either.
        if parts[0] in {"Multiple Fields", "Multiple Values"} or "generated" in parts[1]:
            continue
        if len(parts) < 2:
            problems.append(f"unparseable field reference {token}")
            continue
        # Measure Names and Measure Values are Tableau's own generated fields, not
        # columns in the extract. They carry no aggregation prefix and are declared
        # by Tableau itself, so they cannot resolve against `declared`.
        if parts[0] in {"Multiple Fields", "Multiple Values"}:
            continue
        if len(parts) < 2:
            problems.append(f"unparseable field reference {token}")
            continue
        agg, name = parts[0], parts[1]
        if agg not in {"none", "sum", "avg", "min", "max", "ctd"}:
            problems.append(f"unknown aggregation {agg!r} in {token}")
        if name not in declared:
            problems.append(f"field reference to undeclared column {name!r} in {token}")
    for ds in ("[federated.0mpiatlas2021]", "[federated.0mpipanel2021]"):
        if ds not in xml:
            problems.append(f"datasource reference {ds} never declared")
    return problems


def check_hyper_schema(
    pairs: list[tuple[str, Path, list[tuple[str, str, str]]]],
    row_counts: dict[str, int],
) -> list[str]:
    """Confirm each packaged Hyper's real column order matches the declared columns.

    This is the failure that would actually hurt: a declared <column> list that
    disagrees with the extract silently attaches the wrong field to every visual,
    and nothing upstream would notice. Reading the schema back out of the .hyper
    checks the file Tableau will actually open, which is stronger than the CSV
    header check this replaced.
    """
    from tableauhyperapi import Connection, HyperProcess, TableName, Telemetry

    problems: list[str] = []
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as process:
        for label, path, columns in pairs:
            if not path.exists():
                problems.append(f"{label}: extract not written at {path}")
                continue
            with Connection(endpoint=process.endpoint, database=path) as conn:
                table_def = conn.catalog.get_table_definition(TableName("Extract", "Extract"))
                row_count = conn.execute_scalar_query(
                    'SELECT COUNT(*) FROM "Extract"."Extract"'
                )
            actual = [(c.name.unescaped, str(c.type)) for c in table_def.columns]
            if len(actual) != len(columns):
                problems.append(
                    f"{label}: extract has {len(actual)} columns but {len(columns)} declared"
                )
                continue
            for position, ((name, datatype, _role), (got_name, got_type)) in enumerate(
                zip(columns, actual)
            ):
                if got_name != name:
                    problems.append(
                        f"{label}: position {position} declared {name!r} "
                        f"but the extract holds {got_name!r}"
                    )
                expected_type = HYPER_CATALOG_TYPE[datatype]
                if got_type.upper() != expected_type:
                    problems.append(
                        f"{label}: column {name!r} declared {expected_type} "
                        f"but the extract holds {got_type}"
                    )
            problems.extend(
                f"{label}: expected {expected} rows in the extract, found {row_count}"
                for expected in [row_counts[label]]
                if row_count != expected
            )
    return problems


def main() -> int:
    atlas_path = PROCESSED / "mpi_atlas_2021.csv"
    panel_path = PROCESSED / "mpi_trends_panel.csv"
    for p in (atlas_path, panel_path):
        if not p.exists():
            raise SystemExit(f"missing {p}; run scripts/04_merge.py first")

    with atlas_path.open(newline="", encoding="utf-8-sig") as fh:
        atlas_reader = list(csv.DictReader(fh))
    with panel_path.open(newline="", encoding="utf-8-sig") as fh:
        panel_reader = list(csv.DictReader(fh))

    def infer(rows: list[dict[str, str]], numeric: list[str], dims: list[str]):
        cols: list[tuple[str, str, str]] = []
        for name in rows[0].keys():
            if name in numeric:
                cols.append((name, "integer" if name.endswith(("_rank",)) or name in {"events", "n_indicators", "survey_year"} else "real", "measure"))
            elif name in dims:
                cols.append((name, "string", "dimension"))
            else:
                cols.append((name, "string", "dimension"))
        return cols

    atlas_columns = infer(atlas_reader, [m for m, _ in MEASURES], DIMENSIONS)
    panel_columns = infer(
        panel_reader,
        PANEL_MEASURES,
        PANEL_DIMS,
    )
    # survey_year is numeric in the panel but categorical on the shelf
    panel_columns = [
        (n, "integer" if n == "survey_year" else dt, "measure" if dt != "string" else "dimension")
        for n, dt, _r in panel_columns
    ]

    declared = {n for n, _, _ in atlas_columns} | {n for n, _, _ in panel_columns}
    xml = build_workbook(atlas_columns, len(atlas_reader), panel_columns, len(panel_reader))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    atlas_hyper = OUT_DIR / ATLAS_HYPER
    panel_hyper = OUT_DIR / PANEL_HYPER
    atlas_n = build_hyper(atlas_path, atlas_hyper, atlas_columns)
    panel_n = build_hyper(panel_path, panel_hyper, panel_columns)

    problems = validate(xml, declared)
    problems += check_hyper_schema(
        [(ATLAS_HYPER, atlas_hyper, atlas_columns), (PANEL_HYPER, panel_hyper, panel_columns)],
        {ATLAS_HYPER: atlas_n, PANEL_HYPER: panel_n},
    )
    if problems:
        print("WORKBOOK VALIDATION FAILED")
        for p in problems:
            print("  -", p)
        return 1

    twb_path = OUT_DIR / "Nigeria-MPI-Equity-Atlas.twb"
    twb_path.write_text(xml, encoding="utf-8")

    twbx_path = OUT_DIR / "Nigeria-MPI-Equity-Atlas.twbx"
    with zipfile.ZipFile(twbx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(twb_path, twb_path.name)
        # The .twb references the extracts relative to the package root.
        zf.write(atlas_hyper, f"Data/{ATLAS_HYPER}")
        zf.write(panel_hyper, f"Data/{PANEL_HYPER}")

    print(f"XML validated: {len(declared)} columns declared, all field references resolve")
    print(
        f"Extracts validated: {ATLAS_HYPER} ({atlas_n} rows), "
        f"{PANEL_HYPER} ({panel_n} rows) match the declared columns"
    )
    print(f"wrote {twb_path.relative_to(REPO_ROOT)} ({twb_path.stat().st_size/1024:.0f} KB)")
    print(f"wrote {twbx_path.relative_to(REPO_ROOT)} ({twbx_path.stat().st_size/1024:.0f} KB)")
    with zipfile.ZipFile(twbx_path) as zf:
        print("package contents:")
        for n in zf.namelist():
            print(f"   {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())