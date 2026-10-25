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
  3  How poverty is made up        one stacked bar per state: the three dimension
                                   shares of the MPI (an identity, the bar
                                   always totals 100), bars listed in
                                   hand-computed MPI order, which the subtitle
                                   says is not a ranking
                                   (docs/SHEET_DIMENSIONS.md)
  4  A state over time             the Measure Names / Measure Values panel: the
                                   reader picks a state, ticks measures off a
                                   checklist, and each measure draws its own
                                   RANK line over the four harmonised rounds --
                                   rank variables only (the 2026-10-21 user
                                   amendment: every non-rank measure is out of
                                   the extract), R1 = highest of that measure,
                                   labels carry the field's own "R0" number
                                   format, no fitted trend line, no red-list
                                   measure,
                                   (docs/SHEET_TIME_PANEL.md)
  5  What the words mean           reference table, part 1 of 3: the 24 words
  6  The list of basic needs       reference table, part 2 of 3: the 11 needs
  7  How we did it                 reference table, part 3 of 3: the 9 steps

  8  Where Nigeria stands          the KPI board against WHO / SDG benchmark
                                    standards: one row per benchmarked KPI, one
                                    circle per reference point (Nigeria, sub-
                                    Saharan Africa, world), positions on each
                                    row's own scale, hover carries the raw
                                    values (docs/SHEET_KPI.md). National figures
                                    only; no per-state panel.
   9 How measures pair             the bivariate exploration board: any two of
                                   the extract's measures as one point per
                                   state-round, both axes driven by parameter
                                   dropdowns (docs/SHEET_PAIRS.md). Kept on the
                                   last tab on purpose: it is for looking, not
                                   the atlas's story.

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
they are recoverable from git. One of them came back on 2026-10-20, deliberately
rebuilt rather than restored: "A state over time" is not the withdrawn
"Poverty over time" (a 37-coloured-trend sheet), but a per-state measure panel
whose fitted trend -- the part that sheet could not support -- is excluded by
design. A second came back on 2026-10-22: the composition sheet is the withdrawn
"dimension breakdown" rebuilt as one stacked bar per state to a frozen design
(docs/SHEET_DIMENSIONS.md), instead of the three-pane defect it died with; one
lesson carried over, the Measure Names union filter that would have de-duplicated
the old sheet's 18,000-tall bar. The pairs board joined on 2026-10-21
(docs/SHEET_PAIRS.md) and brought its own extract. The analyses behind the
withdrawal did not go: stages 02, 03 and 08 still
run, because the party test is pre-registered and its result, the conflict
undercount and the climate overlap are the evidence behind the sentences the
reference tabs now carry.
"""

from __future__ import annotations

import base64
import csv
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape

import atlas_text
from common import PROCESSED, REFERENCE, REPO_ROOT, spatial_context_line

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
              default_agg: str = "", caption: str = "",
              number_format: str = "") -> str:
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
    # ``number_format`` is the field's own number format, serialised the way the
    # application stores one (verified 2026-10-21, V4 load test): the attribute is
    # ``default-format`` ON THE COLUMN -- sheet-level <style-rule> format rules
    # reject attr='number-format' outright ("value 'number-format' not in
    # enumeration", error D2E8DA72) because it is not in the <format> attr enum at
    # all. Tableau applies it to the field's aggregate marks and its axis ticks.
    fmt = f" default-format='{number_format}'" if number_format else ""
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
    # A MEASURE is always type='quantitative', whatever its datatype. The zip of
    # datatype->type above exists for the dimensions (survey_year is an ordinal
    # dimension); applied blindly to measures it made the integer rank fields
    # type='ordinal' measures, and an ordinal measure is not a member of the
    # quantitative Measure Names domain: the field's own domain key is then not
    # the [sum:X:qk] the filter members and palette buckets reference, so the
    # whole Measure Names microcosm -- union filter, colour palette, tick state --
    # silently failed to bind and the sheet drew Tableau's defaults (all-ticked,
    # pastel palette, generated "Count of Migrated Data" drawn as a pane). Seen
    # in Tableau Public 2026.2, 2026-10-21. verified by the render test that
    # re-drew six assigned colours and a six-ticked filter after this change.
    if role == "measure":
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
        f"      <column{cap} datatype='{datatype}'{fmt} name='[{escape(name)}]' "
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


def palette_block(field: str, entries: list[tuple[str, str]],
                  field_ref: str | None = None,
                  shape_entries: list[tuple[str, str]] | None = None) -> str:
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

    Two variants exist in the real workbooks, and which one a colour field uses
    depends on what it is: a normal column on Colour takes ``[none:field:nk]``
    (the default here), while Tableau's generated **Measure Names** field takes the
    bare ``[:Measure Names]`` with no derivation, no kind and no column prefix --
    that is how ``ClimatechangeprofileNigeria`` (via the Tableau MCP server)
    serialises its per-measure colours. Its buckets are not labels either: they are
    the quoted *field references* that make up the measure set, so the caller
    passes those strings as the labels. Both forms end up quoted the same way,
    which is why the one implementation carries both.

    ``type='palette'`` is the discrete form. The continuous form is a sibling of
    this one (``type='interpolated'``, or ``type='custom-interpolated'`` with a
    nested ``<color-palette>`` of hex stops and a ``max`` attribute); it does not
    apply to a nominal dimension.

    ``shape_entries`` adds a sibling encoding for the Shape mark class in the
    same style rule: ``<encoding attr='shape' field='…' type='shape'>`` whose
    ``<map to='Folder/file.png'>`` carries the palette-folder-prefixed FILE NAME
    (not a colour -- the `toint` is a path). ``type='shape'`` is the observed
    spelling, not ``type='palette'`` (every real shape rule in
    ``CH24_BBOD_ChurnTurnover_Updated.twb``, fetched 2026-10-23, uses ``shape``),
    and the images live in the workbook's ``<external><shapes>`` block,
    byte-identical to the files on disk. String buckets are quoted the same way
    the colour buckets are.
    """
    maps = "".join(
        f"            <map to='{colour}'>\n"
        f"              <bucket>{escape(chr(34) + label + chr(34), {chr(34): '&quot;', chr(39): '&apos;'})}</bucket>\n"
        f"            </map>\n"
        for label, colour in entries
    )
    shape_encoding = ""
    if shape_entries:
        shape_maps = "".join(
            f"            <map to='{image}'>\n"
            f"              <bucket>{escape(chr(34) + label + chr(34), {chr(34): '&quot;', chr(39): '&apos;'})}</bucket>\n"
            f"            </map>\n"
            for label, image in shape_entries
        )
        shape_encoding = (
            f"          <encoding attr='shape' field='{field_ref or f'[none:{escape(field)}:nk]'}' type='shape'>\n"
            f"{shape_maps}"
            "          </encoding>\n"
        )
    return (
        "      <style>\n"
        "        <style-rule element='mark'>\n"
        f"          <encoding attr='color' field='{field_ref or f'[none:{escape(field)}:nk]'}' type='palette'>\n"
        f"{maps}"
        "          </encoding>\n"
        f"{shape_encoding}"
        "        </style-rule>\n"
        "      </style>\n"
    )


def datasource_xml(columns: list[tuple[str, str, str]], hyper_filename: str, row_count: int,
                   ds_name: str, ds_caption: str, conn_name: str,
                   instances: str = "",
                   palette: tuple[str, list[tuple[str, str]]] | None = None,
                   shape_palette: list[tuple[str, str]] | None = None,
                   captions: dict[str, str] | None = None,
                   default_formats: dict[str, str] | None = None,
                   calcs: str = "") -> str:
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
    formats = default_formats or {}
    cols = []
    for name, datatype, role in columns:
        cols.append(col_block(name, datatype, role, geographic=(name == "state"),
                              caption=captions.get(name, ""),
                              number_format=formats.get(name, "")))

    col_blocks = "".join(cols)
    dbname = f"Data/{hyper_filename}"
    palette_rule = palette_block(*palette, shape_entries=shape_palette) if palette else ""
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
{col_blocks}{calcs}{instances}      <extract count='-1' enabled='true' units='records'>
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
             captions: dict[str, str] | None = None,
             default_formats: dict[str, str] | None = None,
             calcs: str = "") -> str:
    """The per-worksheet column block real Tableau writes.

    Tableau repeats the datasource's columns inside every worksheet that uses it
    (<datasource-dependencies>). The matching <column-instance> elements are added
    by worksheet_xml, which can see which fields the shelves actually reference.

    ``captions`` must be the same map the datasource was built with. Tableau writes
    a field's caption in both places, and a workbook whose worksheet copies disagree
    with its datasource is a state Tableau never produces itself; which of the two
    the shelf pill and the colour legend read is not established here, so the two
    are made to agree rather than argued about. ``default_formats`` follows the
    same rule for the field number formats (a V4 packet matched Tableau's own
    serialization, which repeats default-format in the worksheet copy too).

    ``calcs`` are calculated-field columns (plus their <column-instance>) that the
    worksheet needs and the extract cannot hold, because they read a parameter.
    They sit INSIDE <datasource-dependencies>, which is where Tableau puts both a
    calculation and its instance -- the boolean-filter calc in
    SoftwareRetailAnalytics.twb is the reference shape (2026-10-25).
    """
    captions = captions or {}
    formats = default_formats or {}
    body = "".join(
        col_block(name, datatype, role, geographic=(name == "state"),
                  caption=captions.get(name, ""),
                  number_format=formats.get(name, ""))
        for name, datatype, role in columns
    )
    return f"""          <datasource-dependencies>
{body}{calcs}          </datasource-dependencies>
"""


