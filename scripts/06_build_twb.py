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
  1  MPI by state            filled map on the geographic role
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
import sys
import zipfile
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from common import PROCESSED, REPO_ROOT

DS_NAME = "federated.0mpiatlas2021"
DS_CAPTION = "Nigeria MPI Atlas"
CONN_NAME = "textscan.0mpiatlas2021"
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
    ("events_per_100k", "real"),
    ("fatalities_per_100k", "real"),
    ("conflict_exposure_index", "real"),
    ("temp_mean_c", "real"),
    ("precip_total_mm", "real"),
    ("temp_anomaly_c", "real"),
    ("precip_anomaly_pct", "real"),
    ("baseline_temp_c", "real"),
    ("baseline_precip_mm", "real"),
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
    "indicators_missing",
    "survey",
    "n_indicators",
    "survey_year",
]

PANEL_MEASURES = ["mpi", "headcount_ratio_pct", "intensity_pct", "events", "fatalities",
                  "events_per_100k", "conflict_exposure_index", "temp_mean_c",
                  "temp_anomaly_c", "precip_anomaly_pct"]
PANEL_DIMS = ["pcode", "state", "survey_year", "survey"]


def ref(column: str, kind: str) -> str:
    """Build a Tableau field reference such as [ds].[sum:mpi:qk]."""
    if kind == "dim":
        return f"[{DS_NAME}].[none:{column}:nk]"
    agg = "sum" if kind == "sum" else "avg"
    return f"[{DS_NAME}].[{agg}:{column}:qk]"


def col_block(name: str, datatype: str, role: str, *, geographic: bool = False,
              default_agg: str = "") -> str:
    extra = f" default-aggregation-type='{default_agg}'" if default_agg else ""
    if datatype == "string":
        type_attr = "nominal"
    elif datatype == "integer":
        type_attr = "ordinal"
    else:
        type_attr = "quantitative"
    semantic = ""
    if geographic:
        # Assign the Nigeria admin-1 role so Tableau's built-in geocoding draws
        # state polygons instead of treating the name as a plain string.
        semantic = (
            "<semantic-values>"
            "<semantic-value key='[Country].[Name]' value='&quot;Nigeria&quot;' />"
            "</semantic-values>"
        )
    return (
        f"      <column caption='{escape(name)}' datatype='{datatype}' name='[{escape(name)}]' "
        f"role='{role}' type='{type_attr}'{extra}>{semantic}</column>\n"
    )


def datasource_xml(columns: list[tuple[str, str, str]], csv_filename: str, row_count: int) -> str:
    """One datasource over a packaged CSV, with every column declared explicitly."""
    ordinals = []
    cols = []
    for i, (name, datatype, role) in enumerate(columns):
        ordinals.append(
            f"                  <column datatype='{datatype}' name='{escape(name)}' ordinal='{i}' />"
        )
        cols.append(col_block(name, datatype, role, geographic=(name == "state")))

    last_col = chr(ord("A") + (len(columns) - 1) % 26) if len(columns) <= 26 else "A"
    grid = f"A1:{last_col}{row_count + 1}"
    remote_types = {"string": "129", "integer": "20", "real": "5"}
    metadata = []
    for name, datatype, _role in columns:
        metadata.append(
            "            <metadata-record class='column'>\n"
            f"              <remote-name>{escape(name)}</remote-name>\n"
            f"              <remote-type>{remote_types[datatype]}</remote-type>\n"
            f"              <local-name>[{escape(name)}]</local-name>\n"
            f"              <parent-name>[{escape(csv_filename)}]</parent-name>\n"
            f"              <remote-alias>{escape(name)}</remote-alias>\n"
            f"              <ordinal>{columns.index((name, datatype, _role))}</ordinal>\n"
            f"              <family>{'quantitative' if datatype != 'string' else 'nominal'}</family>\n"
            f"              <local-type>{datatype}</local-type>\n"
            "              <aggregation>Sum</aggregation>\n"
            "            </metadata-record>"
        )

    col_tags = "\n".join(ordinals)
    meta_tags = "\n".join(metadata)
    col_blocks = "".join(cols)
    return f"""    <datasource caption='{DS_CAPTION}' inline='true' name='{DS_NAME}' version='{VERSION}'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='{csv_filename}' name='{CONN_NAME}'>
            <connection class='textscan' directory='Data' filename='{csv_filename}'>
              <relation name='{csv_filename}' table='[{csv_filename}#csv]' type='table'>
                <columns gridOrigin='{grid}' header='yes' outcome='2'>
{col_tags}
                </columns>
              </relation>
              <metadata-records>
{meta_tags}
              </metadata-records>
            </connection>
          </named-connection>
        </named-connections>
        <relation connection='{CONN_NAME}' name='{csv_filename}' table='[{csv_filename}#csv]' type='table' />
        <cols>
          <map key='[state]' value='[Data].[state]' />
        </cols>
        <metadata-records>
{meta_tags}
        </metadata-records>
      </connection>
      <aliases enabled='yes' />
{col_blocks}      <layout dim-ordering='alphabetic' dim-percentage='0.5' measure-ordering='alphabetic' measure-percentage='0.4' show-structure='true' />
      <semantic-values>
        <semantic-value key='[Country].[Name]' value='&quot;Nigeria&quot;' />
      </semantic-values>
    </datasource>
"""


