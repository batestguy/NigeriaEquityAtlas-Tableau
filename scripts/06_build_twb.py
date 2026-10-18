"""Stage 6 -- generate a Tableau workbook (.twb) and package it as a .twbx.

What is generated, and why it is deliberately lean
---------------------------------------------------
Hand-authored Tableau XML is written to a schema taken from real, published
Tableau-authored workbooks downloaded and unpacked via the Tableau MCP server
(``ClimatechangeprofileNigeria`` first; later, for the colour-palette grammar,
``Ode to Cowbell`` and ``Clinic Performance Dashboard``), and every column
reference it emits is verified against the columns it declares. It is also opened
in Tableau Public 2026.2 and looked at, which is the only check that catches a
defect the schema accepts.

The datasource is a Hyper extract written by `tableauhyperapi` and packaged inside
the .twbx (see the corrections list in AGENTS.md, #6): Tableau Public refuses a
workbook whose datasource is not an extract. That is the lowest-risk option --
nothing to refresh, since the MPI survey updates annually -- and it is the only one
Tableau Public accepts at all.

Sheet inventory
---------------
  1  Where poverty sits            filled choropleth, Polygon + Path from shipped
                                   ADM1 rings; five assigned band colours
  2  Where poverty clusters        the same rings drawn again, filled by the
                                   neighbourhood type (whether a state and the
                                   states it borders are on the same side of the
                                   national average), with the four assigned
                                   type colours and the pre-registered spatial
                                   result in the hover
  3  What the words mean           reference table, part 1 of 3: the 24 words
  4  The list of basic needs       reference table, part 2 of 3: the 11 needs
  5  How we did it                 reference table, part 3 of 3: the 9 steps

  The three reference tabs are one table cut into its own three groups, because
  rendered as a single dashboard it measured 2000 x 8720 px -- thirteen screens on
  the window it was reviewed in. Each part repeats the intro and the column headers
  so it stands alone; the columns are the word with its formula or weight, what it
  means, and how it was made. They are text zones, not a datasource: see the note
  above `table_dashboards` for why a real Tableau text table was not available.

What is *not* here, and why: this workbook used to carry five more chart sheets
(dimension breakdown, poverty vs conflict, poverty over time, incidence vs
intensity, party alignment) plus the Moran scatter, the "Equity Atlas" dashboard
and an offline HTML map built by stage 7. The user withdrew all of them on
2026-10-18 -- "I only care about MPI bands we built and the [spatial] sheet" -- and
they are recoverable from git. The analyses behind them did not go: stages 02, 03
and 08 still run, because the party test is pre-registered and its result, the
conflict undercount and the climate overlap are the evidence behind the sentences
the reference tabs now carry.
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
from common import PROCESSED, REPO_ROOT, spatial_context_line

OUT_DIR = REPO_ROOT / "tableau"
VERSION = "18.1"


def ref(column: str, kind: str, ds: str) -> str:
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
    # Captions go into a single-quoted attribute, so quotes have to be escaped and
    # not just &/</>. A caption containing an apostrophe -- "this state's poverty"
    # -- otherwise produces well-formed-looking markup that fails to parse
    # ("invalid token"), and the whole workbook fails to build for a comma.
    quoted = {chr(34): "&quot;", chr(39): "&apos;"}
    cap = (
        f" caption='{escape(caption, quoted)}'" if caption
        else f" caption='{escape(name)}'"
    )
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


def palette_block(field: str, entries: list[tuple[str, str]]) -> str:
    """The datasource's colour-palette style rule: one colour per member.

    A discrete field on Colour gets Tableau's *default categorical* palette unless
    the workbook assigns one, so an ordered five-band scale would be drawn in five
    unrelated hues -- colour that carries no order on a map whose whole claim is
    that poverty rises. This is the block that fixes that.

    The grammar is copied from two real Tableau-authored Public workbooks
    (``Ode to Cowbell``, ``Clinic Performance Dashboard``, both downloaded via the
    Tableau MCP server), where it sits *inside the <datasource>*, between
    ``<layout .../>`` and ``<semantic-values>`` -- which is exactly where the two
    elements already sit here. Two details are not guessable:

    * the field is named **without** its datasource prefix (``[none:mpi_band:nk]``,
      not ``[federated.0mpipolygons].[none:mpi_band:nk]``);
    * a string member is written as a quoted ``<bucket>``, with the quotes escaped
      as ``&quot;`` -- the bucket holds the *data value*, the same string the
      extract stores.

    ``type='palette'`` is the discrete form. The continuous form is a sibling of
    this one (``type='interpolated'``, or ``type='custom-interpolated'`` with a
    nested ``<color-palette>`` of hex stops and a ``max`` attribute); it does not
    apply to a nominal dimension.
    """
    maps = "".join(
        f"            <map to='{colour}'>\n"
        f"              <bucket>{escape(chr(34) + label + chr(34), {chr(34): '&quot;', chr(39): '&apos;'})}</bucket>\n"
        f"            </map>\n"
        for label, colour in entries
    )
    return (
        "      <style>\n"
        "        <style-rule element='mark'>\n"
        f"          <encoding attr='color' field='[none:{escape(field)}:nk]' type='palette'>\n"
        f"{maps}"
        "          </encoding>\n"
        "        </style-rule>\n"
        "      </style>\n"
    )


def datasource_xml(columns: list[tuple[str, str, str]], hyper_filename: str, row_count: int,
                   ds_name: str, ds_caption: str, conn_name: str,
                   instances: str = "",
                   palette: tuple[str, list[tuple[str, str]]] | None = None,
                   captions: dict[str, str] | None = None) -> str:
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

    The name, caption and connection name are arguments, not a base string that
    callers then rewrite. They used to be: one template datasource was built and
    ``str.replace``d per surface. That worked for six of them, but it meant an
    accidental shared caption opened as a UniqueDataSource error. With two
    surfaces the indirection is pure risk, so each one states its own identity.
    """
    captions = captions or {}
    cols = []
    for name, datatype, role in columns:
        cols.append(col_block(name, datatype, role, geographic=(name == "state"),
                              caption=captions.get(name, "")))

    col_blocks = "".join(cols)
    dbname = f"Data/{hyper_filename}"
    palette_rule = palette_block(*palette) if palette else ""
    return f"""    <datasource caption='{escape(ds_caption)}' inline='true' name='{ds_name}' version='{VERSION}'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='Extract' name='{conn_name}'>
            <connection access_mode='readonly' author-locale='en' class='hyper' dbname='{dbname}' default-settings='hyper' schema='Extract' sslmode='' tablename='Extract'>
              <relation name='Extract' table='[Extract].[Extract]' type='table' />
            </connection>
          </named-connection>
        </named-connections>
        <relation connection='{conn_name}' name='Extract' table='[Extract].[Extract]' type='table' />
      </connection>
      <aliases enabled='yes' />
{col_blocks}{instances}      <extract count='-1' enabled='true' units='records'>
        <connection access_mode='readonly' author-locale='en' class='hyper' dbname='{dbname}' default-settings='hyper' schema='Extract' sslmode='' tablename='Extract'>
          <relation name='Extract' table='[Extract].[Extract]' type='table' />
        </connection>
      </extract>
      <layout dim-ordering='alphabetic' dim-percentage='0.5' measure-ordering='alphabetic' measure-percentage='0.4' show-structure='true' />
{palette_rule}      <semantic-values>
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


def deps_xml(columns: list[tuple[str, str, str]],
             captions: dict[str, str] | None = None) -> str:
    """The per-worksheet column block real Tableau writes.

    Tableau repeats the datasource's columns inside every worksheet that uses it
    (<datasource-dependencies>). The matching <column-instance> elements are added
    by worksheet_xml, which can see which fields the shelves actually reference.

    ``captions`` must be the same map the datasource was built with. Tableau writes
    a field's caption in both places, and a workbook whose worksheet copies disagree
    with its datasource is a state Tableau never produces itself; which of the two
    the shelf pill and the colour legend read is not established here, so the two
    are made to agree rather than argued about.
    """
    captions = captions or {}
    body = "".join(
        col_block(name, datatype, role, geographic=(name == "state"),
                  caption=captions.get(name, ""))
        for name, datatype, role in columns
    )
    return f"""          <datasource-dependencies>
{body}          </datasource-dependencies>
"""


def worksheet_xml(name: str, *, rows: str, cols: str, mark: str = "Automatic",
                  encodings: str = "", ds_name: str, ds_caption: str,
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


# --- The cluster map's extract (stage 9, spatial_polygons.csv) -----------------
# Sheet 1's geometry, joined to the four neighbourhood types: the map draws the same
# rings the poverty map draws, with `spatial_group` as the fill. A separate extract
# rather than extra columns on mpi_polygons.csv because stage 4 owns that file and
# runs before stage 9 exists -- appending there would make a stage-4 artifact depend
# on a later stage. Column order is POLY_COLUMNS with the spatial fields appended, in
# the order stage 9 writes them (POLY_SPATIAL_FIELDS).
SPATIAL_POLY_DS_NAME = "federated.0mpispatialpoly"
SPATIAL_POLY_DS_CAPTION = "Spatial polygons"
SPATIAL_POLY_CONN = "hyper.0mpispatialpoly"
SPATIAL_POLY_HYPER = "spatial_polygons.hyper"
SPATIAL_POLY_COLUMNS: list[tuple[str, str, str]] = POLY_COLUMNS + [
    ("spatial_group", "string", "dimension"),
    ("spatial_lag_mpi_pct", "real", "measure"),
    ("neighbours", "integer", "measure"),
]


# --- The reference tab: plain-language text from scripts/atlas_text.py ---------
# One tab where two prose pages used to be ("What the words mean", "How we did it"):
# a table three columns wide, one row per word, per basic need and per worked step.
# The words live in atlas_text.py and are never retyped here -- this code arranges
# them, so the table cannot drift from the prose it replaced.
#
# Why a grid of text zones and not a Tableau text table: a real multi-column table
# needs the Measure Names / Measure Values pair and its <measure-values> filter,
# which this project tried and could not make render from hand-written XML (the note
# inside the old dimension-breakdown sheet recorded that failure). Text zones are
# grammar this workbook has shipped since the first reader dashboards were added, so
# the table is built from what is already proven in the application. The cost is
# that it is a layout, not a datasource: nothing in it is selectable or exportable.

TABLE_WIDTH = 2000       # px; fixed size, tall rather than clipped
TABLE_GAP = 12           # px between rows
TABLE_PAD = 30           # px of slack at the foot of the dashboard
# Column shares of the width: the word and its formula, what it means, how it was
# made. The first is narrowest because it is the column a reader scans.
TABLE_COLUMNS: list[float] = [0.24, 0.38, 0.38]
# Background fills for the header row and the group bands. This attribute is the one
# piece of grammar here that has not been seen in a Tableau-authored workbook: if the
# application ignores it the table still reads, and a load failure with it present is
# the first thing to bisect.
HEADER_FILL = "#e8ecf1"
GROUP_FILL = "#f2f4f7"
CELL_MARGIN = 14

TEXT_COLOUR = "#22252a"
FORMULA_COLOUR = "#5b6270"
HEADER_SIZE = 12
GROUP_SIZE = 15
BODY_SIZE = 11
TERM_SIZE = 11
HEADING_SIZE = 14
TITLE_SIZE = 20
# Tableau marks a paragraph break inside formatted text with this pair.
PARA_BREAK = "Æ&#10;"

# A paragraph is a list of (text, bold, fontsize, italic) runs that share one line.
Run = tuple[str, bool, int, bool]


def para(text: str, *, bold: bool = False, size: int = BODY_SIZE,
         italic: bool = False) -> list[Run]:
    return [(text, bold, size, italic)]


def _run_xml(text: str, bold: bool, size: int, italic: bool,
             colour: str = TEXT_COLOUR) -> str:
    weight = " bold='true'" if bold else ""
    slant = " italic='true'" if italic else ""
    return (f"<run{weight}{slant} fontcolor='{colour}' fontsize='{size}'>"
            f"{escape(text)}</run>")


def _estimate_height(paragraphs: list[list[Run]], width_px: int) -> int:
    """Rendered height in px, sized for the worst case so nothing is clipped.

    Calibrated against the render, not by eye. Loading the built workbook in Tableau
    Public 2026.2 on 2026-10-18 (a 2000px table, 11pt body) showed the width model is
    right and the height model was one line short: a 480px cell held 41 characters per
    line and a 760px cell 68, exactly what ``(width - padding) / (size * 0.95)``
    predicts, but the first version counted only the text and not the zone's own
    vertical margin, so every cell that wrapped was ellipsized by Tableau -- which
    truncates the last line rather than growing the zone. The padding is now part of
    the estimate, in both directions, from one constant.

    Tableau renders 11pt type at ~30.8px per line in this application and smaller on
    the web, so the published table has slack rather than a stranger's font deciding
    whether a row fits.
    """
    import math

    padding = 2 * CELL_MARGIN + 12  # the zone's margin, plus Tableau's own inset
    height = float(padding)
    for runs in paragraphs:
        size = max(r[2] for r in runs)
        chars_per_line = max(1, int((width_px - padding) / (size * 0.95)))
        chars = sum(len(r[0]) for r in runs) * 1.08  # word-wrap waste
        lines = max(1, math.ceil(chars / chars_per_line))
        height += lines * size * 2.8
    return int(height)


def text_zone(zone_id: int, *, x: int, y: int, w: int, h: int,
              paragraphs: list[list[Run]], background: str = "") -> str:
    """One text zone. Geometry is in 1/100000ths of the dashboard, Tableau's unit."""
    body = f"<run fontsize='{BODY_SIZE}'>{PARA_BREAK}</run>".join(
        "".join(_run_xml(*r) for r in runs) for runs in paragraphs
    )
    fill = (f"              <format attr='background-color' value='{background}' />\n"
            if background else "")
    return (
        f"          <zone h='{h}' id='{zone_id}' type-v2='text' w='{w}' x='{x}' y='{y}'>\n"
        f"            <formatted-text>{body}</formatted-text>\n"
        "            <zone-style>\n"
        f"              <format attr='margin' value='{CELL_MARGIN}' />\n"
        f"{fill}"
        "            </zone-style>\n"
        "          </zone>\n"
    )


