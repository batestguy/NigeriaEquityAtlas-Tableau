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
  6  Party alignment and MPI change   scatter, aligned_share vs dmpi_annual,
                                      interval on Colour (stage 8 panel, its
                                      own extract; never coloured by party)

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

import atlas_text
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


def ref(column: str, kind: str, ds: str = DS_NAME) -> str:
    """Build a Tableau field reference such as [ds].[sum:mpi:qk]."""
    if kind == "dim":
        return f"[{ds}].[none:{column}:nk]"
    if kind == "ord":
        # An integer dimension is declared type='ordinal', so its reference must
        # carry :ok. Referencing one as :nk makes Tableau report that the field
        # does not exist (9CA7205B) -- verified 2026-10-17.
        return f"[{ds}].[none:{column}:ok]"
    agg = "sum" if kind == "sum" else "avg"
    return f"[{ds}].[{agg}:{column}:qk]"





def col_block(name: str, datatype: str, role: str, *, geographic: bool = False,
              default_agg: str = "", caption: str = "") -> str:
    """One <column> declaration.

    Two schema rules learned the hard way, by loading the workbook in Tableau:

    * A column carrying a geographic role must declare ``semantic-role``. Without it
      Tableau refuses to load with "missing required attribute 'semantic-role'".
    * ``<semantic-values>`` is **not** a legal child of ``<column>``. It belongs on
      the datasource, once. Putting it inside the column produces the same
      "missing required attribute" error, because the schema parser trips over the
      unexpected child before it ever reads the attributes.

    ``caption`` is what Tableau shows for the field everywhere it names it --
    shelf pills, tooltips' default fields and, for a colour field, the title of
    the colour legend. The captions default to the column name, which is how the
    legend used to read the internal name ``mpi_band``.
    """
    extra = f" default-aggregation-type='{default_agg}'" if default_agg else ""
    cap = f" caption='{escape(caption)}'" if caption else f" caption='{escape(name)}'"
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
        f"      <column{cap} datatype='{datatype}' name='[{escape(name)}]' "
        f"role='{role}' type='{type_attr}'{semantic_role}{extra} />\n"
    )


# Hyper spells 64-bit floats "DOUBLE PRECISION"; bare DOUBLE collides with a
# domain of that name. The catalog reports the type back as DOUBLE, which is why
# the DDL spelling and the read-back spelling are kept apart.
HYPER_DDL_TYPE = {"string": "TEXT", "integer": "BIGINT", "real": "DOUBLE PRECISION"}
HYPER_CATALOG_TYPE = {"string": "TEXT", "integer": "BIG_INT", "real": "DOUBLE"}

ATLAS_HYPER = "mpi_atlas_2021.hyper"
PANEL_HYPER = "mpi_trends_panel.hyper"
ALIGN_HYPER = "party_alignment_panel.hyper"
POLY_HYPER = "mpi_polygons.hyper"