def worksheet_xml(name: str, *, rows: str, cols: str, mark: str = "Automatic",
                  encodings: str = "", ds_name: str, ds_caption: str,
                  deps: str = "", subtitle: str = "", tooltip: str = "",
                  mark_formats: tuple[tuple[str, str], ...] = (),
                  pane_mark_formats: tuple[tuple[str, str], ...] = (),
                  pane_datalabel_attrs: tuple[tuple[str, str], ...] = (),
                  filters: str = "", table_style: str = "",
                  label_colour: str = "") -> str:
    """A tooltip, when given, is Tableau's "customized tooltip": it replaces the
    default field list entirely, so fields that exist only to draw the mark stop
    appearing to the reader. Grammar taken from a real Tableau-authored workbook
    -- field references live in CDATA, wrapped in angle brackets.

    ``filters`` are worksheet-level filters, placed inside <view> after the
    datasource-dependencies -- the position ``ClimatechangeprofileNigeria`` and
    ``ClinicPerformanceDashboard`` (both via the Tableau MCP server) always use:
    before <slices>/<aggregation>, never inside <panes>. A quick-filter card in the
    window strip needs a worksheet filter behind it, or the card lists members but
    filters nothing.

    ``table_style`` adds format rules to the worksheet's table-level <style> --
    used by the measure chart to hide its "Multiple Values" axis title, the way
    real serialise the axis they turned off (an <style-rule element='axis'> with an
    attr='display' format naming the field.

    Position matters, and is not guessable: the tooltip element belongs *after*
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

    ``label_colour`` sets the mark LABELS' text colour, when a sheet's numbers sit
    on its own dark fills (the composition sheet's shares sit on the dark
    green/orange/blue segments; the first render, 2026-10-22, printed them in the
    default ink and they were unreadable). Grammar not guessed: GlobeMap_17915413395900
    sets its label text with a worksheet-level <style-rule element='label'> whose
    <format attr='color'> rides beside the mark rule, and the label rule comes
    BEFORE the mark rule in that workbook's <style>.
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
    pane_style = ""
    if label_colour:
        # THE label-colour grammar, proven and landed 2026-10-22. The hunt,
        # one variable per packet in Tableau Public 2026.2: worksheet-level
        # plain <style-rule element='label'> has effect but whitens every
        # label in the sheet (row headers white-on-white, render_dim2);
        # worksheet-level field-scoped on Measure Values (render_dim3) and
        # pane-level field-scoped (render_dim4) are inert; pane-level plain
        # element='label' is inert too (render_dim5). The real serialisation
        # of the Label card's custom colour is element='datalabel' with
        # color-mode='user', copied byte-shape from
        # Try-UmphantStartGallagherPremOpeningWeekend.twbx, which also rides
        # in the pane's <style> -- cell rule, datalabel rule, then mark rule,
        # in that order -- and labels its points white on dark fills. Scoped
        # to data labels only, so the row headers keep their ink.
        pane_style = (
            "            <style-rule element='datalabel'>\n"
            "              <format attr='color-mode' value='user' />\n"
            f"              <format attr='color' value='{label_colour}' />\n"
            "              <format attr='font-weight' value='bold' />\n"
            "            </style-rule>\n"
        )
    # Pane-level mark formats: the Shape marks' size factor lives here in the
    # real serialisation (CH24's Shape panes carry their
    # `<format attr='size' … />` inside the pane's mark style rule, beside
    # mark-labels-show). Anything passed rides under the same rule.
    pane_mark_lines = "".join(
        f"              <format attr='{attr}' value='{value}' />\n"
        for attr, value in pane_mark_formats
    )
    # Pane-level datalabel font rules, same element as the label_colour rule
    # above but for anything else a sheet's labels need (the HR reference
    # workbook's datalabel rules carry `font-size` 8/9/11 beside color-mode /
    # font-family). colour-mode='auto' is the form the real sheets with a bare
    # font-size rule carry; labels keep the default ink.
    pane_datalabel = ""
    if pane_datalabel_attrs:
        body = "".join(
            f"              <format attr='{attr}' value='{value}' />\n"
            for attr, value in pane_datalabel_attrs
        )
        pane_datalabel = (
            "            <style-rule element='datalabel'>\n"
            f"{body}"
            "            </style-rule>\n"
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
{pane_datalabel}{pane_style}            <style-rule element='mark'>
              <format attr='mark-labels-show' value='true' />
{pane_mark_lines}            </style-rule>
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
{deps}{filters}          <aggregation value='true' />
        </view>
        <style>{table_style}{style_block}</style>
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
    # The composition line both maps' hovers print: how the state's MPI splits
    # across OPHI's three areas, pre-composed by stage 4 in stacking order.
    ("dim_hover", "string", "dimension"),
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


# --- The time panel's extract (stage 2/4, mpi_trends_panel.csv) ----------------
# Sheet "A state over time": one state picked, any set of measures ticked, the four
# harmonised survey rounds as a line each. Design freeze: docs/SHEET_TIME_PANEL.md.
#
# The extract's schema *is* the enforceable half of the freeze: the red-list fields
# (the within-year relative conflict index, the weather anomalies) are simply not
# columns, so a later edit cannot put them on a shelf. The raw event/death counts
# are excluded the same way -- the per-100k pair is the defensible form, and the
# freeze's open decision ("raw counts hidden or not at all") is settled as "not at
# all".
#
# The 2026-10-21 amendment extends the red list to every raw value column: the
# marks are ranks, and the user asked that the sheet carry rank variables only, so
# the value measures are not in the extract at all -- the Measure Names domain can
# only list the six ranks (plus the application's generated "Count of Migrated
# Data", which no XML can remove). The hover's two numeric annotations ride as
# PRE-FORMATTED STRINGS (mpi_change_label, deaths_high_label; 04_merge.py formats
# them), because a numeric annotation measure would re-enter the Measure Names
# domain the amendment just cleaned. The full values live in
# data/processed/mpi_trends_panel.csv, which the pipeline's later stages read.
PANEL_DS_NAME = "federated.0mpitrends"
PANEL_DS_CAPTION = "A state over time"
PANEL_CONN = "hyper.0mpitrends"
PANEL_HYPER = "mpi_trends_panel.hyper"
# The tab name is also the sheet's title; the subtitle is a Worksheet argument.
SHEET_TIME_TITLE = "A state over time"
# The dashboard's sheet name. Its title and subtitle come from atlas_text (the
# same two strings the stage-5 gate would print if it drew the board).
SHEET_OVERVIEW = "Overview"
SHEET_CONTEXT = "A state, in context"
PANEL_EXCLUDED = {
    "conflict_exposure_index", "temp_anomaly_c", "precip_anomaly_pct",
    "events", "fatalities", "fatalities_low", "fatalities_high",
    # The amendment's half of the red list: the raw values the marks replaced.
    "mpi", "headcount_ratio_pct", "intensity_pct",
    "events_per_100k", "fatalities_per_100k", "fatalities_per_100k_high",
    "mpi_change_since_prev", "temp_mean_c",
}
PANEL_COLUMNS: list[tuple[str, str, str]] = [
    ("pcode", "string", "dimension"),
    ("state", "string", "dimension"),
    ("survey_year", "integer", "dimension"),
    ("survey", "string", "dimension"),
    ("mpi_change_significant", "string", "dimension"),
    # The hover annotations as strings, so the only measures in the domain are
    # ranks. 04_merge.py writes the formatted text; the tooltip prints it verbatim.
    ("mpi_change_label", "string", "dimension"),
    ("deaths_high_label", "string", "dimension"),
    # The ranks the marks draw (04_merge.py RANK_FIELDS): integer, one per
    # whitelisted measure. These are the ONLY measures the extract declares, so a
    # bare value can no longer reach a mark -- or the checklist.
    ("rank_mpi", "integer", "measure"),
    ("rank_headcount", "integer", "measure"),
    ("rank_intensity", "integer", "measure"),
    ("rank_events", "integer", "measure"),
    ("rank_deaths", "integer", "measure"),
    ("rank_temp", "integer", "measure"),
]


# --- The pairs board's extract (stage 4, mpi_pairs_148.csv) -------------------
# Sheet "How measures pair" (docs/SHEET_PAIRS.md, frozen 2026-10-21): any two of
# the four-round measures or the atlas's per-state constants as one point per
# state-round, split into the two 2021 poverty-group panes. Two selectors make
# the environment dynamic; their grammar was proven in packets A1-A6
# (docs/FIX_LEDGER.md section P): parameters are an inline pseudo-datasource,
# the deck shelf is a paren-plus rows expression, and the axes are CASE calc
# columns that switch on the bound member.
#
# This extract carries NO extraction-time promise the departs from the panel's:
# it is the panel CSV joined to the atlas's per-state constants (joined once in
# stage 4) and the three log(1+rate) columns -- a logged rate is a shipped
# column, not a LOG() inside the CASE, because the log columns need to act as
# ordinary members of the menu that the parameter-driven CASE differentiates;
# the packet proved the extract column drives the payload (packet A6).
PAIRS_DS_NAME = "federated.0mpipairs"
PAIRS_DS_CAPTION = "Pairs board"
PAIRS_CONN = "hyper.0mpipairs"
PAIRS_HYPER = "pairs_board.hyper"
SHEET_PAIRS_TITLE = atlas_text.PAIRS_TITLE
PAIRS_X_CALC = "pair_x_sel"
PAIRS_Y_CALC = "pair_y_sel"
PAIRS_X_CALC_CAPTION = "value of the chosen X measure"
PAIRS_Y_CALC_CAPTION = "value of the chosen Y measure"
PAIRS_PARAM_X = "X axis measure"
PAIRS_PARAM_Y = "Y axis measure"

# The menu is what both dropdowns list and what the CASE differentiates; the
# captions double as the fields' display names (docs/SHEET_PAIRS.md froze the
# list). No order in the menu: the dropdown sorts alphabetically.
PAIRS_MENU: list[tuple[str, str]] = [
    ("H (% poor)", "headcount_ratio_pct"),
    ("MPI", "mpi"),
    ("Depth (avg deprivation among the poor, %)", "intensity_pct"),
    ("Capital temperature in the round (C)", "temp_mean_c"),
    ("UCDP events per 100k", "events_per_100k"),
    ("UCDP events per 100k, log(1+rate)", "log1p_events_per_100k"),
    ("UCDP deaths per 100k", "fatalities_per_100k"),
    ("UCDP deaths per 100k, log(1+rate)", "log1p_fatalities_per_100k"),
    ("UCDP deaths per 100k, upper estimate", "fatalities_per_100k_high"),
    ("UCDP deaths per 100k, upper, log(1+rate)", "log1p_fatalities_per_100k_high"),
    ("MPI standard error (2021)", "mpi_se"),
    ("H standard error (2021)", "headcount_se"),
    ("Vulnerable to poverty, % of population (2021)", "vulnerable_pct"),
    ("In severe poverty, % of population (2021)", "severe_pct"),
    ("Health share of the MPI (2021)", "contrib_health_pct"),
    ("Education share of the MPI (2021)", "contrib_education_pct"),
    ("Living standards share of the MPI (2021)", "contrib_living_standards_pct"),
    ("Population (thousands)", "population_thousands"),
    ("People in MPI poverty (thousands)", "mpi_poor_thousands"),
    ("Capital rainfall in the survey year (mm)", "precip_total_mm"),
    ("Capital temperature, 1991-2020 mean (C)", "baseline_temp_c"),
    ("Capital rainfall, 1991-2020 mean (mm/yr)", "baseline_precip_mm"),
    ("Latitude (capital)", "lat"),
    ("Longitude (capital)", "lon"),
]
PAIRS_DEFAULT_X = "H (% poor)"          # headcount_ratio_pct
PAIRS_DEFAULT_Y = "UCDP events per 100k, log(1+rate)"   # log1p_events_per_100k
assert PAIRS_DEFAULT_X in {label for label, _f in PAIRS_MENU}
assert PAIRS_DEFAULT_Y in {label for label, _f in PAIRS_MENU}
assert len({field for _l, field in PAIRS_MENU}) == len(PAIRS_MENU), (
    "the pairs menu repeats a field"
)
assert len(PAIRS_MENU) == 24, f"the menu has 24 entries, wrote {len(PAIRS_MENU)}"

# ids + panes + hover fields the extract carries besides the menu measures.
# The red-listed family (the within-year conflict index, the anomaly columns)
# is absent BY the freeze -- an exploration space is not an exemption, and the
# two anomaly columns are not in the extract they would have re-entered
# (this extract holds per-STATE constants, not the round-wise anomalies).
PAIRS_COLUMNS: list[tuple[str, str, str]] = [
    ("pcode", "string", "dimension"),
    ("state", "string", "dimension"),
    ("poverty_group", "string", "dimension"),
    ("survey_year", "integer", "dimension"),
    ("survey", "string", "dimension"),
] + [(field, "real", "measure") for _label, field in PAIRS_MENU]


# --- The composition sheet's extract (stage 4, mpi_atlas_2021.csv subset) -----
# Sheet "How poverty is made up" (docs/SHEET_DIMENSIONS.md, frozen 2026-10-22):
# the three dimension shares as one stacked bar per state, bars listed by each
# state's 2021 MPI. The shares are an identity (they are the MPI by construction
# and total 100 per state), which is the one claim the atlas makes without a
# standard error attached.
#
# Measure discipline is the panel's lesson kept: the extract declares exactly
# the three shares as measures, so the Measure Names domain -- which the Colour
# encoding reads and an axis aggregate would stack -- cannot contain anything
# else. The MPI value does NOT enter the extract: the sort it drives is
# hand-computed in main() from the atlas table and serialised as a MANUAL sort
# dictionary (class='manual', quoted buckets, the grammar the
# RegionalSalesDashboard workbook ships byte-for-byte), computed at build time
# so the data file owns the order and the workbook owns no copy of the values.
# The hover's MPI phrase rides as a pre-formatted string (mpi_label, stage 4),
# the same trick the time panel's amendment ships.
DIM_DS_NAME = "federated.0mpidimshare"
DIM_DS_CAPTION = "Poverty composition"
DIM_CONN = "hyper.0mpidimshare"
DIM_HYPER = "dimension_shares.hyper"
SHEET_DIM_TITLE = atlas_text.DIMENSIONS_TITLE
# The short captions are the Measure Names members' display names -- what the
# colour legend, the stacked segments and the tooltip's area name print.
DIM_COLUMNS: list[tuple[str, str, str]] = [
    ("pcode", "string", "dimension"),
    ("state", "string", "dimension"),
    ("poverty_group", "string", "dimension"),
    ("mpi_label", "string", "dimension"),
] + [(field, "real", "measure") for field, _caption, _colour in atlas_text.DIMENSION_SHARES]


# --- The KPI board's extract (stage 7, kpi_dots.csv) --------------------------# Sheet "Where Nigeria stands" (docs/SHEET_KPI.md, frozen 2026-10-23): one row
# per benchmarked KPI, one circle per reference point (Nigeria every row, sub-
# Saharan Africa where WDI publishes it, world every row), each row on its own
# scale (stage 7 row-normalises: pos = value / the row's largest reference).
# The hover carries every raw value pre-formatted (stage 7 composes it from the
# benchmarks table and atlas_text.KPI_SOURCE), so the reader never reads pos as
# a figure -- it is layout, not data.
#
# Palette risk carried from the pairs board (docs/SHEET_PAIRS.md): the PAIRS
# datasource could not take a ds-level palette (grey shell on load), but the
# two maps' and the panel's and the composition sheet's ds-level palettes all
# render, and this datasource has their shape (plain columns, real member
# strings), not the pairs' param/CASE shape. Packet check at publish time.
KP_DS_NAME = "federated.0kpiboard"
KP_DS_CAPTION = "Where Nigeria stands"
KP_CONN = "hyper.0kpiboard"
KP_HYPER = "kpi_dots.hyper"
SHEET_KPI_TITLE = atlas_text.KPI_TITLE
KP_COLUMNS: list[tuple[str, str, str]] = [
    ("kpi", "string", "dimension"),
    ("series", "string", "dimension"),
    ("hover", "string", "dimension"),
    ("pos", "real", "measure"),
    # The mark label: the one-decimal share the sheet prints BESIDE each
    # silhouette, composed data-side by stage 7 (the twb number-format lanes
    # leave the label at Tableau's General 4-decimal print; 2026-10-23).
    ("pos_label", "string", "dimension"),
]

# --- The KPI board's Shape marks (2026-10-23): silhouettes instead of circles --
# The marks are map silhouettes: world / Africa / Nigeria. The grammar is copied
# byte-shape from a real Tableau-authored twb (CH24_BBOD_ChurnTurnover_Updated,
# shipped as a sample in roemeren/tableau-workbook-extractor, fetched
# 2026-10-23), which carries all three pieces:
#
#   * the datasource-level rule ``<encoding attr='shape' field=… type='shape'>``
#     with ``<map to='Folder/file.png'>`` under ``<style-rule element='mark'>``
#     -- the observed type is `shape`, NOT `palette`, and the `to` is the
#     palette-folder-prefixed file name, matching the pane-level constant form
#     ``<format attr='shape' value='Other/transparent.png' />`` the same
#     workbook (and HR #RWFD) serialises;
#   * the pane ``<encodings><shape column='…' /></encodings>`` binding, beside
#     the colour encoding, under ``<mark class='Shape' />``;
#   * the images EMBEDDED in the twb inside ``<external><shapes>`` as
#     ``<shape name='Folder/file.png'>base64</shape>``, which is what keeps a
#     saved/published workbook renderable with no Shapes-repository copy (same
#     finding as the antichaosdata extraction script: the name carries the
#     palette path, and extracting by that name reproduces the folder tree).
#
# The images themselves are stage 7's silhouettes (data/reference/kpi_shapes,
# drawn from the atlas's own ADM1 rings and Natural Earth 110m). The mapping is
# derived from atlas_text.KPI_SHAPE_FILES (the single source shared with the
# stage-5 gate) -- the asserts in shape_pack_xml fail loudly when a member's
# file is missing.
KP_SHAPE_PALETTE: list[tuple[str, str]] = [
    (member, f"KPI_Geo/{fname}")
    for member, fname in atlas_text.KPI_SHAPE_FILES.items()
]
# The mark-box size factor: Shape marks draw at their default scale unless the
# pane's mark style-rule pins one (CH24's Shape panes carry
# ``<format attr='size' value='1.109…|1.785…' />`` at pane level). 1.5 read too
# small in the 2026-10-23 user pass; 2.5 is the follow-up pass's value, and the
# render decides again.
KP_SHAPE_SIZE = "4.0"


def shape_pack_xml() -> str:
    """The workbook's <external><shapes> block: the three silhouettes embedded.

    Tableau embeds custom shapes into the .twb as base64 <shape> children under
    <external><shapes>, with `name` carrying the palette-folder path (the same
    `Folder/file.png` the rule's `map to` references). Embedding is what makes
    the packaged workbook self-contained: saving from Tableau serialises every
    palette the workbook references this way, so nothing outside Data/ is
    needed at open time, and nothing has to be in My Tableau Repository
    either. Only the three files the palette maps to are embedded; the
    repository's default palettes resolve from the install.
    """
    source = REFERENCE / "kpi_shapes"
    shapes_hdr = "  <external>\n    <shapes>\n"
    shapes_body = ""
    for _member, image in KP_SHAPE_PALETTE:
        path = source / image.split("/")[-1]
        assert path.exists(), (
            f"missing silhouette {path.name}: run scripts/07_kpi_reference.py first"
        )
        payload = path.read_bytes()
        assert len(payload) > 2000, f"{path.name} is suspiciously small"
        encoded = base64.b64encode(payload).decode("ascii")
        wrapped = "\n".join(encoded[i:i + 88] for i in range(0, len(encoded), 88))
        shapes_body += f"      <shape name='{image}'>{wrapped}</shape>\n"
    shapes_ftr = "    </shapes>\n  </external>\n"
    return shapes_hdr + shapes_body + shapes_ftr


def pairs_case_formula(param: str) -> str:
    """The axis-picking calc column's CASE, from the frozen menu.

    Both axis columns take the same WHEN list (each arm = one menu entry); the
    packet proved Tableau evaluates thearm at load from the parameter's bound
    value (packets A3/A4: axis = H vs MPI decided the sheet sum exactly).
    """
    whens = "&#10;".join(
        f"WHEN &quot;{escape(label)}&quot; THEN [{field}]"
        for label, field in PAIRS_MENU
    )
    return f"CASE [Parameters].[{param}]&#10;{whens}&#10;END"


def parameter_column_xml(caption: str, pname: str, menu: list[str], default: str) -> str:
    """One parameter, serialised as a column of the inline Parameters datasource.

    Simplification: the caption, the internal name and the tooltip are the same
    string; the packet A5 workbook -- the one that rendered and resolved -- used
    the exact layout this function emits (caption/id both the menu's PVCAM). The
    default must be identical in the datasource and in the sheet-level deps
    mirror: A4 proved the sheet mirror is the one that binds the value.
    """
    return (
        f"      <column caption='{escape(caption)}' datatype='string' name='[{pname}]' "
        f"param-domain-type='list' role='measure' type='nominal' value='&quot;{escape(default)}&quot;'>\n"
        f"        <calculation class='tableau' formula='&quot;{escape(default)}&quot;' />\n"
        f"        <members>\n"
        + "".join(
            f"          <member value='&quot;{escape(label)}&quot;' />\n" for label in menu
        )
        + f"        </members>\n"
        f"      </column>\n"
    )


def parameters_ds_xml(def_x: str, def_y: str, states: list[str]) -> str:
    """The Parameters pseudo-datasource the workbook-level <datasources> carries.

    Grammar from packet A1/A2 (loads, cards render off it). It is appended
    after the extract datasources so the inline (connection-less) block does
    not confuse the two extract-backed reads; inspection of the shipped
    serialized KPI workbook shows parameters first, but the packet had them
    last and loaded, so either position binds.

    Three parameters since 2026-10-25: the pairs board's two dropdowns and the
    Overview's state selector. Parameters are workbook-global, which is the
    whole reason the selector is a parameter and not a filter card -- see the
    STATE_PARAM block.
    """
    labels = [label for label, _field in PAIRS_MENU]
    return (
        "    <datasource hasconnection='false' inline='true' name='Parameters' "
        f"version='{VERSION}'>\n"
        "      <aliases enabled='yes' />\n"
        + parameter_column_xml(PAIRS_PARAM_X, PAIRS_PARAM_X, labels, def_x)
        + parameter_column_xml(PAIRS_PARAM_Y, PAIRS_PARAM_Y, labels, def_y)
        + state_parameter_column_xml(states)
        + panel_state_column_xml(states)
        + "    </datasource>\n"
    )


def parameters_deps_xml(def_x: str, def_y: str) -> str:
    """The sheet-level mirror of the Parameters columns (packet A4's rule)."""
    labels = [label for label, _field in PAIRS_MENU]
    def render(pcaption: str, pdefault: str) -> str:
        return (
            f"          <column caption='{escape(pcaption)}' datatype='string' "
            f"name='[{pcaption}]' param-domain-type='list' role='measure' "
            f"type='nominal' value='&quot;{escape(pdefault)}&quot;'>\n"
            f"            <calculation class='tableau' formula='&quot;{escape(pdefault)}&quot;' />\n"
            f"            <members>\n"
            + "".join(
                f"              <member value='&quot;{escape(label)}&quot;' />\n"
                for label in labels
            )
            + f"            </members>\n"
            f"          </column>\n"
        )
    return (
        "          <datasource-dependencies datasource='Parameters'>\n"
        + render(PAIRS_PARAM_X, def_x)
        + render(PAIRS_PARAM_Y, def_y)
        + "          </datasource-dependencies>\n"
    )


# --- the Overview's state selector (2026-10-25) ------------------------------
# The ask: "selection of states button and a filter so that when a state is
# selected it shows values on all panes in dashboard".
#
# A dashboard filter CARD cannot do that here. The three panes read three
# different extracts (`Nigeria MPI polygons`, `Spatial polygons`, `Poverty
# composition`), and a filter card only ever applies to worksheets on its own
# datasource. A workbook PARAMETER can, because parameters are global: one
# parameter, one calculated boolean per extract, one `paramctrl` zone on the
# page.
#
# Both grammar pieces are copied from SoftwareRetailAnalytics.twbx, unpacked
# 2026-10-25 through the Tableau MCP server (the same file the Overview's zone
# grammar came from). It carries two paramctrl zones and a boolean-calculation
# filter, so neither shape is a guess:
#   <zone h=.. id=.. mode='compact' param='[Parameters].[X]' type-v2='paramctrl' w=.. x=.. y=.. />
#   <filter class='categorical' column='[ds].[none:<calc>:nk]'>
#     <groupfilter function='member' level='[none:<calc>:nk]' member='true' .../>
#   </filter>
STATE_PARAM = "State select"
STATE_PARAM_CAPTION = "State"
STATE_ALL = "(All states)"
STATE_MATCH = "state_match"
STATE_MATCH_CAPTION = "State selection (Overview)"

# The time panel needs exactly ONE state, so it cannot share the Overview's
# selector: that one's "(All states)" arm would draw 37 lines into every pane.
# It gets its own parameter, and its dropdown card is retired the same way the
# composition's was -- the filter becomes parameter-driven, so the card has
# nothing left to bind to and a dashboard can carry a `paramctrl` zone instead.
PANEL_STATE_PARAM = "Panel state"
PANEL_STATE_CAPTION = "Panel state"
PANEL_STATE_MATCH = "panel_state_match"
PANEL_STATE_MATCH_CAPTION = "State shown in the panel"


def panel_state_column_xml(states: list[str]) -> str:
    """The time panel's state parameter (no "(All)" member, by design)."""
    return parameter_column_xml(
        PANEL_STATE_CAPTION, PANEL_STATE_PARAM, states,
        atlas_text.PANEL_DEFAULT_STATE,
    )


def panel_state_calc_xml(indent: str, with_instance: bool = True) -> str:
    """The time panel's calculated filter: the picked state, one row per round."""
    column = (
        f"{indent}<column caption='{escape(PANEL_STATE_MATCH_CAPTION)}'"
        f" datatype='boolean' name='[{PANEL_STATE_MATCH}]' role='dimension'"
        " type='nominal'>\n"
        f"{indent}  <calculation class='tableau' formula='[state] = [Parameters].[{PANEL_STATE_PARAM}]' />\n"
        f"{indent}</column>\n"
    )
    if not with_instance:
        return column
    return column + (
        f"{indent}<column-instance column='[{PANEL_STATE_MATCH}]' derivation='None'"
        f" name='[none:{PANEL_STATE_MATCH}:nk]' pivot='key' type='nominal' />\n"
    )


def state_parameter_column_xml(states: list[str]) -> str:
    """The Overview's state selector, as a column of the Parameters datasource.

    The caption is short ("State") because a dashboard paramctrl shows the
    caption in its label column, and a 348 px zone truncated "State select" to
    "State s.." in the 2026-10-25 render.
    """
    return parameter_column_xml(
        STATE_PARAM_CAPTION, STATE_PARAM, [STATE_ALL] + states, STATE_ALL
    )


def state_match_formula(default_states: list[str] | None = None) -> str:
    """The selector's calculated filter, in Tableau formula syntax.

    Two flavours, because the three panes answer different questions:

    * the maps show whoever is picked, and all 37 on "(All states)";
    * the composition bar must ALSO keep its 17-bar default (the user's
      2026-10-22 decision, docs/SHEET_DIMENSIONS.md D-052) when nobody has
      picked anything, or the sheet opens as a wall of 37 slivers. So its
      "(All states)" arm carries the 17-name list, and a single pick
      overrides it -- which is what stops a pick outside those 17 drawing a
      silently empty pane (the failure AGENTS.md warns about: a filter that
      matches nothing looks like a valid chart with no data).

    Single quotes inside the formula are escaped as &apos; and the string
    literals use &quot;, the serialisation Tableau itself writes for a
    calculation attribute.
    """
    param = f"[Parameters].[{STATE_PARAM}]"
    if default_states is None:
        return f"[state] = {param} OR {param} = &quot;{STATE_ALL}&quot;"
    in_default = " OR ".join(
        f"[state] = &quot;{escape(name)}&quot;" for name in default_states
    )
    return (
        f"{param} = [state] OR "
        f"({param} = &quot;{STATE_ALL}&quot; AND ({in_default}))"
    )


def state_match_calc_xml(indent: str, default_states: list[str] | None = None,
                         with_instance: bool = True) -> str:
    """The calculated field (+ its column-instance), for a deps or datasource block.

    A boolean calculation serialises as ``datatype='boolean' type='nominal'
    role='dimension'`` with a ``<calculation class='tableau' formula=... />``
    child, and it carries a nominal column-instance -- the shape of
    ``Latest Month Filter`` in SoftwareRetailAnalytics.twb (2026-10-25).

    ``with_instance=False`` at DATASOURCE level: the datasource declares the
    field, the worksheet's dependency block declares the instance its filter
    references. That is one declaration per scope, the state Tableau itself
    writes, rather than the same instance twice.
    """
    column = (
        f"{indent}<column caption='{escape(STATE_MATCH_CAPTION)}' datatype='boolean'"
        f" name='[{STATE_MATCH}]' role='dimension' type='nominal'>\n"
        f"{indent}  <calculation class='tableau' formula='{state_match_formula(default_states)}' />\n"
        f"{indent}</column>\n"
    )
    if not with_instance:
        return column
    return column + (
        f"{indent}<column-instance column='[{STATE_MATCH}]' derivation='None'"
        f" name='[none:{STATE_MATCH}:nk]' pivot='key' type='nominal' />\n"
    )


def state_match_filter_xml(ds_name: str) -> str:
    """The worksheet filter that makes the calculation bite.

    ``member='true'`` on a boolean level, with the three ``user:ui-*`` hints
    Tableau writes on every categorical filter it produces itself.
    """
    return calc_true_filter_xml(ds_name, STATE_MATCH)


def panel_state_deps_xml(states: list[str]) -> str:
    """The panel sheet's mirror of its state parameter.

    Packet A4's rule, and this sheet proved it the hard way (2026-10-25): with no
    mirror, the calculation bound to an arbitrary list member and the panel
    opened on Sokoto instead of its Bauchi default, while the parameter's own
    ``value`` attribute in the file still read Bauchi. The mirror is what binds.
    """
    return (
        "          <datasource-dependencies datasource='Parameters'>\n"
        + panel_state_column_xml(states)
        + "          </datasource-dependencies>\n"
    )


def calc_true_filter_xml(ds_name: str, field: str) -> str:
    """``<filter>`` keeping the rows where a boolean calculation is true."""
    return (
        f"          <filter class='categorical' column='[{ds_name}].[none:{field}:nk]'>\n"
        f"            <groupfilter function='member' level='[none:{field}:nk]'"
        " member='true' user:ui-domain='database' user:ui-enumeration='inclusive'"
        " user:ui-marker='enumerate' />\n"
        "          </filter>\n"
    )


def state_parameter_deps_xml(states: list[str]) -> str:
    """The sheet-level mirror of the selector parameter.

    Packet A4's rule, unchanged: the sheet's copy is the one that binds the
    value, so a calculation reading a parameter without this block evaluates
    against nothing.
    """
    return (
        "          <datasource-dependencies datasource='Parameters'>\n"
        + state_parameter_column_xml(states)
        + "          </datasource-dependencies>\n"
    )


def pairs_captions() -> dict[str, str]:
    """The pairs extract's captions: the menu label for every measure in it.

    Same two-location rule as the other sheets (datasource + worksheet deps
    both built from this map), and the menu entry text must equal the caption,
    because the CASE WHEN compares the member to the caption string.
    """
    captions = {field: label for label, field in PAIRS_MENU}
    # The pane-split column's own header printed "povert.." (a truncated
    # poverty_group) over the plot. The values beneath it already read
    # "Poorest 12" / "Other 25", so the column header only needs a word that
    # fits at the header width.
    captions["poverty_group"] = "Group"
    return captions


def pairs_tooltip_runs() -> str:
    """The runs inside the pairs board's customized tooltip.

    Same CDATA grammar as the maps' tooltips. 2026-10-22 the user asked for
    state names ONLY in the hover (was: state + round + group + the two
    values + caveat), so the tooltip is the bold state line alone; the
    chosen pair is visible in the dropdown cards and the caveat sentence
    stays in the subtitle.
    """
    ds = PAIRS_DS_NAME

    def fld(text: str, attrs: str = "") -> str:
        return f"              <run{attrs}><![CDATA[<{text}>]]></run>\n"

    return fld(ref("state", "dim", ds), " bold='true' fontsize='13'")


def pairs_instance_xml() -> str:
    """The <column-instance> block the pairs schema needs, wherever columns go.

    Hand-written: the pairs shelves reference mixed datasources (extract AND
    Parameters) and the pair calc columns, whose instances
    column_instances() cannot derive from a shelf scan (its parser only reads
    [agg:field:kind] refs -- which actually would resolve here, but the
    parameters' pseudo-datasource column-instances do not exist to scan, and
    the packet's proven block is copied verbatim instead).
    """
    return (
        f"      <column-instance column='[{PAIRS_X_CALC}]' derivation='Avg' "
        f"name='[avg:{PAIRS_X_CALC}:qk]' pivot='key' type='quantitative' />\n"
        f"      <column-instance column='[{PAIRS_Y_CALC}]' derivation='Avg' "
        f"name='[avg:{PAIRS_Y_CALC}:qk]' pivot='key' type='quantitative' />\n"
        "      <column-instance column='[poverty_group]' derivation='None' "
        "name='[none:poverty_group:nk]' pivot='key' type='nominal' />\n"
        "      <column-instance column='[state]' derivation='None' "
        "name='[none:state:nk]' pivot='key' type='nominal' />\n"
        "      <column-instance column='[survey_year]' derivation='None' "
        "name='[none:survey_year:ok]' pivot='key' type='ordinal' />\n"
        "      <column-instance column='[pcode]' derivation='None' "
        "name='[none:pcode:nk]' pivot='key' type='nominal' />\n"
        "      <column-instance column='[survey]' derivation='None' "
        "name='[none:survey:nk]' pivot='key' type='nominal' />\n"
    )


def pairs_calc_columns_xml() -> str:
    """The two <column> blocks for the axis-picking CASE columns.

    Both live at workbook level in the pairs datasource AND mirrored inside the
    sheet's deps block (the two-location rule the KPI reference workbook
    serialises everywhere).
    """
    return (
        f"      <column caption='{escape(PAIRS_X_CALC_CAPTION)}' datatype='real' "
        f"name='[{PAIRS_X_CALC}]' role='measure' type='quantitative'>\n"
        f"        <calculation class='tableau' formula='{pairs_case_formula(PAIRS_PARAM_X)}' />\n"
        f"      </column>\n"
        f"      <column caption='{escape(PAIRS_Y_CALC_CAPTION)}' datatype='real' "
        f"name='[{PAIRS_Y_CALC}]' role='measure' type='quantitative'>\n"
        f"        <calculation class='tableau' formula='{pairs_case_formula(PAIRS_PARAM_Y)}' />\n"
        f"      </column>\n"
    )


def pairs_worksheet_xml(def_x: str, def_y: str) -> tuple[str, str]:
    """The 'How measures pair' worksheet and its window cards.

    Built on the packet-A5/A6 serialization rather than worksheet_xml: the
    shelves mix two datasources (the extract AND Parameters), and worksheet_xml
    assumes one. Kept close to the packet, which loaded and drew both times.
    """
    ds = PAIRS_DS_NAME
    deps = (
        "          <datasource-dependencies>\n"
        + deps_xml(PAIRS_COLUMNS, pairs_captions())
                     .replace("          <datasource-dependencies>\n", "")
                     .replace("          </datasource-dependencies>\n", "")
        + pairs_calc_columns_xml().replace("      <column", "            <column")
        + pairs_instance_xml()
        + "          </datasource-dependencies>\n"
        + parameters_deps_xml(def_x, def_y)
    )
    tooltip = pairs_tooltip_runs()
    worksheet = (
        f"    <worksheet name='{escape(SHEET_PAIRS_TITLE)}'>\n"
        f"      <layout-options>\n"
        f"        <title>\n"
        f"          <formatted-text>\n"
        f"            <run bold='true' fontsize='13'>{escape(SHEET_PAIRS_TITLE)}</run>"
        f"<run fontsize='9'>  {escape(atlas_text.PAIRS_SUBTITLE)}</run>\n"
        f"          </formatted-text>\n"
        f"        </title>\n"
        f"      </layout-options>\n"
        f"      <table>\n"
        f"        <view>\n"
        f"          <datasources>\n"
        f"            <datasource caption='{escape(PAIRS_DS_CAPTION)}' name='{ds}' />\n"
        f"          </datasources>\n"
        f"{deps}"
        f"          <aggregation value='true' />\n"
        f"        </view>\n"
        # The mark colour saga, 2026-10-22 (full trial list in
        # docs/SHEET_PAIRS.md): the fill is set by the pane-level
        # mark-color format below -- the FinanceDashboard shape. Not
        # worksheet-level: a plain attr='color' format was inert, an
        # <encoding> palette map on a pane rule and on a table-level rule
        # was inert beside the colour pill, an unqualified-field table rule
        # also left blue, and a ds-level palette on this datasource failed
        # the LOAD outright (grey empty shell). None of the four are in
        # this file's output.
        #
        # <style> under <table> is REQUIRED even when it carries no rules:
        # the builds that dropped it here (2026-10-22) failed the LOAD --
        # grey empty shell, twice on clean starts, packet and full workbook
        # alike -- while this exact shape with the element present loads.
        # Found by bracketing against the pre-session build: the twb diff
        # names this element and the tooltip runs as the only deltas.
        f"        <style />\n"
        f"      <panes>\n"
        f"        <pane selection-relaxation-option='selection-relaxation-allow'>\n"
        f"          <view>\n"
        f"            <breakdown value='auto' />\n"
        f"          </view>\n"
        f"          <mark class='Circle' />\n"
        f"          <encodings>\n"
        f"            <lod column='[{ds}].[none:state:nk]' />\n"
        f"            <lod column='[{ds}].[none:survey_year:ok]' />\n"
        # NO colour pill here: an explicit colour encoding engages the
        # categorical-palette machinery, which beat every style rule tried
        # (packet still drew blue + one stray default-palette orange dot,
        # 2026-10-22). The fill is set by the pane-level mark-color format
        # below, the exact shape FinanceDashboard serialises (52 hits:
        # <format attr='mark-color' value='#000000' /> on pane mark rules).
        f"          </encodings>\n"
        # The quadratic trend line, 2026-10-24 (docs/SHEET_PAIRS.md, "Trend
        # line"). Grammar is NOT guessable and is not from a saved packet --
        # no public twb serialises one -- it is Tableau's own TWB schema,
        # github.com/tableau/tableau-document-schemas,
        # schemas/2026_1/twb_2026.1.0.xsd, group
        # PaneSpecification-Trendline-G:
        #   <trendline enabled fit exclude-intercept enable-confidence-bands
        #              exclude-color [enable-instant-analytics]
        #              [enable-tooltips] [degree]>
        # fit is TrendLineFitType-ST: linear | polynomial | log | exp | power.
        # `degree` is only meaningful for fit='polynomial'. The group's
        # position in PaneSpecification-G's sequence is fixed: after
        # hidden-fields/drop-line, BEFORE reference-line* and before
        # customized-tooltip -- which is where this sits.
        # exclude-color='false' is "allow a trend line per colour"; with no
        # colour pill on this sheet the split that matters is the pane one
        # (poverty_group is on Rows), so each pane gets its own line.
        # enable-instant-analytics='false' on purpose: that switch is what
        # prints the fitted model's equation and p-value in the hover, which is
        # exactly what this sheet's guardlist forbids (no slope, no
        # coefficient). enable-tooltips='true' keeps the ordinary hover.
        f"          <trendline enabled='true' fit='polynomial' degree='2'"
        f" exclude-intercept='false' enable-confidence-bands='true'"
        f" exclude-color='false' enable-instant-analytics='false'"
        f" enable-tooltips='true' />\n"
        f"          <customized-tooltip show-buttons='false'>\n"
        f"            <formatted-text>\n"
        f"{tooltip}"
        f"            </formatted-text>\n"
        f"          </customized-tooltip>\n"
        f"          <style>\n"
        f"            <style-rule element='mark'>\n"
        # The circle fill: pane-level mark-color, the real-workbook shape
        # (FinanceDashboard, 52 hits; scope verified -- it is a <pane>-level
        # mark format there). Tried and dead before this (2026-10-22): a
        # plain attr='color' format (inert), an <encoding> palette on the
        # pane and table rules (inert, the pill's categorical palette won,
        # one stray orange dot), and a ds-level palette on this datasource
        # (failed the LOAD outright -- grey empty shell).
        # mark-color BISECT resolved (2026-10-22): the earlier mark-color
        # "failure" was the missing table-level <style /> above, not this
        # format -- the bracketing diff against the pre-session build names
        # the element as the only structural delta. The format is the
        # FinanceDashboard shape (52 hits, pane mark rules).
        f"              <format attr='mark-color' value='{atlas_text.PAIRS_POINT_COLOUR}' />\n"
        f"              <format attr='mark-labels-show' value='false' />\n"
        f"            </style-rule>\n"
        # The trend line's own paint, 2026-10-24. StyleElement-ST (same schema,
        # same file) enumerates 'trendline' alongside mark/refline/gridline, so
        # a rule with element='trendline' is schema-legal; stroke-color and
        # stroke-size come from StyleAttribute-ST. Verified by render, not by
        # schema alone (docs/SHEET_PAIRS.md).
        f"            <style-rule element='trendline'>\n"
        f"              <format attr='stroke-color' value='{atlas_text.PAIRS_TREND_COLOUR}' />\n"
        f"              <format attr='stroke-size' value='2' />\n"
        f"            </style-rule>\n"
        f"          </style>\n"
        f"        </pane>\n"
        f"      </panes>\n"
        f"        <rows>([{ds}].[none:poverty_group:nk] + [{ds}].[avg:{PAIRS_Y_CALC}:qk])</rows>\n"
        f"        <cols>[{ds}].[avg:{PAIRS_X_CALC}:qk]</cols>\n"
        f"      </table>\n"
        f"    </worksheet>\n"
    )
    window = (
        f"    <!-- The pairs board: its two parameter dropdowns. The cards carry the\n"
        f"         Parameters datasource (packet A2: the card renders off that block,\n"
        f"         unused parameters included); both sit on the left rail with the\n"
        f"         pages/filters/marks stack, the edge the time panel proved draws. -->\n"
        f"    <window class='worksheet' name='{escape(SHEET_PAIRS_TITLE)}'>\n"
        f"      <cards>\n"
        f"        <edge name='left'>\n"
        f"          <strip size='160'>\n"
        f"            <card mode='compact' param='[Parameters].[{PAIRS_PARAM_X}]' type='parameter' />\n"
        f"            <card mode='compact' param='[Parameters].[{PAIRS_PARAM_Y}]' type='parameter' />\n"
        f"            <card type='pages' />\n"
        f"            <card type='filters' />\n"
        f"            <card type='marks' />\n"
        f"          </strip>\n"
        f"        </edge>\n"
        f"        <edge name='top'>\n"
        f"          <strip size='2147483647'>\n"
        f"            <card type='columns' />\n"
        f"          </strip>\n"
        f"          <strip size='31'>\n"
        f"            <card type='title' />\n"
        f"          </strip>\n"
        f"        </edge>\n"
        f"      </cards>\n"
        f"      <viewpoint>\n"
        f"        <zoom type='entire-view' />\n"
        f"      </viewpoint>\n"
        f"    </window>\n"
    )
    return worksheet, window


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


def map_axis_hidden(ds: str) -> str:
    """Hide a map sheet's lat/lon axes: they are place coordinates, not data.

    Grammar: ``<style-rule element='axis'>`` with an ``attr='display'`` format
    naming the field and its ``scope``. The composition sheet already ships this
    shape to drop its generated "Multiple Values" axis
    (``dim_table_style``), and the same attribute is what a real serialised
    workbook writes for an axis the author switched off. A hand-drawn polygon map
    has no business printing a 3..15 longitude ruler, and on the dashboard it did
    (2026-10-24 render), which is what made the panels look like scatter plots.

    ``class='0'`` is the axis level the composition sheet uses; both axes of a
    sheet on Rows/Columns carry it.
    """
    return (
        "          <style-rule element='axis'>\n"
        f"            <format attr='display' class='0' field='[{ds}].[avg:lat:qk]'"
        " scope='rows' value='false' />\n"
        f"            <format attr='display' class='0' field='[{ds}].[avg:lon:qk]'"
        " scope='cols' value='false' />\n"
        "          </style-rule>\n"
    )


def overview_dashboard_xml() -> tuple[str, str]:
    """The "Overview" dashboard: four of the shipped sheets on one fixed page.

    Grammar, all from real files -- nothing here is guessed:

    - the ``<dashboard>`` shell, a bare ``<style />`` and ``<size>``: our own three
      reference dashboards (this file's output, which loads and renders). The
      visible page title is a TEXT ZONE, not ``<layout-options><title>``: the
      layout-options block is what a Tableau-authored file carries, but it did not
      render on this dashboard (2026-10-24 render), while a text zone is the object
      our reference dashboards already prove;
    - an EMBEDDED WORKSHEET zone: ``<zone h w x y name='<sheet>'>`` with no
      ``type-v2``, a ``<layout-cache type-h='cell' type-w='cell' />`` child and a
      ``<zone-style>``: from
      ``SoftwareRetailAnalytics.twbx`` (the dashboard the author pointed at,
      unpacked 2026-10-24), zone id 128;
    - ``<viewpoint name='<sheet>'><zoom type='entire-view' /></viewpoint>`` in the
      dashboard's window: same file, its ``d1. Performance Overview`` window;
    - zone coordinates are 1/100000 of the canvas on each axis, so x/w are
      fractions of the width and y/h of the height -- which is why the helpers
      below convert per axis.

    Three panels, not nine: the two maps answer "where" at the same grain, and the
    composition answers "made of what" for the same 37 states. The KPI board is
    deliberately NOT here -- it is national while these three are state-level, and
    ``docs/SHEET_KPI.md`` forbids reading a state figure against a country
    average, which adjacency alone would invite. The time panel and the pairs
    board stay tabs: one is a full page of six small multiples, the other is the
    interactive coda.
    """
    size = (1600, 1000)
    gap = 8
    header_h = 64

    def ux(px: float) -> int:
        return round(px / size[0] * 100_000)

    def uy(px: float) -> int:
        return round(px / size[1] * 100_000)

    body = size[1] - header_h
    # 2026-10-25: the page gained a state selector and two colour legends. The
    # maps kept their 372 px of height and ceded 250 px of width each to a legend
    # column; the composition bar gained the freed strip and now gets 556 px,
    # about 32 px per bar at the 17-bar default (the old 400/536 split was tuned
    # for 17 bars and no legend at all).
    map_h = 372
    panels = [
        # (sheet name, x, y, w, h) in canvas pixels.
        # Three panels, not four: at this canvas the composition bar and the time
        # panel each need a half-page of their own, and putting both in the bottom
        # row squeezed them into unreadable states (2026-10-24 render of the 2x2:
        # 17 bars in ~300 px, small-multiple row labels truncated to "Conflic..").
        # The maps survive any size, so they take the top row; the composition
        # takes the full width below it, where 17 stacked bars finally breathe.
        # The time panel stays a tab -- it is a page, not a card.
        #
        # 2026-10-25: both legends share ONE column on the far right (330 px),
        # stacked. Attempt 1 put them in a 76 px strip UNDER the maps: one
        # horizontal row of five swatches, every band label clipped to
        # "1. under ..". Attempt 2 gave each map its own 250 px column: the
        # spatial legend's sentences ("Better off than average, neighbours
        # better off") still clipped, and the right map was placed under the left
        # legend by an offset mistake the render caught. One column, two stacks,
        # and the maps keep 627 px each.
        ("Where poverty sits", 0, header_h, 480, map_h),
        (atlas_text.SPATIAL_MAP_TITLE, 488, header_h, 480, map_h),
        # 2026-10-25 (second pass): the composition row cedes its right-hand
        # 292 px to the third legend, so the bar keeps the height it just gained.
        (atlas_text.DIMENSIONS_TITLE, 0, header_h + map_h + gap, 1300,
         body - map_h - gap),
    ]

    # The three colour legends, one per pane, as DASHBOARD ZONES rather than
    # window cards: a card belongs to a sheet's own window and does not travel
    # into a dashboard (FIX_LEDGER O6), which is why the page showed no legend
    # until now. The zone shape is SoftwareRetailAnalytics.twb's (2026-10-25):
    # name = the sheet it belongs to, pane-specification-id = that sheet's pane
    # (0, the default single pane this builder writes), param = the colour field.
    # Each pane encodes a different field, so each needs its own legend. The
    # composition's is `[:Measure Names]`, referenced bare like its palette
    # buckets -- the generated field has no `none:` instance.
    legend_y2 = header_h + map_h + gap
    legends = [
        ("Where poverty sits",
         f"[{POLY_DS_NAME}].[none:mpi_band:nk]", 976, 624, header_h, 190),
        (atlas_text.SPATIAL_MAP_TITLE,
         f"[{SPATIAL_POLY_DS_NAME}].[none:spatial_group:nk]",
         976, 624, header_h + 190, map_h - 190),
        (atlas_text.DIMENSIONS_TITLE, f"[{DIM_DS_NAME}].[:Measure Names]",
         1308, 292, legend_y2, body - map_h - gap),
    ]
    legend_zones = "".join(
        f"          <zone h='{uy(h)}' id='{20 + i}' name='{escape(sheet)}'"
        f" pane-specification-id='0' param='{escape(param)}'"
        f" type-v2='color' w='{ux(w)}' x='{ux(x)}' y='{uy(y)}' />\n"
        for i, (sheet, param, x, w, y, h) in enumerate(legends)
    )
    # The selector, a `paramctrl` zone: package A (SoftwareRetailAnalytics) carries
    # two of these and no window card for either, so the zone alone is the whole
    # declaration. It sits in the title band's right-hand fifth, over the running
    # text zone's last 350 px, which is why that zone narrowed to 1236 px.
    selector_zone = (
        f"          <zone h='{uy(44)}' id='30' mode='compact'"
        f" param='[Parameters].[{STATE_PARAM}]' type-v2='paramctrl'"
        f" w='{ux(348)}' x='{ux(1244)}' y='{uy(10)}' />\n"
    )

    zones = (
        # The page's own title band. A text zone rather than the dashboard's
        # <layout-options><title>: that block is what a Tableau-authored file
        # carries, but it did not render here (2026-10-24 render), while a text
        # zone is the object our three reference dashboards already prove.
        f"          <zone forceUpdate='true' h='{uy(header_h)}' id='9'"
        f" type-v2='text' w='{ux(1236)}' x='0' y='0'>\n"
        f"            <formatted-text>\n"
        f"              <run bold='true' fontsize='16'>{escape(atlas_text.OVERVIEW_TITLE)}</run>"
        f"<run fontsize='10'>  {escape(atlas_text.OVERVIEW_SUBTITLE)}</run>\n"
        f"            </formatted-text>\n"
        f"            <zone-style>\n"
        f"              <format attr='margin' value='8' />\n"
        f"            </zone-style>\n"
        f"          </zone>\n"
        f"{selector_zone}"
    ) + "".join(
        f"          <zone h='{uy(h)}' id='{10 + i}' name='{escape(name)}'"
        f" w='{ux(w)}' x='{ux(x)}' y='{uy(y)}'>\n"
        f"            <layout-cache type-h='cell' type-w='cell' />\n"
        f"            <zone-style>\n"
        f"              <format attr='border-color' value='#d9d9d9' />\n"
        f"              <format attr='border-style' value='solid' />\n"
        f"              <format attr='border-width' value='1' />\n"
        f"              <format attr='margin' value='2' />\n"
        f"            </zone-style>\n"
        f"          </zone>\n"
        for i, (name, x, y, w, h) in enumerate(panels)
    ) + legend_zones
    dashboard = (
        f"    <dashboard name='{escape(SHEET_OVERVIEW)}'>\n"
        f"      <style />\n"
        f"      <size maxheight='{size[1]}' maxwidth='{size[0]}'"
        f" minheight='{size[1]}' minwidth='{size[0]}' />\n"
        f"      <zones>\n"
        f"        <zone h='100000' id='1' type-v2='layout-basic' w='100000'"
        f" x='0' y='0'>\n"
        f"{zones}"
        f"        </zone>\n"
        f"      </zones>\n"
        f"    </dashboard>\n"
    )
    viewpoints = "".join(
        f"        <viewpoint name='{escape(name)}'>\n"
        f"          <zoom type='entire-view' />\n"
        f"        </viewpoint>\n"
        for name, _x, _y, _w, _h in panels
    )
    window = (
        f"    <window class='dashboard' name='{escape(SHEET_OVERVIEW)}'>\n"
        f"      <viewpoints>\n"
        f"{viewpoints}"
        f"      </viewpoints>\n"
        f"      <active id='-1' />\n"
        f"    </window>\n"
    )
    return dashboard, window


def context_dashboard_xml() -> tuple[str, str]:
    """The second data dashboard: "A state, in context" (2026-10-25).

    Three shipped sheets on one 1600x1300 page, at the author's request: the time
    panel top-left, the pairs board top-right, the national benchmarks full width
    at the bottom.

    **This page knowingly contradicts a frozen guardrail, on the record.**
    ``docs/SHEET_KPI.md`` says "No state-level panel ... this one stays national",
    because a state's line beside a world average invites comparing the two. The
    author asked for the three together (2026-10-25); the override is written up
    as amendment 1 in that file, and the mitigation is here: the page subtitle
    says the bottom band is a national comparison, and the KPI band keeps its own
    title, subtitle and direction key rather than borrowing the page's.

    **Controls.** Three ``paramctrl`` zones, because cards do not travel into a
    dashboard (``FIX_LEDGER`` O6):

    * the time panel's state -- its OWN parameter, not the Overview's selector:
      that one has an ``(All states)`` arm, which on a six-pane panel would draw
      37 lines into every pane;
    * the pairs board's X and Y measures, whose parameters already existed.

    The panel's Measure Names checklist stays on its tab. Turning it into a
    dashboard control would need a third parameter and a whitelist calculation,
    which is a bigger change than this page is worth today.
    """
    size = (1600, 1300)
    gap = 8
    header_h = 150

    def ux(px: float) -> int:
        return round(px / size[0] * 100_000)

    def uy(px: float) -> int:
        return round(px / size[1] * 100_000)

    panels = [
        # (sheet, x, y, w, h). The time panel needs height (six stacked panes);
        # the pairs board needs height too (two panes, each with a fitted band);
        # the KPI board needs width (long row labels plus three silhouettes).
        (SHEET_TIME_TITLE, 0, header_h, 880, 620),
        (atlas_text.PAIRS_TITLE, 888, header_h, 712, 620),
        (SHEET_KPI_TITLE, 0, header_h + 620 + gap, 1316, 512),
    ]
    # The KPI board's colour card cannot travel; the three reference points are
    # what the silhouettes mean, so the legend is a zone of its own.
    kpi_legend = (
        f"          <zone h='{uy(512)}' id='20' name='{escape(SHEET_KPI_TITLE)}'"
        f" pane-specification-id='0'"
        f" param='[{KP_DS_NAME}].[none:series:nk]'"
        f" type-v2='color' w='{ux(276)}' x='{ux(1324)}'"
        f" y='{uy(header_h + 620 + gap)}' />\n"
    )
    controls = "".join(
        f"          <zone h='{uy(40)}' id='{30 + i}' mode='compact'"
        f" param='[Parameters].[{param}]' type-v2='paramctrl'"
        f" w='{ux(570)}' x='{ux(1020)}' y='{uy(10 + 50 * i)}' />\n"
        for i, param in enumerate(
            (PANEL_STATE_PARAM, PAIRS_PARAM_X, PAIRS_PARAM_Y)
        )
    )
    zones = (
        f"          <zone forceUpdate='true' h='{uy(header_h)}' id='9'"
        f" type-v2='text' w='{ux(1000)}' x='0' y='0'>\n"
        f"            <formatted-text>\n"
        f"              <run bold='true' fontsize='16'>{escape(atlas_text.CONTEXT_TITLE)}</run>"
        f"<run fontsize='10'>  {escape(atlas_text.CONTEXT_SUBTITLE)}</run>\n"
        f"            </formatted-text>\n"
        f"            <zone-style>\n"
        f"              <format attr='margin' value='8' />\n"
        f"            </zone-style>\n"
        f"          </zone>\n"
        f"{controls}"
    ) + "".join(
        f"          <zone h='{uy(h)}' id='{10 + i}' name='{escape(name)}'"
        f" w='{ux(w)}' x='{ux(x)}' y='{uy(y)}'>\n"
        f"            <layout-cache type-h='cell' type-w='cell' />\n"
        f"            <zone-style>\n"
        f"              <format attr='border-color' value='#d9d9d9' />\n"
        f"              <format attr='border-style' value='solid' />\n"
        f"              <format attr='border-width' value='1' />\n"
        f"              <format attr='margin' value='2' />\n"
        f"            </zone-style>\n"
        f"          </zone>\n"
        for i, (name, x, y, w, h) in enumerate(panels)
    ) + kpi_legend
    dashboard = (
        f"    <dashboard name='{escape(SHEET_CONTEXT)}'>\n"
        f"      <style />\n"
        f"      <size maxheight='{size[1]}' maxwidth='{size[0]}'"
        f" minheight='{size[1]}' minwidth='{size[0]}' />\n"
        f"      <zones>\n"
        f"        <zone h='100000' id='1' type-v2='layout-basic' w='100000'"
        f" x='0' y='0'>\n"
        f"{zones}"
        f"        </zone>\n"
        f"      </zones>\n"
        f"    </dashboard>\n"
    )
    viewpoints = "".join(
        f"        <viewpoint name='{escape(name)}'>\n"
        f"          <zoom type='entire-view' />\n"
        f"        </viewpoint>\n"
        for name, _x, _y, _w, _h in panels
    )
    window = (
        f"    <window class='dashboard' name='{escape(SHEET_CONTEXT)}'>\n"
        f"      <viewpoints>\n"
        f"{viewpoints}"
        f"      </viewpoints>\n"
        f"      <active id='-1' />\n"
        f"    </window>\n"
    )
    return dashboard, window


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
                   poly_rows: int, spatial_poly_rows: int, panel_rows: int,
                   pairs_rows: int, dim_bar_order: list[str],
                   dim_rows: int, kpi_rows: int,
                   kpi_order: list[str]) -> str:
    """The workbook: two maps drawn from the same rings, the composition bar, the
    time panel, the KPI board, the pairs board, and the reference table.

    Six extracts, six datasources, plus the inline Parameters pseudo-datasource
    the pairs board's two dropdowns read. The atlas, party-alignment and
    spatial-diagnostic extracts were withdrawn on 2026-10-18 with the sheets that
    drew them (module docstring); the trends panel is the one extract that came
    back, in 2026-10-20, for the frozen time-panel sheet
    (docs/SHEET_TIME_PANEL.md) -- its red-list fields are not in the schema at
    all (they are asserted against, not filtered out of the sheet). The pairs
    board is the seventh sheet, 2026-10-21 (docs/SHEET_PAIRS.md). The
    composition sheet is the eighth, 2026-10-22 (docs/SHEET_DIMENSIONS.md):
    the three dimension shares stacked, bars in hand-computed MPI order carried
    as a manual sort dictionary, the MPI value itself not in the extract.
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
    poly_deps = deps_xml(
        POLY_COLUMNS, poly_captions, calcs=state_match_calc_xml("            ")
    )

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
    spatial_poly_deps = deps_xml(
        SPATIAL_POLY_COLUMNS, spatial_poly_captions,
        calcs=state_match_calc_xml("            "),
    )

    # ---- the cluster map's tooltip ------------------------------------------
    # The same per-state numbers the poverty map's hover carries, plus the four
    # frozen reader lines from the pre-registered spatial test (stage 9) and the
    # technical footer. The paragraph that says how to read *this* surface is a
    # parameter, because it used to be shared with the Moran scatter, which was
    # withdrawn on 2026-10-18; the frozen lines and the footer stay single-sourced.
    def spatial_tooltip_runs(ds: str) -> str:
        """The runs inside the cluster map's customized tooltip.

        2026-10-25, the second pass on this hover: the user's note was that the
        text was too much ("reduce it so its precise and concise"). What it
        carried was a four-line essay (the frozen SPATIAL_READER_LINES), a
        "how to read this surface" paragraph, a reading heading and a technical
        footer -- eleven lines of prose behind a 40 px hover box.

        What is left is the numbers and the one caveat that may not be dropped:
        a neighbourhood type is vocabulary that invites a spillover reading, so
        SPATIAL_NO_CAUSE stays. The four frozen lines are not lost -- they move
        to "How we did it" (docs/spatial_preregistration.md, amendment 3), where
        long prose belongs. The reading is now carried by the legend
        (type-v2='color' zone on the Overview) and the sheet's subtitle.
        """
        def fld(column: str, kind: str = "sum", attrs: str = "") -> str:
            return f"              <run{attrs}><![CDATA[<{ref(column, kind, ds)}>]]></run>\n"

        def txt(body: str, attrs: str = "") -> str:
            return f"              <run{attrs}>{body}</run>\n"

        out = (
            fld("state", "dim", " bold='true' fontsize='13'")
            + txt(" &#183; ")
            + fld("spatial_group", "dim")
            + txt("&#10;Poverty score: ", " bold='true'")
            + fld("mpi_pct", "sum", " bold='true'")
            + txt("%", " bold='true'")
            + txt("&#10;Made up of: ")
            + fld("dim_hover", "dim")
            + txt("&#10;Average of the ")
            + fld("neighbours")
            + txt(" states it borders: ")
            + fld("spatial_lag_mpi_pct")
            + txt("%")
            + txt("&#10;&#10;" + escape(atlas_text.SPATIAL_NO_CAUSE), " italic='true'")
        )
        # The first shortened build lost the state name and the type label without
        # anything complaining: ``fld()`` defaults to kind="sum", so
        # ``fld("spatial_group")`` serialised a sum: aggregate over a *dimension*,
        # which prints an aggregate instead of the member's words. A tooltip is a
        # popup window no PrintWindow capture can see, so the render could not
        # catch it either. Both leading fields are asserted here instead.
        assert "[none:state:nk]" in out, "cluster hover lost the state name"
        assert "[none:spatial_group:nk]" in out, "cluster hover lost the type label"
        return out

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
            + txt("Made up of: ")
            + fld("dim_hover", "dim")
            + txt("&#10;")
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
        subtitle=atlas_text.MPI_MAP_SUBTITLE,
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
        deps=poly_deps + state_parameter_deps_xml(dim_bar_order),
        filters=state_match_filter_xml(POLY_DS_NAME),
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
        table_style=map_axis_hidden(POLY_DS_NAME),
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
        deps=spatial_poly_deps + state_parameter_deps_xml(dim_bar_order),
        filters=state_match_filter_xml(SPATIAL_POLY_DS_NAME),
        tooltip=spatial_tooltip_runs(SPATIAL_POLY_DS_NAME),
        # The same white strokes sheet 1 carries, so the country reads as the same
        # country drawn twice rather than as two different maps of two different places.
        mark_formats=(("has-stroke", "true"), ("stroke-color", "#FFFFFF"), ("stroke-size", "3")),
        table_style=map_axis_hidden(SPATIAL_POLY_DS_NAME),
    )

    # ---- sheet 2b: the time panel, "A state over time" ----------------------
    # The frozen design (docs/SHEET_TIME_PANEL.md, amended 2026-10-21): the reader
    # picks ONE state from a dropdown and ticks ANY SET of measures from a
    # checklist; each measure draws its own line over the four survey rounds, and
    # since the amendment the mark's number is that state's RANK of the 37 in that
    # round, and the extract carries rank variables ONLY -- the raw value columns
    # left the schema the same day (see PANEL_COLUMNS' comment). Labels carry the
    # field's own "R0" number format; the direction key rides the row headers and
    # the subtitle. A fitted trend line is deliberately never added to this sheet
    # -- four points per line cannot support a slope, and a trend sheet is exactly
    # what was withdrawn in W1.
    #
    # The construct is the Measure Names / Measure Values pair, copied from a real
    # Tableau-authored workbook rather than invented: ``ClimatechangeprofileNigeria``
    # (via the Tableau MCP server) draws exactly this pair as a stacked area, and
    # "KPI - Progress -Status" places the same composition `([a] + [b])` on shelves.
    # Here Measure NAMES is on Rows with Measure VALUES under it, so each selected
    # measure small-multiples into its own pane and its own axis -- the one construct
    # where "tick any combination of measures" does not force a shared axis (MPI at
    # 0-0.45 dies against H at 0-75 on one axis, and normalising would reintroduce
    # the within-year relativity the conflict index demonstrates the danger of).
    # Note how Tableau serialises the pair: Measure Values is the generated field
    # [Multiple Values], Measure Names the generated [Measure Names] with no
    # derivation and no kind, referenced as [:Measure Names].
    #
    # The earlier attempt (the old dimension-breakdown sheet) failed at this pair --
    # it drew one 18,000-tall bar because it lacked the <filter> over Measure Names
    # that de-duplicates the shelf. The real workbooks settle it: the filter is a
    # categorical <groupfilter function='union' user:op='manual'> whose members are
    # the quoted field references of the measures, and the default member set is
    # everything on the whitelist (the reader un-ticks from the checklist card).
    #
    # State is filtered once, worksheet-level, to a single member -- the sheet
    # cannot open blank because Bauchi (the hover example everywhere else) is the
    # default; the dropdown card narrows it. The customized tooltip carries the
    # honest per-point annotations -- the annualised change since the previous
    # round, the star flag, the survey source. No customized tooltip would be
    # needed to show values: there are none on the sheet any more, the marks print
    # ranks, and the generated [Multiple Values] field has no proven tooltip
    # serialization in any workbook on hand.
    panel_captions = {field: caption for field, caption, _colour in atlas_text.PANEL_MEASURES}
    panel_captions.update({
        "mpi_change_significant": "Movement OPHI's change test calls significant (*, **, ***)",
        "mpi_change_label": "Mean annual change since the previous round (MPI points/yr)",
        "deaths_high_label": "Conflict deaths per 100,000 (upper estimate)",
        "survey": "Survey the round comes from",
    })
    # The six rank measures carry the sheet's own number format: the custom format
    # "R"0 (escaped) on the FIELD -- see col_block for the serialization finding.
    panel_formats = {name: "&quot;R&quot;0" for name, _c, _k in atlas_text.PANEL_MEASURES}
    panel_deps = deps_xml(
        PANEL_COLUMNS, panel_captions, panel_formats,
        calcs=panel_state_calc_xml("            "),
    )

    def panel_filters() -> str:
        """Worksheet-level filters, copied from the real workbooks' grammar.

        The Measure Names filter's members are the quoted field references of the
        six whitelist measures (that is what a member of Measure Names *is*); the
        union with user:op='manual' is the default-checked set. The state filter is
        a single member, the freeze's "default state on load".
        """
        members = "".join(
            "          <groupfilter function='member' level='[:Measure Names]' "
            f"member=\"&quot;[{PANEL_DS_NAME}].[sum:{name}:qk]&quot;\" />\n"
            for name, _caption, _colour in atlas_text.PANEL_MEASURES
        )
        # 2026-10-25: the single-member state filter became the Panel state
        # parameter's calculation, so a dashboard can carry the control
        # (`paramctrl`) instead of a card that cannot travel. The parameter
        # defaults to PANEL_DEFAULT_STATE, so the tab still opens on Bauchi.
        return (
            f"          <filter class='categorical' column='[{PANEL_DS_NAME}].[:Measure Names]'>\n"
            "            <groupfilter function='union' user:op='manual'>\n"
            f"{members}"
            "            </groupfilter>\n"
            "          </filter>\n"
            f"{calc_true_filter_xml(PANEL_DS_NAME, PANEL_STATE_MATCH)}"
        )

    def panel_table_style() -> str:
        """Hide the meaningless axis title ``Multiple Values``.

        The reader names the panes by the row headers (the measure captions);
        leaving the generated field's title in the axis would print "Multiple
        Values" beside each pane. This is how the real workbooks turn an axis off:
        a table-level axis rule with an attr='display' format naming the field.

        The rank labels' prefix comes from the field, not from a style rule: the
        question of where a mark's number format serialises is settled
        (2026-10-21, four bisected packets in Tableau Public 2026.2). A
        ``<style-rule>``-level ``attr='number-format'`` -- field-scoped or
        mark-scoped -- fails the whole workbook load with D2E8DA72, "value
        'number-format' not in enumeration": the 2026.2 schema's <format> attr
        enum (read out of tabfileformat.dll) does not contain it at all. The
        number format lives on the <column> as ``default-format='"R"0'``; with
        that attribute present the workbook loads and the labels print bare
        integers (the old two-decimal misprint gone with it). The "R" prefix
        itself did not render from XML in the verification load, so the direction
        key rides in the row-header captions and the sheet subtitle
        (atlas_text.PANEL_SUBTITLE) -- docs/SHEET_TIME_PANEL.md records it.
        """
        return (
            "          <style-rule element='axis'>\n"
            f"            <format attr='display' class='0' field='[{PANEL_DS_NAME}].[Multiple Values]' "
            "scope='rows' value='false' />\n"
            "          </style-rule>\n"
            # 2026-10-25: the row headers were breaking MID-WORD ("Intensit /
            # y / ran / k"), which reads as a rendering fault rather than a
            # label. The header column was sized by Tableau's default; this
            # pins it. Same field-scoped width rule the KPI board (230 px on
            # `kpi`) and the composition sheet (92 px on `poverty_group`) already
            # ship, so the grammar is proven in this workbook. The field here is
            # the generated Measure Names dimension, referenced bare like its
            # palette buckets.
            "          <style-rule element='header'>\n"
            f"            <format attr='width' field='[{PANEL_DS_NAME}].[:Measure Names]' "
            "value='168' />\n"
            "          </style-rule>\n"
        )

    panel_encodings = (
        f"            <color column='[{PANEL_DS_NAME}].[:Measure Names]' />\n"
    )
    # Deliberately NO <lod> fields on the mark. The first render (2026-10-20,
    # review_time_only.twbx in Tableau Public 2026.2) drew six panes x four rounds
    # of isolated points, no connecting lines: of the hover's supporting fields,
    # `survey` and `mpi_change_significant` are DIMENSIONS, and a dimension on
    # detail is part of the mark's identity, so a value that changes from round to
    # round (DHS -> MICS, blank -> **) splits the pane's four marks into four
    # one-point "lines". Since the 2026-10-21 amendment every annotation field is a
    # string dimension that rides in the customized tooltip only -- nothing sits on
    # detail -- so the four rounds of each rank line remain one line per pane.
    # Tableau's tooltip refs of off-view fields resolve to the mark's own context,
    # which for this sheet is exactly one (state, round) row. The default tooltip
    # would have carried nothing but the measure name and value.

    def panel_tooltip_runs(ds: str) -> str:
        """The runs inside the time panel's customized tooltip.

        Same CDATA grammar as the maps' tooltips (declared columns in angle
        brackets), and only fields that exist in the extract. The movement
        annotation and the deaths estimate print STRING dimensions
        (mpi_change_label / deaths_high_label -- 04_merge.py pre-formats them):
        numeric annotation measures would re-enter the Measure Names domain, which
        the 2026-10-21 amendment empties of everything but the six ranks.
        """

        def fld(column: str, kind: str = "sum", attrs: str = "") -> str:
            return f"              <run{attrs}><![CDATA[<{ref(column, kind, ds)}>]]></run>\n"

        def txt(body: str, attrs: str = "") -> str:
            return f"              <run{attrs}>{body}</run>\n"

        return (
            fld("state", "dim", " bold='true' fontsize='13'")
            + txt(" &#183; ")
            + fld("survey_year", "dim", " bold='true'")
            + txt("&#10;Survey the round comes from: ")
            + fld("survey", "dim")
            + txt("&#10;Mean annual change since the previous round (MPI points/yr): ")
            + fld("mpi_change_label", "dim", " bold='true'")
            + txt("&#10;Movement the OPHI change test calls significant: ")
            + fld("mpi_change_significant", "dim", " bold='true'")
            + txt("&#10;Conflict deaths per 100,000 people (upper estimate): ")
            + fld("deaths_high_label", "dim")
            + txt("&#10;&#10;")
            + txt(
                "Line, not a trend: four harmonised rounds per measure (2013 DHS, "
                "2016 and 2018 MICS, 2021 DHS). Neighbouring states' intervals "
                "overlap at 95%, so read movement within this state only.",
                " italic='true'",
            )
        )
    sheet_time = worksheet_xml(
        SHEET_TIME_TITLE,
        subtitle=atlas_text.PANEL_SUBTITLE,
        rows=f"([{PANEL_DS_NAME}].[:Measure Names] + [{PANEL_DS_NAME}].[Multiple Values])",
        cols=f"[{PANEL_DS_NAME}].[none:survey_year:ok]",
        mark="Line",
        encodings=panel_encodings,
        ds_name=PANEL_DS_NAME,
        ds_caption=PANEL_DS_CAPTION,
        deps=panel_deps + panel_state_deps_xml(dim_bar_order),
        filters=panel_filters(),
        table_style=panel_table_style(),
        tooltip=panel_tooltip_runs(PANEL_DS_NAME),
    )

    # ---- sheet 2b: the composition sheet, "How poverty is made up" ----------
    # The frozen design (docs/SHEET_DIMENSIONS.md, built 2026-10-22): one bar
    # per state, each stacked into the three dimension shares, bars listed by
    # each state's 2021 MPI. The shares are an identity -- the bar totals 100
    # everywhere -- and the claim the sheet carries is the dimension CONTRAST
    # the reference table already publishes (education 39.9% of the MPI in the
    # poorest 12 vs 22.3% in the rest), never the MPI ordering itself: the
    # subtitle, the caveat in the hover and the reference table all say order
    # is not a ranking. The construct is the same Measure Names / Measure
    # Values pair the time panel proved renders from hand-written XML, with the
    # names on Colour and the values on Columns so the measures STACK instead
    # of pane-ing, and the Measure Names union filter de-duplicating the shelf
    # (the old withdrawn dimension sheet's 18,000-tall-bar defect, without
    # which the filter let the aggregate in). The bar order is hand-computed in
    # main() from the atlas table and shipped as a class='manual' sort
    # dictionary, copied byte-for-byte from RegionalSalesDashboard -- a
    # computed sort would need an MPI measure in the extract, and the extract
    # declares the three shares and nothing else.
    def dim_filters(order: list[str]) -> str:
        """The Measure Names whitelist, the manual bar order, and the state
        filter's default-checked set.

        The default view's membership moved from a fixed filter to the Overview's
        state parameter on 2026-10-25 (amendment 2, docs/SHEET_DIMENSIONS.md),
        and the default itself became the TOP HALF of each group the same day:
        ranks 1-6 and ranks 13-24 -- 18 bars (atlas_text.composition_default).
        It lives in the ``state_match`` calculation rather than a filter, because
        a parameter pick must be able to override it and two ANDed filters
        cannot: a pick outside the default used to draw a silently empty pane.
        The bar order is still MPI descending, so each block prints its own
        highest-ranked states first without a second sort.
        """
        members = "".join(
            "          <groupfilter function='member' level='[:Measure Names]' "
            f"member=\"&quot;[{DIM_DS_NAME}].[sum:{field}:qk]&quot;\" />\n"
            for field, _caption, _colour in atlas_text.DIMENSION_SHARES
        )
        buckets = "".join(
            f"            <bucket>&quot;{escape(state)}&quot;</bucket>\n"
            for state in order
        )
        # The multi-member union grammar the state filter used to carry (and
        # that the Measure Names filter below still uses) lives on in
        # state_match_filter_xml's single-member form instead: the parameter
        # now decides membership.
        # The state selector, not a 17-member union: see the docstring. A
        # parameter pick reaches all three panes because the parameter is
        # workbook-global and each extract carries its own copy of the calc.
        # The comment above the old block explained the union grammar; that
        # grammar still ships on the time panel's Measure Names filter.
        return (
            f"          <filter class='categorical' column='[{DIM_DS_NAME}].[:Measure Names]'>\n"
            "            <groupfilter function='union' user:op='manual'>\n"
            f"{members}"
            "            </groupfilter>\n"
            "          </filter>\n"
            f"{state_match_filter_xml(DIM_DS_NAME)}"
            f"          <sort class='manual' column='[{DIM_DS_NAME}].[none:state:nk]' "
            "direction='ASC'>\n"
            "            <dictionary>\n"
            f"{buckets}"
            "            </dictionary>\n"
            "          </sort>\n"
            # The group's block order: "Poorest 12" first, MPI order, not
            # alphabetically. Manual sort with string buckets is the proven
            # dictionary shape (real workbooks sort dimensions exactly this
            # way; the state sort above rides the same grammar on titles).
            f"          <sort class='manual' column='[{DIM_DS_NAME}].[none:poverty_group:nk]' "
            "direction='ASC'>\n"
            "            <dictionary>\n"
            f"            <bucket>&quot;{escape(atlas_text.POVERTY_GROUP_TOP)}&quot;</bucket>\n"
            f"            <bucket>&quot;{escape(atlas_text.POVERTY_GROUP_REST)}&quot;</bucket>\n"
            "            </dictionary>\n"
            "          </sort>\n"
        )

    def dim_table_style() -> str:
        # The generated field's axis title would print "Multiple Values" on the
        # shared axis; hide it the way panel_table_style hides the rows copy.
        # The second rule widens the nested group header so "Poorest 12"/
        # "Other 25" print on one line -- the field-scoped width rule is the
        # ClinicPerformanceDashboard/FinanceDashboard grammar
        # (<style-rule element='header'><format attr='width' field=... />).
        return (
            "          <style-rule element='axis'>\n"
            f"            <format attr='display' class='0' field='[{DIM_DS_NAME}].[Multiple Values]' "
            "scope='cols' value='false' />\n"
            "          </style-rule>\n"
            "          <style-rule element='header'>\n"
            f"            <format attr='width' field='[{DIM_DS_NAME}].[none:poverty_group:nk]' "
            "value='92' />\n"
            "          </style-rule>\n"
        )

    dim_captions = {
        field: caption for field, caption, _colour in atlas_text.DIMENSION_SHARES
    }
    dim_captions.update({
        "mpi_label": "MPI (as a % of the index)",
        # The nested group header's caption: without it the axis strip prints
        # the raw field name and truncates. States its meaning plainly.
        "poverty_group": "Poverty group",
    })
    # The composition's selector calc keeps the 17-bar default: "(All states)"
    # resolves to the same 17 the sheet has shipped since 2026-10-22, and a
    # single pick overrides it (docs/SHEET_DIMENSIONS.md, 2026-10-25 amendment).
    dim_deps = deps_xml(
        DIM_COLUMNS, dim_captions,
        calcs=state_match_calc_xml(
            "            ", atlas_text.composition_default(dim_bar_order)
        ),
    )

    def dim_tooltip_runs(ds: str) -> str:
        """The runs inside the composition sheet's customized tooltip."""

        def fld(column: str, attrs: str = "") -> str:
            return f"              <run{attrs}><![CDATA[<{ref(column, 'dim', ds)}>]]></run>\n"

        def fldnames(attrs: str = "") -> str:
            return (
                f"              <run{attrs}><![CDATA[<[{ds}].[:Measure Names]>]]></run>\n"
            )

        def txt(body: str, attrs: str = "") -> str:
            return f"              <run{attrs}>{body}</run>\n"

        return (
            fld("state", " bold='true' fontsize='13'")
            + txt(" &#183; MPI ")
            + fld("mpi_label", " bold='true'")
            + txt("&#10;Area being shown: ")
            + fldnames(" bold='true'")
            + txt("&#10;")
            + txt(escape(atlas_text.DIMENSION_HOVER_PREFIX))
            + fld("dim_hover")
            + txt("&#10;&#10;")
            + txt(escape(atlas_text.DIMENSIONS_CAVEAT), " italic='true'")
        )

    sheet_dim = worksheet_xml(
        SHEET_DIM_TITLE,
        subtitle=atlas_text.DIMENSIONS_SUBTITLE,
        # Nested rows: the poverty group above the state, so the sheet prints
        # two header blocks -- "Poorest 12" then "Other 25" -- separated by the
        # pane divider: the "clear axis marker between poor states and others"
        # the user asked for (2026-10-22). Same shelf grammar as the pairs
        # board's pane split (FIX_LEDGER P5: dim + field in a paren-plus rows
        # shelf). The group order below in dim_filters pins "Poorest 12" first,
        # since alphabetical order would put "Other 25" on top.
        rows=(f"([{DIM_DS_NAME}].[none:poverty_group:nk] + "
              f"[{DIM_DS_NAME}].[none:state:nk])"),
        cols=f"[{DIM_DS_NAME}].[Multiple Values]",
        mark="Bar",
        encodings=(f"            <color column='[{DIM_DS_NAME}].[:Measure Names]' />\n"),
        ds_name=DIM_DS_NAME,
        ds_caption=DIM_DS_CAPTION,
        deps=dim_deps + state_parameter_deps_xml(dim_bar_order),
        # The Measure Names whitelist (three members only: everything else with
        # a measure role was kept out of the extract at birth) and the manual
        # bar order, both computed above from the frozen lists / main().
        filters=dim_filters(dim_bar_order),
        table_style=dim_table_style(),
        tooltip=dim_tooltip_runs(DIM_DS_NAME),
        # The segment numbers sit on the dark green/orange/blue fills; the first
        # render printed them in the default ink on those fills and they were
        # unreadable. White on all three Okabe-Ito hues is legible (2026-10-22).
        label_colour="#FFFFFF",
    )
    dim_window = (
        "    <!-- The composition sheet: its colour card carries the three\n"
        "         dimension colours; the grammar is the cluster map's, which is\n"
        "         the one right-edge colour card this generator has proven\n"
        "         renders (sheet 1's identical declaration never has; keep\n"
        "         the Analysis, then Legends, then Colour Legend fallback in\n"
        "         mind). -->\n"
        f"    <window class='worksheet' name='{escape(SHEET_DIM_TITLE)}'>\n"
        "      <cards>\n"
        "        <edge name='left'>\n"
        "          <strip size='160'>\n"
        "            <card type='pages' />\n"
        "            <card type='filters' />\n"
        "            <!-- the state selector, 2026-10-25: the SAME parameter the\n"
        "                 Overview dashboard's paramctrl zone drives. The old\n"
        "                 17-of-37 checklist card is retired with the filter it\n"
        "                 bound to: two controls over one row set could not be\n"
        "                 reconciled (docs/SHEET_DIMENSIONS.md, amendment 2). -->\n"
        f"            <card mode='compact' param='[Parameters].[{STATE_PARAM}]' type='parameter' />\n"
        "            <card type='marks' />\n"
        "          </strip>\n"
        "        </edge>\n"
        "        <edge name='top'>\n"
        "          <strip size='2147483647'>\n"
        "            <card type='columns' />\n"
        "          </strip>\n"
        "          <strip size='31'>\n"
        "            <card type='title' />\n"
        "          </strip>\n"
        "        </edge>\n"
        "        <edge name='right'>\n"
        "          <strip size='160'>\n"
        f"            <card pane-specification-id='0' param='[{DIM_DS_NAME}].[:Measure Names]' type='color' />\n"
        "          </strip>\n"
        "        </edge>\n"
        "      </cards>\n"
        "      <viewpoint>\n"
        "        <zoom type='entire-view' />\n"
        "      </viewpoint>\n"
        "    </window>\n"
    )

    # ---- sheet 3c: the KPI board, between the reference tabs and the pairs --
    # The frozen national sheet (docs/SHEET_KPI.md): one row per benchmarked
    # KPI, one Shape mark per reference point (2026-10-23: map silhouettes --
    # world / Africa / Nigeria -- instead of circles; the shapes identify the
    # series and the colour pill stays for the legend), shapes mapped by the
    # ds-level `type='shape'` rule (KP_SHAPE_PALETTE, grammar note there) and
    # embedded in the workbook by shape_pack_xml. Rows in the CSV's own order
    # via the same manual sort dictionary the composition sheet proves
    # (class='manual', quoted buckets, RegionalSalesDashboard's shape). The
    # hover is one pre-formatted string dimension (stage 7); the second tooltip
    # line is the static direction key from atlas_text, so no mark draws a
    # good/bad badge.
    kpi_captions = {
        "kpi": "Indicator",
        "series": "Reference point (2021)",
        # 2026-10-24 word budget: these are the axis title, the Label pill's
        # caption and the tooltip's caption, i.e. the words that print around the
        # marks. "Share of this row's largest reference point" and "Value beside
        # the map" said the same thing twice at length; the subtitle now carries
        # the explanation, the axis just needs its name.
        "pos": "Share of the row's largest reference",
        "pos_label": "Share (one decimal)",
        "hover": "Values",
    }
    # The field's own one-decimal number format (2026-10-23 user pass): the
    # printed labels and the axis ticks read 0.0-1.0, not 0.00-1.00. Same lane
    # as the rank panel's number format -- default-format ON the <column>, in
    # both copies (worksheet deps + datasource), never a style rule (D2E8DA72).
    kpi_formats = {"pos": "0.0"}
    kpi_deps = deps_xml(KP_COLUMNS, kpi_captions, kpi_formats)
    assert len(kpi_order) == 7, (
        f"the KPI board's row order has {len(kpi_order)} rows, expected 7"
    )

    def kpi_filters(order: list[str]) -> str:
        """The KPI rows in the benchmarks table's own order.

        Alphabetical order would put "Child deaths..." before "Poverty
        headcount..." and bury the headline row; the manual dictionary pins the
        CSV's narrative order (poverty first, then health, then living
        standards), the grammar the composition sheet proves for string
        dimensions (class='manual').
        """
        buckets = "".join(
            f"            <bucket>&quot;{escape(row)}&quot;</bucket>\n"
            for row in order
        )
        return (
            f"          <sort class='manual' column='[{KP_DS_NAME}].[none:kpi:nk]' "
            "direction='ASC'>\n"
            "            <dictionary>\n"
            f"{buckets}"
            "            </dictionary>\n"
            "          </sort>\n"
        )

    def kpi_table_style() -> str:
        """The KPI board's workbook-level style rules: axis ticks + header width.

        Ticks: grammar from a real Tableau-authored workbook (hr_rwfd.twb), whose
        axis style-rule carries an `<encoding attr='space' … major-origin='0'
        major-spacing='800' … type='space' />` beside its tick-color formats --
        the serialisation of the axis' manual tick spacing, in data units. For
        a 0-1 share axis the spacing 0.5 should land ticks at 0, 0.5 and 1.
        This grammar was never exercised in this repo: if the workbook fails to
        load or the ticks render unchecked, delete this rule and let Tableau
        pick its default ticks (the fallback documented in SHEET_KPI.md).

        Header width: the row labels carry the direction arrow and are long, so
        the header column needs room or every row prints on three lines
        (2026-10-24 render). The field-scoped width rule is the shape the
        composition sheet already ships and the one recorded there from
        ClinicPerformanceDashboard/FinanceDashboard
        (`<style-rule element='header'><format attr='width' field=… />`), so it
        is packet-sourced rather than guessed. 230 px fits the longest label
        ("Basic drinking water (% of people)") on one line at the sheet's header
        font; narrower windows still wrap, which is what Entire View does.
        """
        return (
            "          <style-rule element='axis'>\n"
            f"            <encoding attr='space' class='0' field='{ref('pos', 'avg', KP_DS_NAME)}' "
            "field-type='quantitative' major-origin='0' major-spacing='0.5' "
            "scope='cols' type='space' />\n"
            "          </style-rule>\n"
            "          <style-rule element='header'>\n"
            f"            <format attr='width' field='[{KP_DS_NAME}].[none:kpi:nk]' "
            "value='230' />\n"
            "          </style-rule>\n"
        )

    def kpi_tooltip_runs() -> str:
        """The runs inside the KPI board's customized tooltip.

        Run 1 is the whole pre-formatted line (stage 7): every raw value, the
        benchmark text and the source, one run, as the time panel ships its
        annotations. Run 2 is the static direction key -- the interpretation
        flips row by row, so the reader is told the rule rather than given a
        per-mark badge. Every run carries at least one character (Tableau
        drops whitespace-only runs; the newline leads run 2 so it is not an
        empty run of its own).
        """
        return (
            f"              <run bold='true'><![CDATA[<{ref('hover', 'dim', KP_DS_NAME)}>]]></run>\n"
            f"              <run italic='true'>&#10;{escape(atlas_text.KPI_TOOLTIP_NOTE)}</run>\n"
        )

    sheet_kpi = worksheet_xml(
        SHEET_KPI_TITLE,
        subtitle=atlas_text.KPI_SUBTITLE,
        rows=f"[{KP_DS_NAME}].[none:kpi:nk]",
        cols=ref("pos", "avg", KP_DS_NAME),
        mark="Shape",
        encodings=(
            f"            <lod column='{ref('hover', 'dim', KP_DS_NAME)}' />\n"
            f"            <color column='{ref('series', 'dim', KP_DS_NAME)}' />\n"
            f"            <shape column='{ref('series', 'dim', KP_DS_NAME)}' />\n"
            # The Label pill carries the pre-formatted one-decimal string, the
            # proven Shape-mark labels-from-a-string-dimension shape (CH24's
            # Legend sheet: shape + text columns beside the same member). With
            # a pill on Label, the printed label is THAT string -- the
            # mark-labels-show rule below just turns the printing on.
            f"            <text column='{ref('pos_label', 'dim', KP_DS_NAME)}' />\n"
        ),
        pane_mark_formats=(("size", KP_SHAPE_SIZE),
                           ("mark-labels-cull", "true")),
        pane_datalabel_attrs=(("color-mode", "auto"), ("font-size", "6")),
        ds_name=KP_DS_NAME,
        ds_caption=KP_DS_CAPTION,
        deps=kpi_deps,
        filters=kpi_filters(kpi_order),
        tooltip=kpi_tooltip_runs(),
        table_style=kpi_table_style(),
    )
    kpi_window = (
        "    <!-- The KPI board: left rail (the proven stack) plus the right-edge\n"
        "         colour card, the composition sheet's shape, which is the one\n"
        "         right-edge colour card this generator has proven renders (sheet\n"
        "         1's identical declaration never has; keep the Analysis / Legends\n"
        "         / Colour Legend fallback in mind, and the pairs-datasource\n"
        "         palette lesson: this datasource's ds-level palette is a packet\n"
        "         check at publish time). -->\n"
        f"    <window class='worksheet' name='{escape(SHEET_KPI_TITLE)}'>\n"
        "      <cards>\n"
        "        <edge name='left'>\n"
        "          <strip size='160'>\n"
        "            <card type='pages' />\n"
        "            <card type='filters' />\n"
        "            <card type='marks' />\n"
        "          </strip>\n"
        "        </edge>\n"
        "        <edge name='right'>\n"
        "          <strip size='160'>\n"
        f"            <card pane-specification-id='0' param='[{KP_DS_NAME}].[none:series:nk]' type='color' />\n"
        "          </strip>\n"
        "        </edge>\n"
        "        <edge name='top'>\n"
        "          <strip size='2147483647'>\n"
        "            <card type='columns' />\n"
        "          </strip>\n"
        "          <strip size='31'>\n"
        "            <card type='title' />\n"
        "          </strip>\n"
        "        </edge>\n"
        "      </cards>\n"
        "      <viewpoint>\n"
        "        <zoom type='entire-view' />\n"
        "      </viewpoint>\n"
        "    </window>\n"
    )

    # ---- sheet 3b: the pairs board, after the time panel --------------------
    # The frozen exploration sheet (docs/SHEET_PAIRS.md): any two continuous
    # measures as one point per state-round, split into the two 2021
    # poverty-group panes, both axes driven by parameter dropdowns. It computes
    # nothing and carries no claim -- the pane cut is on the outcome (the 2021
    # MPI), so slope-like readings within a pane are range-restricted; the
    # subtitle and the hover both say so, and the freeze's "may not say" list
    # is what no future edit can cross. The workbook built here was proven by
    # the packet sequence A1-A6 reported in docs/FIX_LEDGER.md section P.
    sheet_pairs, pairs_window = pairs_worksheet_xml(PAIRS_DEFAULT_X, PAIRS_DEFAULT_Y)

    # ---- sheets 3-5: the reference tab, in three parts ----------------------
    # Where the five spec sheets (dimension breakdown, poverty vs conflict, poverty
    # over time, incidence x intensity) and the party-alignment panel used to be.
    # All of them, the Moran scatter and the "Equity Atlas" dashboard were withdrawn
    # on 2026-10-18 (module docstring). Their numbers still exist -- stages 04, 05
    # and 08 write them, and docs/ carries the two pre-registered results -- and
    # every sentence a reader needs from those five sheets is now a row of this
    # table, which is why withdrawing them cost the atlas no claim.
    reference_tabs = table_dashboards()
    overview_dash, overview_window = overview_dashboard_xml()
    context_dash, context_window = context_dashboard_xml()

    dashboards = ("  <dashboards>\n"
                  + overview_dash
                  + context_dash
                  + "".join(xml for _name, xml in reference_tabs)
                  + "  </dashboards>\n")
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
    # then the words that explain both. 2026-10-24: the Overview dashboard goes
    # FIRST, because a workbook opens on its first window and a reader should land
    # on the page that shows four sheets at once rather than on one of them.
    windows = f"""  <windows source-height='1500'>
{overview_window}{context_window}    <window class='worksheet' name='Where poverty sits'>
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
{dim_window}    <!-- The time panel: its two interactive cards. The checklist over the generated
         Measure Names field is the "measures to watch" picker; the dropdown over
         state is the state picker (the worksheet filter pins Bauchi as the default
         member, so the sheet cannot open blank). The pair is standard grammar:
         <card mode='checklist'/'dropdown' param='[ds].[field]' type='filter' /> as
         ClinicPerformanceDashboard and HRAnalytics serialise it. But the
         Measure Names card had no instance to copy from: no downloaded workbook
         showed the generated field named in a card, so the render test decides.
         The cards declare on the LEFT edge, not the right, after the first render
         proved the point the map's colour-card defect already suggested: in
         packets built by this script, left-edge strips draw and right-edge strips
         do not (Pages/Filters/Marks drew on the map; the declared right colour
         card never has). Which side the rail sits on is cosmetic; that the
         interaction exists is not. The top edge gains the title card so the
         sheet's frozen subtitle line renders. -->
    <window class='worksheet' name='{escape(SHEET_TIME_TITLE)}'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card mode='checklist' param='[{PANEL_DS_NAME}].[:Measure Names]' type='filter' values='database' />
            <card mode='compact' param='[Parameters].[{PANEL_STATE_PARAM}]' type='parameter' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='2147483647'>
            <card type='columns' />
          </strip>
          <strip size='31'>
            <card type='title' />
          </strip>
        </edge>
      </cards>
      <viewpoint>
        <zoom type='entire-view' />
      </viewpoint>
    </window>
{tab_windows}{kpi_window}{pairs_window}  </windows>
"""

    # Seven datasources: six extract-backed and the inline Parameters
    # pseudo-datasource the pairs board's dropdowns read. Each declares the
    # instances of its own sheet only: a datasource must not declare an
    # instance for a field that lives in the other extract (it loads as "the
    # field does not exist", 9CA7205B).
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
        calcs=state_match_calc_xml("      ", with_instance=False),
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
        calcs=state_match_calc_xml("      ", with_instance=False),
    )
    # The time panel's datasource: same shape, with a palette for the generated
    # Measure Names field -- its buckets are the quoted field references of the six
    # whitelist measures, not labels, and the field is referenced bare
    # ([:Measure Names]). Both forms were copied from ClimatechangeprofileNigeria.
    # The row header per pane is the measure caption (panel_captions), so the same
    # single source names the measure in the workbook and in the stage 5 gate.
    panel_ds = datasource_xml(
        PANEL_COLUMNS, PANEL_HYPER, panel_rows,
        PANEL_DS_NAME, PANEL_DS_CAPTION, PANEL_CONN,
        instances=column_instances(sheet_time),
        captions=panel_captions,
        default_formats=panel_formats,
        palette=(
            "Measure Names",
            [(f"[{PANEL_DS_NAME}].[sum:{name}:qk]", colour)
             for name, _caption, colour in atlas_text.PANEL_MEASURES],
            "[:Measure Names]",
        ),
        calcs=panel_state_calc_xml("      ", with_instance=False),
    )
    # The composition sheet's datasource: the same Measure Names palette shape
    # the panel's carries -- quoted column-instance keys for the three share
    # measures, the bare generated-field reference, one colour per area sourced
    # from atlas_text.DIMENSION_SHARES so the workbook and the stage 5 gate
    # cannot disagree. The captions are the Measure Names members' display
    # names (Education / Health / Living standards).
    dim_ds = datasource_xml(
        DIM_COLUMNS, DIM_HYPER, dim_rows,
        DIM_DS_NAME, DIM_DS_CAPTION, DIM_CONN,
        instances=column_instances(sheet_dim),
        captions=dim_captions,
        palette=(
            "Measure Names",
            [(f"[{DIM_DS_NAME}].[sum:{name}:qk]", colour)
             for name, _caption, colour in atlas_text.DIMENSION_SHARES],
            "[:Measure Names]",
        ),
        calcs=state_match_calc_xml(
            "      ", atlas_text.composition_default(dim_bar_order), with_instance=False
        ),
    )
    # The KPI board's datasource: the drawn sheet's 20 marks, with the ds-level
    # palette on `series` (one colour per member, the map/panel/composition
    # shape -- NOT the pairs datasource's failed variant; see the constants
    # block comment). Instances mirror the worksheet's shelves, captions are
    # the same map the worksheet deps carry.
    kpi_ds = datasource_xml(
        KP_COLUMNS, KP_HYPER, kpi_rows,
        KP_DS_NAME, KP_DS_CAPTION, KP_CONN,
        instances=column_instances(sheet_kpi),
        captions=kpi_captions,
        # The one-decimal field format must match the worksheet deps copy --
        # same rule as the captions (Tableau repeats it in both places).
        default_formats=kpi_formats,
        palette=("series", list(atlas_text.KPI_SERIES)),
        # The Shape marks' member -> silhouette mapping, in the same
        # ds-level style rule as the colour palette (grammar note at
        # KP_SHAPE_PALETTE).
        shape_palette=KP_SHAPE_PALETTE,
    )
    # The pairs board's datasource: the panel-atlas join plus the two CASE    # columns appended to the field list (their <column> blocks carry a
    # <calculation> child, which datasource_xml's plain columns don't emit).
    pairs_ds = datasource_xml(
        PAIRS_COLUMNS, PAIRS_HYPER, pairs_rows,
        PAIRS_DS_NAME, PAIRS_DS_CAPTION, PAIRS_CONN,
        # The ds-level instance list is the same block the worksheet deps
        # mirror; every field the sheet places gets its instance in both
        # places, the way the shipped datasources carry them.
        instances=pairs_instance_xml(),
        captions=pairs_captions(),
        # (The ds-level palette mapping poverty_group to one green did NOT
        # load here: with it, both the packet and the full workbook failed to
        # open at all — a grey empty shell, 2026-10-22. Bisect: removed; the
        # colour pill on the sheet + a worksheet table-level rule is what the
        # verified build carries instead. The maps' ds-level palettes render,
        # so this is a pairs-datasource-specific finding to re-investigate at
        # publish time.)
    )
    # Append the two calc <column> blocks right after the plain ones, before the
    # <extract> element: datasource_xml emits <column/>s between <aliases/> and
    # <extract/>. Same two-location rule as the captions.
    aliases_marker = "      <aliases enabled='yes' />\n"
    calc_at_ds = pairs_calc_columns_xml()
    pairs_ds = pairs_ds.replace(aliases_marker, aliases_marker + calc_at_ds, 1)
    parameters_ds = parameters_ds_xml(PAIRS_DEFAULT_X, PAIRS_DEFAULT_Y, dim_bar_order)
    # The KPI silhouettes, embedded in the workbook (see shape_pack_xml); the
    # real tree order puts <external> after the window/dashboard blocks and
    # before the workbook element closes.
    shape_pack = shape_pack_xml()

    return f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook original-version='{VERSION}' source-build='2024.1.0 (20241.24.0212.1000)' source-platform='win' version='{VERSION}' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>
  <datasources>
{poly_ds}{spatial_poly_ds}{panel_ds}{dim_ds}{kpi_ds}{pairs_ds}{parameters_ds}  </datasources>
  <worksheets>
{sheet_map}{sheet_cluster}{sheet_dim}{sheet_time}{sheet_kpi}{sheet_pairs}  </worksheets>
{dashboards}{windows}{shape_pack}</workbook>
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
        # [Parameters].[X axis measure] style references name the inline
        # pseudo-datasource, whose columns are not extract fields; a window card
        # carries the same reference. Both are defined by their own blocks, not
        # by `declared`, so neither can resolve here.
        if token.startswith("[Parameters]."):
            continue
        if parts[0] in {"Multiple Fields", "Multiple Values"} or "generated" in parts[1]:
            continue
        # Measure Names, Tableau's other generated field, is referenced bare --
        # [ds].[:Measure Names], no derivation, no kind. It is declared by
        # Tableau itself, so it cannot resolve against `declared`.
        if parts[0] == "" and parts[1] == "Measure Names":
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
    for ds in ("[federated.0mpipolygons]", "[federated.0mpispatialpoly]",
               "[federated.0mpitrends]", "[federated.0mpipairs]",
               "[federated.0kpiboard]", "[Parameters]"):
        if ds not in xml:
            problems.append(f"datasource reference {ds} never declared")

    # The pairs board's trend line (2026-10-24). Its grammar is not guessable and
    # is taken from Tableau's own TWB schema (PaneSpecification-Trendline-G), so a
    # silently dropped or down-graded element would still load and still render
    # -- just without the line. Gate the four things the sheet promises.
    trends = re.findall(r"<trendline\b[^>]*>", xml)
    if len(trends) != 1:
        problems.append(
            f"expected exactly one <trendline> (the pairs board's), found {len(trends)}"
        )
    else:
        for attr, want in (("fit", "polynomial"), ("degree", "2"),
                           ("enable-confidence-bands", "true"),
                           ("enabled", "true")):
            if f"{attr}='{want}'" not in trends[0]:
                problems.append(f"pairs trendline lost {attr}='{want}': {trends[0]}")
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
    import collections

    atlas_path = PROCESSED / "mpi_atlas_2021.csv"
    poly_path = PROCESSED / "mpi_polygons.csv"
    spatial_path = PROCESSED / "spatial_diagnostics.csv"
    spatial_poly_path = PROCESSED / "spatial_polygons.csv"
    spatial_global_path = PROCESSED / "spatial_global.csv"
    panel_path = PROCESSED / "mpi_trends_panel.csv"
    pairs_path = PROCESSED / "mpi_pairs_148.csv"
    kpi_path = PROCESSED / "kpi_dots.csv"
    for path in (atlas_path, poly_path, spatial_path, spatial_poly_path,
                 spatial_global_path, panel_path, pairs_path, kpi_path):
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
    panel_reader = read(panel_path)
    pairs_reader = read(pairs_path)
    kpi_reader = read(kpi_path)

    # The atlas table is drawn by no sheet any more, but it stays the reference both
    # maps are checked against: it is the source of the band labels, and its 37
    # pcodes are what proves each extract covers the whole country.
    assert len(atlas_reader) == 37, f"atlas has {len(atlas_reader)} rows, expected 37"
    atlas_pcodes = {r["pcode"] for r in atlas_reader}

    # The composition sheet's bar order: states sorted by descending 2021 MPI,
    # computed HERE from the atlas table and shipped as a manual sort
    # dictionary. The MPI value itself is deliberately NOT in the extract --
    # the sort is the only thing it drives. Stage 4 already asserts the
    # shares' identity; re-asserted here against the packaged rows because
    # this extract is what the sheet's whole story rests on.
    dim_bar_order = [
        r["state"]
        for r in sorted(atlas_reader, key=lambda r: -float(r["mpi"]))
    ]
    dim_rows = len(atlas_reader)
    assert len(set(dim_bar_order)) == 37, "the composition bar order lost states"
    for row in atlas_reader:
        shares = [float(row[field]) for field, _cap, _col in atlas_text.DIMENSION_SHARES]
        assert all(0 <= s <= 100 for s in shares), (
            f"{row['state']}: a dimension share outside 0-100"
        )
        assert abs(sum(shares) - 100) < 0.5, (
            f"{row['state']}: dimension shares total {sum(shares):.2f}, expected 100"
        )
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

    # ---- the time panel (docs/SHEET_TIME_PANEL.md is the freeze) -------------
    # 148 rows = 37 states x 4 harmonised rounds. The panel is what the sheet
    # draws, so anything off here would draw wrong: a missing state-year is a
    # broken line, a wrong year set silently re-plots the axis.
    assert len(panel_reader) == 148, f"panel has {len(panel_reader)} rows, expected 148"
    assert {r["survey_year"] for r in panel_reader} == {"2013", "2016", "2018", "2021"}, (
        "the panel's survey years are not the four harmonised rounds"
    )
    assert {r["pcode"] for r in panel_reader} == atlas_pcodes, (
        "the panel does not cover the same 37 states as the atlas"
    )
    per_state = collections.Counter(r["pcode"] for r in panel_reader)
    assert set(per_state.values()) == {4}, (
        "each state must have exactly one row per round in the panel"
    )
    # The whitelist and the red list are the freeze's two halves: every measure
    # the sheet offers must be a real, always-populated column, and none of the
    # fields the freeze excludes may exist in the extract's schema at all.
    panel_header = set(panel_reader[0])
    schema_fields = {name for name, _dt, _role in PANEL_COLUMNS}
    for name, _caption, _colour in atlas_text.PANEL_MEASURES:
        assert name in panel_header, f"{name!r} missing from the panel CSV"
        assert name in schema_fields, f"{name!r} missing from the extract schema"
        for row in panel_reader:
            value = float(row[name])  # raises if a measure cell is blank
            assert value == value, f"NaN in {name} for {row['state']} {row['survey_year']}"
    assert not (schema_fields & PANEL_EXCLUDED), (
        "the freeze's red-list fields must not exist in the extract schema; "
        f"{sorted(schema_fields & PANEL_EXCLUDED)}"
    )
    for hover_field in ("survey", "state", "survey_year",
                        "mpi_change_label", "mpi_change_significant",
                        "deaths_high_label"):
        assert hover_field in panel_header and hover_field in schema_fields, (
            f"hover field {hover_field!r} missing from the panel extract"
        )
    assert atlas_text.PANEL_DEFAULT_STATE in {r["state"] for r in panel_reader}, (
        f"default state {atlas_text.PANEL_DEFAULT_STATE} is not in the panel"
    )
    # The rank columns are recomputed here from the panel's own value columns and
    # compared against what stage 4 stored -- an independent read of the same
    # numbers, so a stage-4 edit that re-points a rank at the wrong source field,
    # or a whitelist that names a column that is not a rank, cannot reach the
    # workbook. The mapping is 04_merge.py's RANK_FIELDS, copied on purpose: a
    # stage-4 change without this copy is exactly what this assert wants to catch.
    RANK_FIELDS: dict[str, str] = {
        "rank_mpi": "mpi",
        "rank_headcount": "headcount_ratio_pct",
        "rank_intensity": "intensity_pct",
        "rank_events": "events_per_100k",
        "rank_deaths": "fatalities_per_100k",
        "rank_temp": "temp_mean_c",
    }
    assert set(RANK_FIELDS) == {name for name, _c, _col in atlas_text.PANEL_MEASURES}, (
        "the sheet's whitelist and the rank map must name the same columns"
    )
    for rank_name, value_name in RANK_FIELDS.items():
        for year in ("2013", "2016", "2018", "2021"):
            yr_rows = [r for r in panel_reader if r["survey_year"] == year]
            yr_rows.sort(key=lambda r: float(r[value_name]), reverse=True)
            recomputed = 0
            for i, row in enumerate(yr_rows):
                if i and float(row[value_name]) != float(yr_rows[i - 1][value_name]):
                    recomputed = i
                assert int(row[rank_name]) == recomputed + 1, (
                    f"{rank_name} in {row['state']} {year} is "
                    f"{row[rank_name]}, recomputation says {recomputed + 1}"
                )

    # ---- the pairs board (docs/SHEET_PAIRS.md is the freeze) ----------------
    # 148 rows: the panel plus the joined atlas constants (stage 4). The menu
    # fields must be populated (a blank cell would draw a state with a missing
    # dot and nothing upstream complains); the group stamp must agree with the
    # atlas; the log columns must satisfy the zero-gridline rule.
    assert len(pairs_reader) == 148, f"pairs CSV has {len(pairs_reader)} rows, expected 148"
    assert {r["pcode"] for r in pairs_reader} == atlas_pcodes, (
        "the pairs CSV does not cover the same 37 states as the atlas"
    )
    group_by_state: dict[str, str] = {}
    for row in pairs_reader:
        previous = group_by_state.setdefault(row["state"], row["poverty_group"])
        assert previous == row["poverty_group"], (
            f"{row['state']} carries two poverty groups: {previous!r}, "
            f"{row['poverty_group']!r}"
        )
    atlas_group = {r["state"]: r["poverty_group"] for r in atlas_reader}
    assert group_by_state == atlas_group, (
        "the pairs CSV's 2021 group stamp disagrees with the atlas table"
    )
    assert len({r["state"] for r in pairs_reader
                if r["poverty_group"] == "Poorest 12"}) == 12, (
        "the pairs panes do not split 12/25"
    )
    schema_pairs = {name for name, _dt, _role in PAIRS_COLUMNS}
    for label, field in PAIRS_MENU:
        assert field in schema_pairs, f"{field!r} on the pairs menu is not in the extract"
        for row in pairs_reader:
            value = float(row[field])   # raises if a menu cell is blank
            assert value == value, (
                f"NaN in {field} for {row['state']} {row['survey_year']}"
            )
    import math as _math
    for row in pairs_reader:
        for raw in ("events_per_100k", "fatalities_per_100k",
                    "fatalities_per_100k_high"):
            logged = "log1p_" + raw
            expected = round(_math.log1p(float(row[raw])), 5)
            assert float(row[logged]) == expected, (
                f"{logged} recompute drifted for {row['state']} {row['survey_year']}"
            )
            if float(row[raw]) == 0:
                assert float(row[logged]) == 0.0, (
                    f"{logged} lost the zero gridline for {row['state']} "
                    f"{row['survey_year']}"
                )

    # ---- the KPI board (docs/SHEET_KPI.md is the freeze) --------------------
    # 20 marks: 7 benchmarked KPIs x their reference points (the headcount row
    # has no sub-Saharan-Africa WDI figure, so 2 marks there). What this gate
    # checks is what would draw wrong: a series the palette has no colour for,
    # a position outside the row's own (0, 1], a row that lost its Nigeria
    # mark, or a hover line that reached the reader empty.
    assert len(kpi_reader) == 20, f"kpi_dots.csv has {len(kpi_reader)} rows, expected 20"
    kp_series = {label for label, _colour in atlas_text.KPI_SERIES}
    # Every member the extract draws must have a silhouette mapped, and every
    # mapped file must exist (shape_pack_xml would fail on a build past this
    # assert anyway, but naming the check here makes the failure read right:
    # a series with no image is a drawn error, not a missing file).
    assert kp_series == {member for member, _img in KP_SHAPE_PALETTE}, (
        "KPI_SERIES members and the shape palette disagree: "
        f"{sorted(kp_series)} vs {sorted(m for m, _ in KP_SHAPE_PALETTE)}"
    )
    kpi_rows_seen: dict[str, set[str]] = {}
    for mark in kpi_reader:
        assert mark["series"] in kp_series, (
            f"series {mark['series']!r} has no colour in atlas_text.KPI_SERIES"
        )
        assert mark["kpi"] in atlas_text.KPI_ROW_LABELS.values(), (
            f"row label {mark['kpi']!r} is not in atlas_text.KPI_ROW_LABELS"
        )
        pos = float(mark["pos"])
        assert 0 < pos <= 1.0, (
            f"{mark['kpi']} / {mark['series']}: pos {pos:.3f} out of (0, 1]"
        )
        assert mark["hover"].strip(), f"{mark['kpi']}: empty hover"
        kpi_rows_seen.setdefault(mark["kpi"], set()).add(mark["series"])
    kp_expected = set(atlas_text.KPI_ROW_LABELS.values())
    assert set(kpi_rows_seen) == kp_expected, (
        "the KPI board's rows and the frozen row labels disagree: "
        f"{sorted(set(kpi_rows_seen) ^ kp_expected)}"
    )
    for kpi, series in kpi_rows_seen.items():
        assert "Nigeria (2021)" in series, f"{kpi}: no Nigeria mark"
        assert len(series) in {2, 3}, f"{kpi}: unexpected mark set {sorted(series)}"
    # SSA is absent exactly where WDI does not publish it: the headcount row.
    ssa_absent = [kpi for kpi, series in kpi_rows_seen.items()
                  if "sub-Saharan Africa (2021)" not in series]
    assert ssa_absent == [atlas_text.KPI_ROW_LABELS[
        "Multidimensional poverty headcount (national)"
    ]], f"unexpected rows without a sub-Saharan Africa mark: {ssa_absent}"
    # Row order: first appearance in the CSV, which is stage 7's narrative
    # order (poverty, then health, then living standards). The manual sort
    # dictionary ships exactly this list.
    kpi_order = list(dict.fromkeys(r["kpi"] for r in kpi_reader))
    assert len(kpi_order) == 7, "the KPI board's row order lost a row"

    declared = (
        {name for name, _type, _role in POLY_COLUMNS}
        | {name for name, _type, _role in SPATIAL_POLY_COLUMNS}
        | {name for name, _type, _role in PANEL_COLUMNS}
        | {name for name, _type, _role in PAIRS_COLUMNS}
        | {name for name, _type, _role in DIM_COLUMNS}
        | {name for name, _type, _role in KP_COLUMNS}
        | {PAIRS_X_CALC, PAIRS_Y_CALC}
        # The Overview's state selector and the time panel's own state parameter:
        # calculated fields no extract holds, but four datasources and four
        # worksheets declare them by name.
        | {STATE_MATCH, PANEL_STATE_MATCH}
    )
    xml = build_workbook(
        spatial_context_line(spatial_global), len(poly_reader),
        len(spatial_poly_reader), len(panel_reader), len(pairs_reader),
        dim_bar_order, dim_rows, len(kpi_reader), kpi_order,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    poly_hyper = OUT_DIR / POLY_HYPER
    poly_n = build_hyper(poly_path, poly_hyper, POLY_COLUMNS)
    spatial_poly_hyper = OUT_DIR / SPATIAL_POLY_HYPER
    spatial_poly_n = build_hyper(spatial_poly_path, spatial_poly_hyper, SPATIAL_POLY_COLUMNS)
    panel_hyper = OUT_DIR / PANEL_HYPER
    panel_n = build_hyper(panel_path, panel_hyper, PANEL_COLUMNS)
    pairs_hyper = OUT_DIR / PAIRS_HYPER
    pairs_n = build_hyper(pairs_path, pairs_hyper, PAIRS_COLUMNS)
    dim_hyper = OUT_DIR / DIM_HYPER
    dim_n = build_hyper(atlas_path, dim_hyper, DIM_COLUMNS)
    kpi_hyper = OUT_DIR / KP_HYPER
    kpi_n = build_hyper(kpi_path, kpi_hyper, KP_COLUMNS)

    problems = validate(xml, declared)
    problems += check_hyper_schema(
        [
            (POLY_HYPER, poly_hyper, POLY_COLUMNS),
            (SPATIAL_POLY_HYPER, spatial_poly_hyper, SPATIAL_POLY_COLUMNS),
            (PANEL_HYPER, panel_hyper, PANEL_COLUMNS),
            (PAIRS_HYPER, pairs_hyper, PAIRS_COLUMNS),
            (DIM_HYPER, dim_hyper, DIM_COLUMNS),
            (KP_HYPER, kpi_hyper, KP_COLUMNS),
        ],
        {
            POLY_HYPER: poly_n,
            SPATIAL_POLY_HYPER: spatial_poly_n,
            PANEL_HYPER: panel_n,
            PAIRS_HYPER: pairs_n,
            DIM_HYPER: dim_n,
            KP_HYPER: kpi_n,
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
        zf.write(panel_hyper, f"Data/{PANEL_HYPER}")
        zf.write(pairs_hyper, f"Data/{PAIRS_HYPER}")
        zf.write(dim_hyper, f"Data/{DIM_HYPER}")
        zf.write(kpi_hyper, f"Data/{KP_HYPER}")

    print(f"XML validated: {len(declared)} columns declared, all field references resolve")
    print(
        f"Extracts validated: {POLY_HYPER} ({poly_n} rows), "
        f"{SPATIAL_POLY_HYPER} ({spatial_poly_n} rows), "
        f"{PANEL_HYPER} ({panel_n} rows), "
        f"{DIM_HYPER} ({dim_n} rows), "
        f"{PAIRS_HYPER} ({pairs_n} rows), "
        f"{KP_HYPER} ({kpi_n} rows) match the declared columns"
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