def deps_xml(columns: list[tuple[str, str, str]]) -> str:
    """The per-worksheet column block real Tableau writes.

    Tableau repeats the datasource's columns inside every worksheet that uses it
    (<datasource-dependencies>). Omitting it still opens in Tableau, but shelf
    fields then cannot be resolved by workbook analysers -- and this project's
    only structural check is an analyser.
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
                  deps: str = "") -> str:
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
    return f"""    <worksheet name='{escape(name)}'>
      <layout-options>
        <title>
          <formatted-text>
            <run bold='true' fontsize='13'>{escape(name)}</run>
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
        <panes>
{pane}        </panes>
        <rows>{rows}</rows>
        <cols>{cols}</cols>
      </table>
    </worksheet>
"""


PANEL_DS_NAME = "federated.0mpipanel2021"
PANEL_DS_CAPTION = "Nigeria MPI trends panel"
PANEL_CONN = "textscan.0mpipanel2021"


def build_workbook(atlas_columns: list[tuple[str, str, str]], atlas_rows: int,
                   panel_columns: list[tuple[str, str, str]], panel_rows: int) -> str:
    atlas_deps = deps_xml(atlas_columns)
    panel_deps = deps_xml(panel_columns)

    # ---- sheet 1: filled map ------------------------------------------------
    sheet_map = worksheet_xml(
        "MPI by state",
        rows="",
        cols=f"{ref('state', 'dim')} / {ref('lat', 'sum')} + {ref('lon', 'sum')}",
        mark="Map",
        encodings=(
            f"            <lod column='{ref('state', 'dim')}' />\n"
            f"            <color column='{ref('mpi', 'sum')}' />\n"
        ),
        deps=atlas_deps,
    )

    # ---- sheet 2: stacked bar ----------------------------------------------
    sheet_bar = worksheet_xml(
        "Dimension breakdown",
        rows=f"{ref('contrib_health_pct', 'sum')} + {ref('contrib_education_pct', 'sum')} "
             f"+ {ref('contrib_living_standards_pct', 'sum')}",
        cols=ref("state", "dim"),
        mark="Bar",
        encodings=(
            f"            <color column='{ref('contrib_health_pct', 'sum')}' />\n"
            f"            <text column='{ref('mpi', 'sum')}' />\n"
        ),
        deps=atlas_deps,
    )

    # ---- sheet 3: poverty vs conflict --------------------------------------
    sheet_scatter = worksheet_xml(
        "Poverty vs conflict",
        rows=ref("conflict_exposure_index", "sum"),
        cols=ref("mpi", "sum"),
        mark="Circle",
        encodings=(
            f"            <lod column='{ref('state', 'dim')}' />\n"
            f"            <color column='{ref('quadrant', 'dim')}' />\n"
            f"            <text column='{ref('state', 'dim')}' />\n"
            f"            <size column='{ref('fatalities', 'sum')}' />\n"
        ),
        deps=atlas_deps,
    )

    # ---- sheet 4: poverty over time ----------------------------------------
    sheet_trend = worksheet_xml(
        "Poverty over time",
        rows=f"[{PANEL_DS_NAME}].[sum:mpi:qk]",
        cols=f"[{PANEL_DS_NAME}].[none:survey_year:nk] + [{PANEL_DS_NAME}].[none:state:nk]",
        mark="Line",
        encodings=(
            f"            <lod column='[{PANEL_DS_NAME}].[none:state:nk]' />\n"
        ),
        deps=panel_deps,
        ds_name=PANEL_DS_NAME,
        ds_caption=PANEL_DS_CAPTION,
    )

    # ---- sheet 5: incidence x intensity ------------------------------------
    sheet_quadrant = worksheet_xml(
        "Incidence vs intensity",
        rows=ref("intensity_pct", "sum"),
        cols=ref("headcount_ratio_pct", "sum"),
        mark="Circle",
        encodings=(
            f"            <lod column='{ref('state', 'dim')}' />\n"
            f"            <color column='{ref('quadrant', 'dim')}' />\n"
            f"            <text column='{ref('state', 'dim')}' />\n"
            f"            <size column='{ref('mpi_poor_thousands', 'sum')}' />\n"
        ),
        deps=atlas_deps,
    )

    dashboards = """  <dashboards>
    <dashboard name='Equity Atlas'>
      <layout-options>
        <title>
          <formatted-text>
            <run bold='true' fontsize='16'>Nigeria Multidimensional Poverty Equity Atlas</run>
            <run fontsize='10'>  MICS 2021 &#183; 36 states + FCT</run>
          </formatted-text>
        </title>
      </layout-options>
      <style />
      <size maxheight='1400' maxwidth='1600' minheight='1400' minwidth='1600' />
      <zones>
        <zone h='140000' id='3' type-v2='layout-basic' w='160000' x='0' y='0'>
          <zone h='52000' id='4' name='MPI by state' w='160000' x='0' y='62000' />
          <zone h='62000' id='5' name='Dimension breakdown' w='58000' x='0' y='0' />
          <zone h='62000' id='6' name='Poverty vs conflict' w='52000' x='58000' y='0' />
          <zone h='62000' id='7' name='Incidence vs intensity' w='50000' x='110000' y='0' />
          <zone h='78000' id='8' name='Poverty over time' w='160000' x='0' y='62000' />
        </zone>
      </zones>
    </dashboard>
  </dashboards>