def build_hyper(csv_path: Path, out_path: Path,
                columns: list[tuple[str, str, str]]) -> int:
    """Write a CSV to a Hyper extract at Extract.Extract, returning the row count.

    Tableau Public will only publish workbooks backed by extracts, and it expects
    the packaged file to hold a single table named Extract in a schema named
    Extract -- the same layout Tableau itself writes.

    This build of the Hyper API has no parameter binding, so values go into the
    INSERT as literals. Rows go in batches: one INSERT per statement, 500 rows at
    a time. A statement per row is fine at 37 and 148 rows but the polygon extract
    is ~53k vertices, and one INSERT each takes quarter of an hour.
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
            for start in range(0, len(rows), 500):
                batch = rows[start:start + 500]
                values = ", ".join(
                    "(" + ", ".join(literal(row[name], datatype) for name, datatype, _ in columns) + ")"
                    for row in batch
                )
                conn.execute_command(f'INSERT INTO "Extract"."Extract" VALUES {values}')
    return len(rows)


def datasource_xml(columns: list[tuple[str, str, str]], hyper_filename: str, row_count: int,
                   instances: str = "", extra_columns: str = "", **kwargs) -> str:
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
    captions: dict[str, str] = kwargs.get("captions", {})
    for name, datatype, role in columns:
        cols.append(col_block(name, datatype, role, geographic=(name == "state"),
                              caption=captions.get(name, "")))

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
                  deps: str = "", subtitle: str = "", tooltip: str = "",
                  mark_formats: tuple[tuple[str, str], ...] = ()) -> str:
    """A tooltip, when given, is Tableau's "customized tooltip": it replaces the
    default field list entirely, so fields that exist only to draw the mark stop
    appearing to the reader. Grammar taken from a real Tableau-authored workbook
    -- field references live in CDATA, wrapped in angle brackets.

    Position matters, and is not guessable: the element belongs *after*
    </encodings>, not between <mark> and <encodings>. Placed before the encodings
    it parses but fails the whole workbook load ("Errors occurred while trying to
    load the workbook"), with nothing in the log naming the element. Bisected
    2026-10-17 against Tableau Public 2026.2: identical workbooks differing only
    in this position load or fail. The reference workbook was no help -- its
    panes carry <encodings> or a tooltip, never both.

    ``mark_formats`` adds further <format> lines to the worksheet's mark style
    rule -- used by the map to thicken its white state borders. It goes in the
    worksheet-level <style>, after </view>, where a real Tableau-authored workbook
    puts mark formats; the pane has its own <style> too, but nothing there has been
    observed to take effect.
    """
    tooltip_block = (
        "          <customized-tooltip show-buttons='false'>\n"
        "            <formatted-text>\n"
        f"{tooltip}"
        "            </formatted-text>\n"
        "          </customized-tooltip>\n"
        if tooltip
        else ""
    )
    pane = f"""      <panes>
        <pane selection-relaxation-option='selection-relaxation-allow'>
          <view>
            <breakdown value='auto' />
          </view>
          <mark class='{mark}' />
          <encodings>
{encodings}          </encodings>
{tooltip_block}          <style>
            <style-rule element='mark'>
              <format attr='mark-labels-show' value='true' />
            </style-rule>
          </style>
        </pane>
      </panes>
"""
    style_block = ""
    if mark_formats:
        body = "".join(f"<format attr='{attr}' value='{value}' />" for attr, value in mark_formats)
        style_block = f"\n          <style-rule element='mark'>{body}</style-rule>\n        "
    instances = column_instances(rows, cols, encodings, tooltip)
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
        <style>{style_block}</style>
{pane}        <rows>{rows}</rows>
        <cols>{cols}</cols>
      </table>
    </worksheet>
"""


PANEL_DS_NAME = "federated.0mpipanel2021"
PANEL_DS_CAPTION = "Nigeria MPI trends panel"
PANEL_CONN = "hyper.0mpipanel2021"

ALIGN_DS_NAME = "federated.0partyalignment"
ALIGN_DS_CAPTION = "Party alignment panel"
ALIGN_CONN = "hyper.0partyalignment"
ALIGN_MEASURES = ["aligned_share", "aligned_binary", "aligned_share_sitting", "mpi_t0", "mpi_t1",
                  "dmpi_annual", "dlogmpi_annual"]
ALIGN_SHEET = "Party alignment and MPI change"

# --- The filled map's geometry (stage 4, mpi_polygons.csv) ---------------------
# Tableau's generated geographic fields cannot be hand-authored (see sheet 1), so
# the ADM1 rings ship as rows. Column order here must match POLY_FIELDS in
# 04_merge.py: build_hyper writes them in this order and stage 6 reads the schema
# back out of the .hyper to check.
POLY_DS_NAME = "federated.0mpipolygons"
POLY_DS_CAPTION = "Nigeria MPI polygons"
POLY_CONN = "hyper.0mpipolygons"
POLY_COLUMNS: list[tuple[str, str, str]] = [
    ("state", "string", "dimension"),
    ("pcode", "string", "dimension"),
    ("ring", "integer", "dimension"),
    ("point_order", "integer", "dimension"),
    ("lon", "real", "measure"),
    ("lat", "real", "measure"),
    ("mpi_band", "string", "dimension"),
    ("poverty_group", "string", "dimension"),
    ("mpi", "real", "measure"),
    ("mpi_se", "real", "measure"),
    ("mpi_ci_lo", "real", "measure"),
    ("mpi_ci_hi", "real", "measure"),
    ("headcount_ratio_pct", "real", "measure"),
    ("intensity_pct", "real", "measure"),
    ("mpi_poor_thousands", "real", "measure"),
    # The tooltip renders the MPI as a percentage of the index and cannot do
    # arithmetic, so the scaled values are columns (stage 4 writes mpi * 100), and
    # the governorship line is pre-composed there too -- domain and tie rules live
    # in one place, next to the checks that verify them.
    ("mpi_pct", "real", "measure"),
    ("mpi_ci_lo_pct", "real", "measure"),
    ("mpi_ci_hi_pct", "real", "measure"),
    ("gov_party", "string", "dimension"),
]


# --- Reader dashboards: plain-language text from scripts/atlas_text.py ---------
# Two text-only dashboards, "What the words mean" and "How we did it", built from
# the same strings stage 7 renders on the HTML page. The words live in
# atlas_text.py and are never retyped here; this code only lays them out.

READER_WIDTH = 1000  # px; fixed-size dashboards, tall rather than clipped
READER_PAD = 30  # px of slack added to every estimated zone height
TEXT_COLOUR = "#22252a"
BODY_SIZE = 11
TERM_SIZE = 11
HEADING_SIZE = 14
TITLE_SIZE = 20
# Tableau marks a paragraph break inside formatted text with this pair.
PARA_BREAK = "Æ&#10;"

# A paragraph is a list of (text, bold, fontsize) runs that share one line.
Run = tuple[str, bool, int]


def para(text: str, *, bold: bool = False, size: int = BODY_SIZE) -> list[Run]:
    return [(text, bold, size)]


def _run_xml(text: str, bold: bool, size: int) -> str:
    weight = " bold='true'" if bold else ""
    return f"<run{weight} fontcolor='{TEXT_COLOUR}' fontsize='{size}'>{escape(text)}</run>"


def _estimate_height(paragraphs: list[list[Run]], width_px: int) -> int:
    """Rendered height in px, sized for the worst case so nothing is clipped.

    Calibrated by eye on Tableau Public Desktop at 150% Windows scaling, which
    enlarges text but not the dashboard: an 11pt line there is ~30.5 px tall and
    holds ~93 characters across 1000 px. Fonts render smaller on the web, so
    the published dashboards get slack, never clipping.
    """
    import math

    height = 0.0
    for runs in paragraphs:
        size = max(r[2] for r in runs)
        chars_per_line = max(1, int((width_px - 40) / (size * 0.95)))
        chars = sum(len(r[0]) for r in runs) * 1.08  # word-wrap waste
        lines = max(1, math.ceil(chars / chars_per_line))
        height += lines * size * 2.8
    return int(height) + READER_PAD


def reader_zone(zone_id: int, y: int, h: int, paragraphs: list[list[Run]]) -> str:
    """One full-width text zone. Tiled zone geometry is in 1/100000ths of the
    dashboard, so y and h arrive already scaled."""
    body = f"<run fontsize='{BODY_SIZE}'>{PARA_BREAK}</run>".join(
        "".join(_run_xml(*r) for r in runs) for runs in paragraphs
    )
    return (
        f"          <zone h='{h}' id='{zone_id}' type-v2='text' w='100000' x='0' y='{y}'>\n"
        f"            <formatted-text>{body}</formatted-text>\n"
        "            <zone-style>\n"
        "              <format attr='margin' value='12' />\n"
        "            </zone-style>\n"
        "          </zone>\n"
    )


def reader_dashboard(name: str, zones: list[list[list[Run]]], first_id: int) -> str:
    """A fixed-width, text-only dashboard of vertically stacked text zones."""
    heights = [_estimate_height(z, READER_WIDTH) for z in zones]
    total = sum(heights)
    parts: list[str] = []
    y = 0
    for offset, (paragraphs, h_px) in enumerate(zip(zones, heights)):
        # The last zone takes the remainder so rounding never leaves a gap.
        h = 100000 - y if offset == len(zones) - 1 else round(h_px * 100000 / total)
        parts.append(reader_zone(first_id + offset, y, h, paragraphs))
        y += h
    return f"""    <dashboard name='{escape(name)}'>
      <style />
      <size maxheight='{total}' maxwidth='{READER_WIDTH}' minheight='{total}' minwidth='{READER_WIDTH}' />
      <zones>
        <zone h='100000' id='{first_id - 1}' type-v2='layout-basic' w='100000' x='0' y='0'>
{"".join(parts)}        </zone>
      </zones>
    </dashboard>
"""


BLANK: list[Run] = para(" ")


def words_dashboard() -> str:
    t = atlas_text
    terms = [
        [para(t.WORDS_TITLE, bold=True, size=TITLE_SIZE), para(t.WORDS_INTRO), BLANK]
    ]
    half = (len(t.TERMS) + 1) // 2
    for chunk in (t.TERMS[:half], t.TERMS[half:]):
        zone: list[list[Run]] = []
        for term in chunk:
            zone += [para(term["term"], bold=True, size=TERM_SIZE), para(term["meaning"]), BLANK]
        terms.append(zone)
    terms[0] += terms.pop(1)
    needs: list[list[Run]] = [para(t.INDICATORS_TITLE, bold=True, size=HEADING_SIZE),
                              para(t.INDICATORS_INTRO), BLANK]
    for i in t.INDICATORS:
        needs.append([
            (f"{i['area']} · {i['need']} · {i['weight']}", True, BODY_SIZE),
            (f" — Missing if: {i['missing_if']}", False, BODY_SIZE),
        ])
    needs += [BLANK, para(t.INDICATORS_NOTE), BLANK,
              para(t.EXAMPLE_TITLE, bold=True, size=HEADING_SIZE)]
    needs += [para(f"{item} — {w}") for item, w in t.EXAMPLE_LINES]
    # The total's label is the glossary's own term for it, not a retyped string.
    score_term = next(x["term"] for x in t.TERMS if x["term"] == "Deprivation score")
    needs += [para(f"{score_term} — {t.EXAMPLE_TOTAL}", bold=True), para(t.EXAMPLE_VERDICT)]
    return reader_dashboard(t.WORDS_TITLE, [*terms, needs], first_id=40)


def method_dashboard() -> str:
    t = atlas_text
    zones: list[list[list[Run]]] = [
        [para(t.METHOD_TITLE, bold=True, size=TITLE_SIZE), para(t.METHOD_INTRO), BLANK]
    ]
    half = (len(t.METHOD) + 1) // 2
    for chunk in (t.METHOD[:half], t.METHOD[half:]):
        zone: list[list[Run]] = []
        for section in chunk:
            zone.append(para(section["heading"], bold=True, size=HEADING_SIZE))
            zone += [para(p) for p in section["paragraphs"]]
            zone.append(BLANK)
        zones.append(zone)
    zones[0] += zones.pop(1)
    return reader_dashboard(t.METHOD_TITLE, zones, first_id=60)


READER_DASHBOARDS = [atlas_text.WORDS_TITLE, atlas_text.METHOD_TITLE]


def build_workbook(atlas_columns: list[tuple[str, str, str]], atlas_rows: int,
                   panel_columns: list[tuple[str, str, str]], panel_rows: int,
                   align_columns: list[tuple[str, str, str]], align_rows: int,
                   poly_rows: int) -> str:
    atlas_deps = deps_xml(atlas_columns)
    panel_deps = deps_xml(panel_columns)
    align_deps = deps_xml(align_columns)
    poly_deps = deps_xml(POLY_COLUMNS)

    # ---- sheet 1: the filled map -------------------------------------------
    # A genuine filled choropleth, drawn from shipped geometry rather than from
    # Tableau's geography engine. What was tried, in order:
    #
    #   1. cols = state / SUM(lat) + SUM(lon)  ->  74 small lat/lon BAR CHARTS.
    #      This shipped for the workbook's whole life; the handoff called it
    #      "renders". Verified in the application 2026-10-06.
    #   2. [Latitude (generated)] / [Longitude (generated)] on the shelves with
    #      matching <column> declarations -> red unresolved pill, blank canvas.
    #   3. Geographic role on `state` alone, no coordinates -> 37 coloured numbers
    #      as a text table.
    #   4. Raw lat/lon as AVG on Rows/Columns with [Geographical] roles -> a
    #      correctly georeferenced SCATTER of the 37 capitals. Not a filled map.
    #
    # The generated-field route is closed, and was re-verified against Tableau
    # Public 2026.2 on 2026-10-17:
    #   * referencing [none:Latitude (generated):qk] without a <column> loads as
    #     "The field '[none:Latitude (generated):qk]' in the datasource ... does
    #     not exist in your database" (9CA7205B);
    #   * declaring it as a <column> in the datasource fails the workbook open
    #     entirely ("Errors occurred while trying to load the workbook").
    # Those fields are synthesised by the application, and only when the
    # application itself performs the geography action. The reference viz in this
    # file's docstring turned out to draw its "map" as a background image, so it
    # was no help as a schema source either.
    #
    # Hence: the ADM1 rings ship as rows (stage 4 -> mpi_polygons.csv) and the
    # sheet draws them with a Polygon mark plus a Path field. `ring` keeps a
    # state's disjoint parts from being joined; `point_order` closes each ring.
    #
    # Colour is the *band*, not a continuous ramp: with a median 95% CI width of
    # 0.075 against a median MPI of 0.092, a ramp invites the reader to resolve
    # differences the data cannot support, and all 36 adjacent rank pairs overlap
    # at 95%.
    #
    # The tooltip is customized rather than default, because the default lists
    # every field on the view and ten of those fifteen fields exist only to draw
    # the polygon (pcode, ring, point_order, mpi_se, and the two coordinate axes).
    # A customized tooltip replaces the default list outright, so those stop
    # reaching the reader while staying on the shelves where the drawing needs
    # them. The MPI line explains the index in full and is italic, so the reader
    # does not take its percentage for the headcount share.
    #
    # Tableau drops a <run> whose content is only whitespace, so every run below
    # carries at least one character of text: a line break belongs to the run that
    # starts the next line, never to a run of its own. (Learned the hard way: with
    # the breaks in their own runs, "Other 25" rendered hard against "17.38%".)
    #
    # "Poorest 12" and "Other 25" are labels the extract carries, not sentences, so
    # the tooltip has to finish them: alone they say 12 and 25 *what*. The suffix
    # fits both values unchanged ("Poorest 12 of the 37 states, by MPI" / "Other 25
    # of the 37 states, by MPI"), which is why it is a static run rather than a
    # second column in the extract.
    def map_tooltip_runs() -> str:
        """The runs inside sheet 1's customized tooltip."""
        def fld(column: str, kind: str = "sum", attrs: str = "") -> str:
            return f"              <run{attrs}><![CDATA[<{ref(column, kind, POLY_DS_NAME)}>]]></run>\n"

        def txt(body: str, attrs: str = "") -> str:
            return f"              <run{attrs}>{body}</run>\n"

        return (
            fld("state", "dim", " bold='true' fontsize='13'")
            + txt(" &#183; ")
            + fld("poverty_group", "dim")
            + txt(" of the 37 states, by MPI&#10;Of the population, ")
            + fld("headcount_ratio_pct")
            + txt("% are multidimensionally poor&#10;")
            + txt("Average deprivation among them: ")
            + fld("intensity_pct")
            + txt("% of the things counted&#10;")
            + txt("Poor people: ")
            + fld("mpi_poor_thousands")
            + txt(" thousand&#10;")
            + txt("Governorship 1999&#8211;2021: ")
            + fld("gov_party", "dim")
            + txt("&#10;&#10;MPI ", " bold='true'")
            + fld("mpi_pct", "sum", " bold='true'")
            + txt("%", " bold='true'")
            + txt("  (95% interval ")
            + fld("mpi_ci_lo_pct")
            + txt("% to ")
            + fld("mpi_ci_hi_pct")
            + txt("%)&#10;")
            + txt(
                "MPI is the share of people who are poor multiplied by how deprived "
                "they are, as a percentage of the index.&#10;&#10;",
                " italic='true'",
            )
            + txt(
                "Neighbouring states' intervals overlap, so the map groups states "
                "into bands instead of ranking them.",
                " italic='true'",
            )
        )

    sheet_map = worksheet_xml(
        "Where poverty sits",
        subtitle="MICS 2021 · 5 bands, not 37 ranks · hover for MPI + 95% CI",
        rows=ref("lat", "avg", POLY_DS_NAME),
        cols=ref("lon", "avg", POLY_DS_NAME),
        mark="Polygon",
        encodings=(
            f"            <lod column='{ref('state', 'dim', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('pcode', 'dim', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('ring', 'ord', POLY_DS_NAME)}' />\n"
            f"            <path column='{ref('point_order', 'ord', POLY_DS_NAME)}' />\n"
            f"            <color column='{ref('mpi_band', 'dim', POLY_DS_NAME)}' />\n"
            f"            <text column='{ref('state', 'dim', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('mpi', 'sum', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('mpi_se', 'sum', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('mpi_ci_lo', 'sum', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('mpi_ci_hi', 'sum', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('headcount_ratio_pct', 'sum', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('intensity_pct', 'sum', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('mpi_poor_thousands', 'sum', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('poverty_group', 'dim', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('mpi_pct', 'sum', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('mpi_ci_lo_pct', 'sum', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('mpi_ci_hi_pct', 'sum', POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('gov_party', 'dim', POLY_DS_NAME)}' />\n"
        ),
        ds_name=POLY_DS_NAME,
        ds_caption=POLY_DS_CAPTION,
        deps=poly_deps,
        tooltip=map_tooltip_runs(),
        # Tableau's default polygon border is a hairline, and at the map's size the
        # states read as one field of colour: you cannot see which state the cursor
        # is over. 3px of white is what makes a choropleth readable at this scale.
        #
        # `has-stroke` turns the border on and `stroke-color`/`stroke-size` set it.
        # The obvious-looking `border-color`/`border-width` pair is *inert* here:
        # the workbook loads and renders identically with and without it, at both
        # worksheet and pane scope (checked pixel-for-pixel against a 4x crop,
        # 2026-10-18). `border-*` styles the borders of table cells and headers;
        # a polygon mark's outline is a stroke. Both names are in the published
        # schema's StyleAttribute vocabulary, so the XML validates either way --
        # only rendering tells them apart.
        mark_formats=(("has-stroke", "true"), ("stroke-color", "#FFFFFF"), ("stroke-size", "3")),
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

    # ---- sheet 6: party alignment and MPI change ----------------------------
    # The stage 8 panel: 36 states x 3 intervals, FCT excluded. state on Detail
    # keeps one mark per state-interval; interval is the only colour. Party is
    # never a colour anywhere in this atlas. The result sentence is not repeated
    # here -- it lives in docs/party_alignment.md section 4.
    sheet_align = worksheet_xml(
        ALIGN_SHEET,
        subtitle="36 states x 3 intervals, FCT excluded · pre-registered test, see docs",
        rows=f"[{ALIGN_DS_NAME}].[sum:dmpi_annual:qk]",
        cols=f"[{ALIGN_DS_NAME}].[sum:aligned_share:qk]",
        mark="Circle",
        encodings=(
            f"            <lod column='[{ALIGN_DS_NAME}].[none:state:nk]' />\n"
            f"            <color column='[{ALIGN_DS_NAME}].[none:interval:nk]' />\n"
        ),
        deps=align_deps,
        ds_name=ALIGN_DS_NAME,
        ds_caption=ALIGN_DS_CAPTION,
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
{text_zone}{kpi_zone}          <zone h='51000' id='4' name='Where poverty sits' w='141000' x='0' y='57000' />
          <!-- The map's colour legend, beside the map rather than inside it. A
               dashboard needs its own legend zone: a worksheet's legend card does
               not carry over into the dashboard by itself. Grammar (the attribute
               set and the param shape) is from a real Tableau-authored workbook. -->
          <zone h='51000' id='9' name='Where poverty sits' pane-specification-id='0' param='[federated.0mpipolygons].[none:mpi_band:nk]' show-title='false' type-v2='color' w='19000' x='141000' y='57000' />
          <zone h='51000' id='5' name='Dimension breakdown (three panels, not stacked)' w='58000' x='0' y='16000' />
          <zone h='51000' id='6' name='Poverty vs conflict' w='52000' x='58000' y='16000' />
          <zone h='51000' id='7' name='Incidence vs intensity' w='50000' x='110000' y='16000' />
          <zone h='77000' id='8' name='Poverty over time' w='160000' x='0' y='73000' />
        </zone>
      </zones>
    </dashboard>
{words_dashboard()}{method_dashboard()}  </dashboards>
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
        <edge name='right'>
          <strip size='160'>
            <card pane-specification-id='0' param='[federated.0mpipolygons].[none:mpi_band:nk]' type='color' />
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
    <window class='worksheet' name='Party alignment and MPI change'>
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
        <!-- The map is a geographic sheet, so Tableau draws it at a fixed map
             scale and a small pane crops it. `entire-view` is the dashboard's
             Fit menu stored as data; it is legal grammar (taken from a real
             Tableau-authored workbook) and makes the whole country fit whatever
             size the zone ends up. It is NOT legal on a worksheet window: the
             loader rejects the whole workbook if it is put there. -->
        <viewpoint name='Where poverty sits'>
          <zoom type='entire-view' />
        </viewpoint>
        <viewpoint name='Dimension breakdown (three panels, not stacked)' />
        <viewpoint name='Poverty vs conflict' />
        <viewpoint name='Poverty over time' />
        <viewpoint name='Incidence vs intensity' />
      </viewpoints>
      <active id='-1' />
    </window>
""" + "".join(
        f"    <window class='dashboard' name='{escape(name)}'>\n"
        # The schema wants viewpoints before active, even when there are none.
        "      <viewpoints />\n"
        "      <active id='-1' />\n"
        "    </window>\n"
        for name in READER_DASHBOARDS
    ) + """  </windows>
"""

    # Sheet 1 draws the polygon extract, not the atlas one, so it is kept out of
    # the atlas instance list: a datasource must not declare instances for fields
    # that live in another extract.
    atlas_sheets = " ".join([sheet_bar, sheet_scatter, sheet_quadrant])
    panel_sheets = " ".join([sheet_trend])
    poly_sheets = sheet_map
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
    align_ds = (
        datasource_xml(align_columns, ALIGN_HYPER, align_rows, column_instances(sheet_align))
        .replace(DS_NAME, ALIGN_DS_NAME)
        .replace(CONN_NAME, ALIGN_CONN)
        .replace(f"caption='{DS_CAPTION}'", f"caption='{ALIGN_DS_CAPTION}'", 1)
    )
    poly_ds = (
        datasource_xml(
            POLY_COLUMNS, POLY_HYPER, poly_rows, column_instances(poly_sheets),
            # The colour field's caption is the legend's title text, so it has to
            # say what the reader is looking at -- the internal name "mpi_band"
            # is not that. The full meaning matches the glossary (atlas_text.py).
            captions={
                # The colour field's caption is the legend's title text. A legend
                # strip is 190px wide, so the title must be short: the acronym
                # expanded, not the full sentence. The full meaning lives in the
                # tooltip's italic line, the colour-bar/HTML legend on the HTML
                # map and the glossary.
                "mpi_band": (
                    f"{atlas_text.MPI_LEGEND_TITLE} "
                    f"({atlas_text.MPI_LEGEND_EXPANSION})"
                ),
            },
        )
        .replace(DS_NAME, POLY_DS_NAME)
        .replace(CONN_NAME, POLY_CONN)
        .replace(f"caption='{DS_CAPTION}'", f"caption='{POLY_DS_CAPTION}'", 1)
    )

    return f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook original-version='{VERSION}' source-build='2024.1.0 (20241.24.0212.1000)' source-platform='win' version='{VERSION}' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>
  <datasources>
{atlas_ds}{panel_ds}{align_ds}{poly_ds}  </datasources>
  <worksheets>
{sheet_map}{sheet_bar}{sheet_scatter}{sheet_trend}{sheet_quadrant}{sheet_align}  </worksheets>
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
    for ds in ("[federated.0mpiatlas2021]", "[federated.0mpipanel2021]",
               "[federated.0partyalignment]", "[federated.0mpipolygons]"):
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
    align_path = PROCESSED / "party_alignment_panel.csv"
    poly_path = PROCESSED / "mpi_polygons.csv"
    for p in (atlas_path, panel_path, align_path, poly_path):
        if not p.exists():
            raise SystemExit(f"missing {p}; run scripts/04_merge.py and 08_party_alignment.py first")

    with atlas_path.open(newline="", encoding="utf-8-sig") as fh:
        atlas_reader = list(csv.DictReader(fh))
    with panel_path.open(newline="", encoding="utf-8-sig") as fh:
        panel_reader = list(csv.DictReader(fh))
    with align_path.open(newline="", encoding="utf-8-sig") as fh:
        align_reader = list(csv.DictReader(fh))
    with poly_path.open(newline="", encoding="utf-8-sig") as fh:
        poly_reader = list(csv.DictReader(fh))
    assert len(align_reader) == 108, f"party alignment panel has {len(align_reader)} rows, expected 108"
    # 37 states, one ring each, 53k vertices: a drift here means the geometry or
    # the pcode join changed, and the map would silently lose a state.
    assert {r["pcode"] for r in poly_reader} == {r["pcode"] for r in atlas_reader}, (
        "polygon extract does not cover the same 37 states as the atlas"
    )

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

    align_columns = infer(align_reader, ALIGN_MEASURES, [])
    # The polygon extract is not inferred: `ring` and `point_order` must be
    # integer dimensions (type='ordinal'), not measures, or the Path field
    # resolves to a nonexistent :ok/:nk instance. Types are pinned in POLY_COLUMNS.
    poly_columns = POLY_COLUMNS

    declared = (
        {n for n, _, _ in atlas_columns}
        | {n for n, _, _ in panel_columns}
        | {n for n, _, _ in align_columns}
        | {n for n, _, _ in poly_columns}
    )
    xml = build_workbook(
        atlas_columns, len(atlas_reader), panel_columns, len(panel_reader),
        align_columns, len(align_reader), len(poly_reader),
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    atlas_hyper = OUT_DIR / ATLAS_HYPER
    panel_hyper = OUT_DIR / PANEL_HYPER
    atlas_n = build_hyper(atlas_path, atlas_hyper, atlas_columns)
    panel_n = build_hyper(panel_path, panel_hyper, panel_columns)
    align_hyper = OUT_DIR / ALIGN_HYPER
    align_n = build_hyper(align_path, align_hyper, align_columns)
    poly_hyper = OUT_DIR / POLY_HYPER
    poly_n = build_hyper(poly_path, poly_hyper, poly_columns)

    problems = validate(xml, declared)
    problems += check_hyper_schema(
        [
            (ATLAS_HYPER, atlas_hyper, atlas_columns),
            (PANEL_HYPER, panel_hyper, panel_columns),
            (ALIGN_HYPER, align_hyper, align_columns),
            (POLY_HYPER, poly_hyper, poly_columns),
        ],
        {
            ATLAS_HYPER: atlas_n,
            PANEL_HYPER: panel_n,
            ALIGN_HYPER: align_n,
            POLY_HYPER: poly_n,
        },
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
        zf.write(align_hyper, f"Data/{ALIGN_HYPER}")
        zf.write(poly_hyper, f"Data/{POLY_HYPER}")

    print(f"XML validated: {len(declared)} columns declared, all field references resolve")
    print(
        f"Extracts validated: {ATLAS_HYPER} ({atlas_n} rows), "
        f"{PANEL_HYPER} ({panel_n} rows), {ALIGN_HYPER} ({align_n} rows), "
        f"{POLY_HYPER} ({poly_n} rows) match the declared columns"
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