def table_dashboards() -> list[tuple[str, str]]:
    """The reference table, in three parts: one dashboard per content group.

    It was a single dashboard until the render test of 2026-10-18 measured it at
    2000 x 8720 px -- thirteen screens on the 687 px window it was reviewed in, and
    not a tab anyone reads top to bottom. The split is the table's own: its three
    groups are already the words, the list of basic needs and the method, so each part
    is a complete three-column table and no row had to be re-cut. The cost is
    repetition -- the intro and the column headers now appear on three tabs -- which
    for a reference work is the right trade.

    Each part's first band carries the shared intro, the part's position in the set,
    and the group's own introduction, so a reader who arrives on part 3 from the tab
    bar is told what the columns are without going back to part 1.
    """
    px = TABLE_WIDTH
    widths = [round(px * share) for share in TABLE_COLUMNS]
    lefts = [round(sum(widths[:i])) for i in range(len(widths))]
    groups = atlas_text.table_rows()
    dashboards: list[tuple[str, str]] = []

    for part, (heading, intro, rows) in enumerate(groups, 1):
        # A spec is (kind, cells): "wide" is one cell spanning the table, "row" is one
        # cell per column. A cell is a list of paragraphs, a paragraph a list of runs.
        specs: list[tuple[str, list[list[list[Run]]]]] = [
            ("wide", [[
                para(atlas_text.TABLE_INTRO),
                para(" "),
                para(f"Part {part} of {len(groups)} \u00b7 {heading}",
                     bold=True, size=GROUP_SIZE),
                para(intro),
            ]]),
            ("row", [[para(header, bold=True, size=HEADER_SIZE)]
                     for header in atlas_text.TABLE_HEADERS]),
        ]
        for row in rows:
            specs.append(("row", [
                [para(row["word"], bold=True, size=TERM_SIZE),
                 para(row["formula"], italic=True)],
                [para(row["meaning"])],
                [para(row["method"])],
            ]))

        heights = [
            _estimate_height(cells[0], px) if kind == "wide"
            else max(_estimate_height(cell, widths[i]) for i, cell in enumerate(cells))
            for kind, cells in specs
        ]
        total = sum(heights) + TABLE_GAP * len(specs) + TABLE_PAD

        def sy(value: float, _total: int = total) -> int:
            return round(value * 100000 / _total)

        def sx(value: float, _px: int = px) -> int:
            return round(value * 100000 / _px)

        header_at = 1  # the column headers are the second spec
        # Zone ids only have to be unique within a dashboard, but the parts get
        # disjoint ranges anyway so a zone id in a log names one tab and not three.
        ids = iter(range(200 + 100 * part, 300 + 100 * part))
        zones: list[str] = []
        y = 0.0
        for index, ((kind, cells), height) in enumerate(zip(specs, heights)):
            if kind == "wide":
                zones.append(text_zone(
                    next(ids), x=0, y=sy(y), w=100000, h=sy(height),
                    paragraphs=cells[0], background=GROUP_FILL,
                ))
            else:
                for i, cell in enumerate(cells):
                    zones.append(text_zone(
                        next(ids), x=sx(lefts[i]), y=sy(y), w=sx(widths[i]),
                        h=sy(height), paragraphs=cell,
                        background=HEADER_FILL if index == header_at else "",
                    ))
            y += height + TABLE_GAP

        dashboards.append((heading, f"""    <dashboard name='{escape(heading)}'>
      <layout-options>
        <title>
          <formatted-text>
            <run bold='true' fontsize='16'>{escape(heading)}</run>
            <run fontsize='10'>  {escape(atlas_text.TABLE_TITLE)}, part {part} of {len(groups)}</run>
          </formatted-text>
        </title>
      </layout-options>
      <style />
      <size maxheight='{total}' maxwidth='{px}' minheight='{total}' minwidth='{px}' />
      <zones>
        <zone h='100000' id='{190 + part}' type-v2='layout-basic' w='100000' x='0' y='0'>
{"".join(zones)}        </zone>
      </zones>
    </dashboard>
"""))
        print(f"  reference tab {part} of {len(groups)}: {heading} -- {px}px wide x "
              f"{total}px tall, {len(rows)} rows / {len(zones)} zones")

    return dashboards