"""

    windows = """  <windows source-height='1400'>
    <window class='worksheet' name='MPI by state'>
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
    <window class='worksheet' name='Dimension breakdown'>
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
        <viewpoint name='MPI by state' />
        <viewpoint name='Dimension breakdown' />
        <viewpoint name='Poverty vs conflict' />
        <viewpoint name='Poverty over time' />
        <viewpoint name='Incidence vs intensity' />
      </viewpoints>
      <active id='-1' />
    </window>
  </windows>
"""

    atlas_ds = datasource_xml(atlas_columns, "mpi_atlas_2021.csv", atlas_rows)
    panel_ds = datasource_xml(panel_columns, "mpi_trends_panel.csv", panel_rows)
    panel_ds = panel_ds.replace(DS_NAME, PANEL_DS_NAME).replace(CONN_NAME, PANEL_CONN)

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


def check_csv_alignment(xml: str) -> list[str]:
    """Confirm declared column ordinals match the packaged CSV header order.

    This is the failure that would actually hurt: a mismatch between
    <column ordinal='N'> and the real header position would silently attach the
    wrong field to every visual, and nothing else in the pipeline would notice,
    because Tableau reports no error for a mis-declared column order.
    """
    import re

    problems: list[str] = []
    for filename in ("mpi_atlas_2021.csv", "mpi_trends_panel.csv"):
        csv_path = PROCESSED / filename
        with csv_path.open(newline="", encoding="utf-8-sig") as fh:
            header = next(csv.reader(fh))
        block = re.search(
            rf"filename='{re.escape(filename)}'.*?<columns[^>]*>(.*?)</columns>", xml, re.S
        )
        if block is None:
            problems.append(f"no <columns> block found for {filename}")
            continue
        declared = re.findall(r"<column datatype='[^']+' name='([^']+)' ordinal='(\d+)' />", block.group(1))
        if len(declared) != len(header):
            problems.append(
                f"{filename}: declares {len(declared)} columns but the CSV has {len(header)}"
            )
            continue
        for position, (name, declared_ordinal) in enumerate(
            sorted(declared, key=lambda kv: int(kv[1]))
        ):
            if declared_ordinal != str(position):
                problems.append(
                    f"{filename}: {name!r} declares ordinal {declared_ordinal}, "
                    f"expected {position}"
                )
            if header[position] != name:
                problems.append(
                    f"{filename}: ordinal {position} declared {name!r} "
                    f"but CSV header has {header[position]!r}"
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

    problems = validate(xml, declared)
    problems += check_csv_alignment(xml)
    if problems:
        print("WORKBOOK VALIDATION FAILED")
        for p in problems:
            print("  -", p)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    twb_path = OUT_DIR / "Nigeria-MPI-Equity-Atlas.twb"
    twb_path.write_text(xml, encoding="utf-8")

    twbx_path = OUT_DIR / "Nigeria-MPI-Equity-Atlas.twbx"
    with zipfile.ZipFile(twbx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(twb_path, twb_path.name)
        # The .twb references the CSVs relative to the package root.
        zf.write(atlas_path, "Data/mpi_atlas_2021.csv")
        zf.write(panel_path, "Data/mpi_trends_panel.csv")

    print(f"XML validated: {len(declared)} columns declared, all field references resolve")
    print("CSV alignment validated: declared ordinals match the packaged CSV headers")
    print(f"wrote {twb_path.relative_to(REPO_ROOT)} ({twb_path.stat().st_size/1024:.0f} KB)")
    print(f"wrote {twbx_path.relative_to(REPO_ROOT)} ({twbx_path.stat().st_size/1024:.0f} KB)")
    with zipfile.ZipFile(twbx_path) as zf:
        print("package contents:")
        for n in zf.namelist():
            print(f"   {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())