def build_workbook(spatial_technical: str,
                   poly_rows: int, spatial_poly_rows: int) -> str:
    """The workbook: two maps drawn from the same rings, and the reference table.

    Two extracts, two datasources. The atlas, trends-panel, party-alignment and
    spatial-diagnostic extracts were withdrawn on 2026-10-18 with the sheets that
    drew them (module docstring), so those four hyper files are neither built nor
    packaged any more.
    """
    # The colour field's caption is the legend's title text, so it has to say what
    # the reader is looking at -- the internal name "mpi_band" is not that. A legend
    # strip is 190px wide, so the title is the acronym expanded, not the full
    # sentence; the full meaning is in the tooltip's italic line and in the reference
    # tab, both from atlas_text.
    #
    # One map, two places: Tableau writes the caption on the datasource <column>
    # AND repeats it in every worksheet's <datasource-dependencies>, so both are
    # built from this dict. Built separately, they silently disagree.
    poly_captions = {
        "mpi_band": (
            f"{atlas_text.MPI_LEGEND_TITLE} ({atlas_text.MPI_LEGEND_EXPANSION})"
        ),
    }
    poly_deps = deps_xml(POLY_COLUMNS, poly_captions)

    # The cluster map's caption also has to say what is being compared: a field
    # captioned "Neighbourhood type" alone invites a reading about people moving.
    spatial_poly_captions = {
        "spatial_group": (
            f"{atlas_text.SPATIAL_LEGEND_TITLE} ({atlas_text.SPATIAL_LEGEND_MEANING})"
        ),
        # Not on a shelf, but a caption is also what the field reads as in the
        # datasource pane, and `spatial_lag_mpi_pct` is unreadable there.
        "mpi_pct": atlas_text.SPATIAL_FIELD_OWN,
        "spatial_lag_mpi_pct": atlas_text.SPATIAL_FIELD_NEIGHBOURS,
        "neighbours": "Number of states it borders",
    }
    spatial_poly_deps = deps_xml(SPATIAL_POLY_COLUMNS, spatial_poly_captions)

    # ---- the cluster map's tooltip ------------------------------------------
    # The same per-state numbers the poverty map's hover carries, plus the four
    # frozen reader lines from the pre-registered spatial test (stage 9) and the
    # technical footer. The paragraph that says how to read *this* surface is a
    # parameter, because it used to be shared with the Moran scatter, which was
    # withdrawn on 2026-10-18; the frozen lines and the footer stay single-sourced.
    def spatial_tooltip_runs(ds: str, reading: str) -> str:
        """The runs inside a spatial sheet's customized tooltip."""

        def fld(column: str, kind: str = "sum", attrs: str = "") -> str:
            return f"              <run{attrs}><![CDATA[<{ref(column, kind, ds)}>]]></run>\n"

        def txt(body: str, attrs: str = "") -> str:
            return f"              <run{attrs}>{body}</run>\n"

        return (
            fld("state", "dim", " bold='true' fontsize='13'")
            + txt(" &#183; ")
            + fld("spatial_group", "dim")
            + txt("&#10;")
            + txt("Poverty score: ", " bold='true'")
            + fld("mpi_pct", "sum", " bold='true'")
            + txt("%", " bold='true'")
            + txt("&#10;Average of the ")
            + fld("neighbours")
            + txt(" states it borders: ")
            + fld("spatial_lag_mpi_pct")
            + txt("%&#10;&#10;")
            + txt(reading + "&#10;&#10;", " italic='true'")
            + txt(atlas_text.SPATIAL_READING_HEADING + "&#10;", " bold='true'")
            + txt(escape(" ".join(atlas_text.SPATIAL_READER_LINES)))
            + txt("&#10;")
            + txt(escape(atlas_text.SPATIAL_NO_CAUSE) + "&#10;", " italic='true'")
            + txt("Technical details&#10;", " bold='true'")
            + txt(escape(spatial_technical))
        )

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
    # at 95%. The five colours are assigned to the five members in the datasource's
    # palette rule (see palette_block) -- without it a nominal field draws in
    # Tableau's default categorical palette, which encodes no order at all.
    #
    # The tooltip is customized rather than default, because the default lists
    # every field on the view and ten of those fifteen fields exist only to draw
    # the polygon (pcode, ring, point_order, and the two coordinate axes). A
    # customized tooltip replaces the default list outright, so those stop
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

    # ---- sheet 1b: the cluster map, immediately after the poverty map -------
    # The same rings, drawn again with the neighbourhood type as the fill. It is not a
    # second poverty map: `spatial_group` says whether a state and the states it
    # borders are on the same side of the national average, which is a statement about
    # the map's pattern and not about how poor anywhere is. The four colours are the
    # purple/teal set from atlas_text.SPATIAL_QUADRANTS, deliberately not the
    # cream-to-brown poverty ramp.
    #
    # What this sheet must NOT do is colour by significance. Only one state survives the
    # correction and none survives Benjamini-Yekutieli (docs/spatial_analysis.md s3), so
    # a significance map would be a single state on a field of grey -- and it would
    # invite the reader to name that state as "the poorest cluster", which is exactly
    # the per-state ordering the atlas withdrew (docs/FIX_LEDGER.md A1). The count is in
    # the hover instead, where it is a number and not a place.
    sheet_cluster = worksheet_xml(
        atlas_text.SPATIAL_MAP_TITLE,
        subtitle=atlas_text.SPATIAL_MAP_SUBTITLE,
        rows=ref("lat", "avg", SPATIAL_POLY_DS_NAME),
        cols=ref("lon", "avg", SPATIAL_POLY_DS_NAME),
        mark="Polygon",
        encodings=(
            f"            <lod column='{ref('state', 'dim', SPATIAL_POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('pcode', 'dim', SPATIAL_POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('ring', 'ord', SPATIAL_POLY_DS_NAME)}' />\n"
            f"            <path column='{ref('point_order', 'ord', SPATIAL_POLY_DS_NAME)}' />\n"
            f"            <color column='{ref('spatial_group', 'dim', SPATIAL_POLY_DS_NAME)}' />\n"
            f"            <text column='{ref('state', 'dim', SPATIAL_POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('mpi_pct', 'sum', SPATIAL_POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('spatial_lag_mpi_pct', 'sum', SPATIAL_POLY_DS_NAME)}' />\n"
            f"            <lod column='{ref('neighbours', 'sum', SPATIAL_POLY_DS_NAME)}' />\n"
        ),
        ds_name=SPATIAL_POLY_DS_NAME,
        ds_caption=SPATIAL_POLY_DS_CAPTION,
        deps=spatial_poly_deps,
        tooltip=spatial_tooltip_runs(SPATIAL_POLY_DS_NAME, atlas_text.SPATIAL_MAP_READING),
        # The same white strokes sheet 1 carries, so the country reads as the same
        # country drawn twice rather than as two different maps of two different places.
        mark_formats=(("has-stroke", "true"), ("stroke-color", "#FFFFFF"), ("stroke-size", "3")),
    )

    # ---- sheets 3-5: the reference tab, in three parts ----------------------
    # Where the five spec sheets (dimension breakdown, poverty vs conflict, poverty
    # over time, incidence x intensity) and the party-alignment panel used to be.
    # All of them, the Moran scatter and the "Equity Atlas" dashboard were withdrawn
    # on 2026-10-18 (module docstring). Their numbers still exist -- stages 04, 05
    # and 08 write them, and docs/ carries the two pre-registered results -- and
    # every sentence a reader needs from those five sheets is now a row of this
    # table, which is why withdrawing them cost the atlas no claim.
    reference_tabs = table_dashboards()

    dashboards = "  <dashboards>\n" + "".join(
        xml for _name, xml in reference_tabs
    ) + "  </dashboards>\n"
    # One window per part, in the same order, so the tab bar reads words -> needs ->
    # method. Each needs its own <window>: a dashboard with no window is not shown at
    # all, and a dashboard whose window is missing loads as a blank tab.
    tab_windows = "".join(
        f"""    <window class='dashboard' name='{escape(name)}'>
      <viewpoints />
      <active id='-1' />
    </window>
"""
        for name, _xml in reference_tabs
    )

    # Window order is tab order when the workbook opens, and it is the order the
    # three surfaces are meant to be read in: where poverty sits, where it clusters,
    # then the words that explain both.
    windows = f"""  <windows source-height='1500'>
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
        <!-- The colour legend is declared here and in the dashboard. Declared, not
             drawn: with this window card in place the legend still does not render in
             Tableau Public 2026.2, while removing the Marks card from the same strip
             does remove it from the UI, so the strip itself is honoured. One click
             turns it on (Analysis, then Legends, then Colour Legend, then Save), and
             docs/PUBLISH.md carries the step. -->
        <edge name='right'>
          <strip size='160'>
            <card pane-specification-id='0' param='[federated.0mpipolygons].[none:mpi_band:nk]' type='color' />
          </strip>
        </edge>
      </cards>
    </window>
    <window class='worksheet' name='{escape(atlas_text.SPATIAL_MAP_TITLE)}'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='right'>
          <strip size='160'>
            <card pane-specification-id='0' param='[federated.0mpispatialpoly].[none:spatial_group:nk]' type='color' />
          </strip>
        </edge>
      </cards>
    </window>
{tab_windows}  </windows>
"""

    # Two extracts, two datasources, and each declares the instances of its own
    # sheet only: a datasource must not declare an instance for a field that lives
    # in the other extract (it loads as "the field does not exist", 9CA7205B).
    poly_ds = datasource_xml(
        POLY_COLUMNS, POLY_HYPER, poly_rows, POLY_DS_NAME, POLY_DS_CAPTION, POLY_CONN,
        instances=column_instances(sheet_map),
        captions=poly_captions,
        # The ordered ramp for the five bands. A nominal dimension defaults to
        # Tableau's categorical palette, which draws an ordered poverty scale in
        # five unrelated hues; this palette rule is the only way to assign colours
        # from XML. The colours come from atlas_text.MPI_BANDS, so the workbook's
        # fill and the matplotlib QA gate cannot drift apart.
        palette=("mpi_band", list(atlas_text.MPI_BANDS)),
    )
    spatial_poly_ds = datasource_xml(
        SPATIAL_POLY_COLUMNS, SPATIAL_POLY_HYPER, spatial_poly_rows,
        SPATIAL_POLY_DS_NAME, SPATIAL_POLY_DS_CAPTION, SPATIAL_POLY_CONN,
        instances=column_instances(sheet_cluster),
        captions=spatial_poly_captions,
        # The same assignment for the cluster map's four neighbourhood types, for
        # the same reason: without it a nominal field draws in Tableau's default
        # categorical scheme, and these four are a designed set, not arbitrary hues.
        palette=(
            "spatial_group",
            [(words, colour) for _code, words, colour in atlas_text.SPATIAL_QUADRANTS],
        ),
    )

    return f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook original-version='{VERSION}' source-build='2024.1.0 (20241.24.0212.1000)' source-platform='win' version='{VERSION}' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>
  <datasources>
{poly_ds}{spatial_poly_ds}  </datasources>
  <worksheets>
{sheet_map}{sheet_cluster}  </worksheets>
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

    # A Python escape that reached the file instead of being interpreted is still
    # well-formed XML, so the parser cannot catch it: a literal backslash-n shipped in
    # <dashboards> once and Tableau's only complaint was D2E8DA72, "the load was not
    # able to complete", with nothing in the log naming the element. Text in this
    # workbook never needs one, so an occurrence is a build error, not a document.
    for escape_seq in ("\\n", "\\t", "\\u"):
        if escape_seq in xml:
            problems.append(
                f"the XML text contains a literal {escape_seq!r}; a Python escape was "
                "not interpreted (Tableau reports this only as a load failure)"
            )

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
    for ds in ("[federated.0mpipolygons]", "[federated.0mpispatialpoly]"):
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
    poly_path = PROCESSED / "mpi_polygons.csv"
    spatial_path = PROCESSED / "spatial_diagnostics.csv"
    spatial_poly_path = PROCESSED / "spatial_polygons.csv"
    spatial_global_path = PROCESSED / "spatial_global.csv"
    for path in (atlas_path, poly_path, spatial_path, spatial_poly_path,
                 spatial_global_path):
        if not path.exists():
            raise SystemExit(
                f"missing {path}; run scripts/04_merge.py and "
                "scripts/09_spatial_diagnostics.py first"
            )

    def read(path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))

    atlas_reader = read(atlas_path)
    poly_reader = read(poly_path)
    spatial_reader = read(spatial_path)
    spatial_poly_reader = read(spatial_poly_path)
    spatial_global = read(spatial_global_path)

    # The atlas table is drawn by no sheet any more, but it stays the reference both
    # maps are checked against: it is the source of the band labels, and its 37
    # pcodes are what proves each extract covers the whole country.
    assert len(atlas_reader) == 37, f"atlas has {len(atlas_reader)} rows, expected 37"
    atlas_pcodes = {r["pcode"] for r in atlas_reader}
    assert len(spatial_reader) == 37, (
        f"spatial table has {len(spatial_reader)} rows, expected 37"
    )
    assert {r["pcode"] for r in spatial_reader} == atlas_pcodes, (
        "the spatial table does not cover the same 37 states as the atlas"
    )

    # The four neighbourhood types are drawn from a fixed set of colours and
    # explained in fixed words. A value in the data that is not on that list would
    # draw in the default categorical colour with no legend entry, and the words in
    # the tooltip would describe a fifth type nobody defined.
    known_types = {words for _code, words, _colour in atlas_text.SPATIAL_QUADRANTS}
    assert len({colour for _c, _w, colour in atlas_text.SPATIAL_QUADRANTS}) == len(
        atlas_text.SPATIAL_QUADRANTS
    ), "atlas_text.SPATIAL_QUADRANTS repeats a colour; the four types must be distinct"
    found_types = {r["spatial_group"] for r in spatial_reader}
    assert found_types <= known_types, (
        "neighbourhood types missing from atlas_text.SPATIAL_QUADRANTS: "
        f"{sorted(found_types - known_types)}"
    )
    # 37 states, one ring each, tens of thousands of vertices: a drift here means the
    # geometry or the pcode join changed, and the map would silently lose a state.
    assert {r["pcode"] for r in poly_reader} == atlas_pcodes, (
        "polygon extract does not cover the same 37 states as the atlas"
    )
    # The cluster map draws the rings again, so it must carry the same geometry in the
    # same order -- a half-joined polygon table would draw states with no fill at all.
    assert len(spatial_poly_reader) == len(poly_reader), (
        f"the cluster map's extract has {len(spatial_poly_reader)} vertices but the map "
        f"draws {len(poly_reader)}; the two must be the same geometry"
    )
    assert [r["point_order"] for r in spatial_poly_reader] == [
        r["point_order"] for r in poly_reader
    ], "the cluster map's extract is not the polygon table in the same order"
    for row, source in zip(spatial_poly_reader, poly_reader):
        if (row["pcode"], row["ring"], row["lon"], row["lat"]) != (
            source["pcode"], source["ring"], source["lon"], source["lat"]
        ):
            raise AssertionError("the cluster map's geometry drifted from the polygon table")
    assert {r["pcode"] for r in spatial_poly_reader} == atlas_pcodes, (
        "the cluster map's extract does not cover the same 37 states as the atlas"
    )
    found_poly_types = {r["spatial_group"] for r in spatial_poly_reader}
    assert found_poly_types <= known_types, (
        "neighbourhood types missing from atlas_text.SPATIAL_QUADRANTS: "
        f"{sorted(found_poly_types - known_types)}"
    )
    assert found_poly_types == found_types, (
        "the two spatial extracts disagree about which neighbourhood types exist: "
        f"{sorted(found_poly_types ^ found_types)}"
    )
    # The workbook's palette and the stage 5 preview map are both built from
    # atlas_text.MPI_BANDS. A band value not on that list would draw in the default
    # categorical colour with no legend entry, and nothing else would complain.
    known_bands = {label for label, _ in atlas_text.MPI_BANDS}
    found_bands = {r["mpi_band"] for r in atlas_reader}
    assert found_bands <= known_bands, (
        f"mpi_band values missing from atlas_text.MPI_BANDS: {sorted(found_bands - known_bands)}"
    )
    assert len({colour for _, colour in atlas_text.MPI_BANDS}) == len(atlas_text.MPI_BANDS), (
        "atlas_text.MPI_BANDS repeats a colour; the ramp must step monotonically"
    )

    declared = (
        {name for name, _type, _role in POLY_COLUMNS}
        | {name for name, _type, _role in SPATIAL_POLY_COLUMNS}
    )
    xml = build_workbook(
        spatial_context_line(spatial_global), len(poly_reader), len(spatial_poly_reader),
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    poly_hyper = OUT_DIR / POLY_HYPER
    poly_n = build_hyper(poly_path, poly_hyper, POLY_COLUMNS)
    spatial_poly_hyper = OUT_DIR / SPATIAL_POLY_HYPER
    spatial_poly_n = build_hyper(spatial_poly_path, spatial_poly_hyper, SPATIAL_POLY_COLUMNS)

    problems = validate(xml, declared)
    problems += check_hyper_schema(
        [
            (POLY_HYPER, poly_hyper, POLY_COLUMNS),
            (SPATIAL_POLY_HYPER, spatial_poly_hyper, SPATIAL_POLY_COLUMNS),
        ],
        {
            POLY_HYPER: poly_n,
            SPATIAL_POLY_HYPER: spatial_poly_n,
        },
    )
    if problems:
        print("WORKBOOK VALIDATION FAILED")
        for problem in problems:
            print("  -", problem)
        return 1

    twb_path = OUT_DIR / "Nigeria-MPI-Equity-Atlas.twb"
    twb_path.write_text(xml, encoding="utf-8")

    twbx_path = OUT_DIR / "Nigeria-MPI-Equity-Atlas.twbx"
    with zipfile.ZipFile(twbx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(twb_path, twb_path.name)
        # The .twb references the extracts relative to the package root.
        zf.write(poly_hyper, f"Data/{POLY_HYPER}")
        zf.write(spatial_poly_hyper, f"Data/{SPATIAL_POLY_HYPER}")

    print(f"XML validated: {len(declared)} columns declared, all field references resolve")
    print(
        f"Extracts validated: {POLY_HYPER} ({poly_n} rows), "
        f"{SPATIAL_POLY_HYPER} ({spatial_poly_n} rows) match the declared columns"
    )
    print(f"wrote {twb_path.relative_to(REPO_ROOT)} ({twb_path.stat().st_size/1024:.0f} KB)")
    print(f"wrote {twbx_path.relative_to(REPO_ROOT)} ({twbx_path.stat().st_size/1024:.0f} KB)")
    with zipfile.ZipFile(twbx_path) as zf:
        print("package contents:")
        for name in zf.namelist():
            print(f"   {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())