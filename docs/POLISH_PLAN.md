# Polish plan — cover, watermark, sheet-by-sheet (documented ahead of build)

Status: **planned 2026-10-22**, before build. This is the interview record and
wave plan; every wave amends this doc in its own " Built" note, never silently.
Interview sources: the user's answers of 2026-10-22 (title, watermark,
illustration, polish axes, publishing split). Academic guardrails live in
`docs/CLAIMS.md`, `docs/CAUSAL_DECISION.md`, `docs/SESSION_HANDOFF.md` (D6).

## Goal (the user's words)

"Final polishes": a Nigerian-themed **cover page**, **watermarks**, and a
**sheet-by-sheet polish** pass. Audience: **professionals and
non-professionals** — the cover must land for a scroller in seconds and still
read credible to a technical reader one click deeper; the reference tabs
already carry the plain-language layer, so the cover's job is the doorway.

## Decisions taken at interview

- **Title (locked):** "One Country. Two Realities." Subtitle:
  *"The Multidimensional Poverty Atlas of Nigeria's 37 States."* This is the
  D6 framing (session handoff 2026-10-08) — decided-with-a-rationale, claim-safe.
- **Cover image: an illustration, not a photograph** — northern and southern
  Nigerian women in traditional attire, hugging. The image mirrors the title.
  Rights: an illustration dodges *portrait consent*, NOT copyright — see Risks.
- **Watermark content: a faint map of Nigeria filled in vertical
  green-white-green bands** (the flag). Reach: **cover tab only** — the user
  accepted the reasoning that a faint Nigeria behind the choropleth of Nigeria
  is rendering noise, and data sheets stay clean.
- **Polish axes, all four, in this order:** (1) clear the open defects list,
  (2) uniform sheet language, (3) visual composition pass, (4) non-professional
  reader pass. Each axis feeds the next; waves are one tab each.
- **Publishing split unchanged:** the agent does XML/grammar/render/docs; the
  user does every GUI click and the publish itself.

## What exists (verified)

- The workbook is 8 worksheet tabs + 5 Hyper extracts, loads clean, green
  pairs board verified 2026-10-22 (`43427f5`).
- **No dashboard has ever been built by this generator.** Every tab is a
  worksheet window. A cover with an image + text zones is **dashboard
  grammar** — windows `class='dashboard'`, floating/tiled zones, image
  objects. Proven shapes must be copied from real dashboard workbooks already
  on disk (ref: HR Analytics, Finance Dashboard, Ode to Cowbell — the last has
  exactly the flavour wanted: fan art, credit lines, playful cover) and
  packet-verified before the shipped twb carries any of it.
- Real-workbook conventions already mined: byline format
  "Viz by: … || Project: … || Source: …" (Ode to Cowbell), dashboard-window
  names as hero titles (HR/KPI), image-in-twbx embedding (to verify which of
  the refs embed images and how).
- The watermark asset is composed once (Python/PIL, or as part of the cover
  illustration edit) and lives under `tableau/assets/` next to the twb, so
  stage 6 can package it. Single-sourced paths and colours from
  `scripts/atlas_text.py` (`COVER_*`, `WATERMARK_*`).

## Waves

Wave 0 — **Packet A7: prove the dashboard grammar.** One floating image
object + one text zone on an empty dashboard, copied from a real workbook,
render-verified in Tableau Public 2026.2. Nothing lands in the shipped twb
before this packet passes. Also verifies: image files actually package into a
twbx and survive the round-trip.
Wave 1 — **The cover tab.** Title, subtitle, illustration, credit line, faint
Nigeria-flag watermark behind. Becomes tab 1 (all existing tabs shift one);
tab-order is a window-list edit, verified by render. Alt text written same
wave. Gate: `0_cover.png` (stage 5's preview list gains the cover).
Wave 2 — **Defects sweep, sheet 1 & 2** (the maps): the colour-legend defect
(`docs/PUBLISH.md` §"colour legend does not draw"), axis headers + Entire
View leftovers, alt text.
Wave 3 — **Defects sweep, composition + time panel + pairs:** the Poorest-12
header wrap (tried-and-failed width rule recorded in FIX_LEDGER D-053 — new
attempt carries a new mechanism, not a rerun), the pairs open-state finding
(documented, not yet reproduced deliberately), tooltip spot-checks.
Wave 4 — **Uniform sheet language:** one title/subtitle grammar via
`atlas_text.py` helpers; every hover carries the same pattern (bold state
line + formatted values + caveat where the sheet makes a claim).
Wave 5 — **Visual composition pass:** pane sizes, spacing, label collisions,
colour balance — per tab, with before/after captures in `docs/preview/`.
Wave 6 — **Non-professional reader pass:** one-line takeaway per subtitle,
units spelled out (per 100k = per 100,000 people, once on each sheet), every
term used on a sheet resolvable in `What the words mean`.
Wave 7 — **Publish preparation:** README/PROJECT line, PUBLISH.md updated end
to end, then the GUI publish + post-publish image checks via the tableau MCP
server.

Each wave: build → packet render → full-workbook load → docs note → commit.

## The cover's guardlist (may not say)

The hug illustration shows a northern and a southern woman; it must never be
composited into a claim. On/around the cover:
- never "north vs south" as a *data* statement — the atlas's phrase is
  "poorest states vs the rest" (all 12 states with MPI > 0.20 sit in the two
  northern bands; AGENTS.md's correction table). The title's "Two Realities"
  is the D6 framing and stops at framing;
- the cover carries **at most one number**, with its interval, from a claim
  `docs/CLAIMS.md` permits — default: the national poverty headcount with its
  95% interval;
- no party/federal-alignment implication anywhere on the cover;
- the credit line names data vintages exactly ("OPHI/NBS 2021 harmonised
  series, accessed …"), never a vague "public data".

## Open questions (UNKNOWN = not guessed)

- **Deadline:** none given at interview. UNKNOWN — waves proceed in order;
  if a live date appears, re-order waves 2-6 against it.
- **Illustration source/licence:** UNKNOWN. The asset ships under the user's
  name on Tableau Public; wave 1 cannot pass until provenance is recorded in
  this file (creator, licence, where obtained). A placeholder is
  acceptable during builds; the *published* cover is not.
- **The illustration's look** beyond its content (attire detail, composition,
  style) is the user's call at asset time — the plan only fixes its content
  requirements (two women, north + south attire, embrace, flag-tone palette).
- Watermark opacity/scale — fixed by render iteration in wave 1, not
  pre-decided.

## Risks

- **Dashboard + image-object grammar is virgin territory here.** Every prior
  sheet was a worksheet; failure modes will be load-breakers until the packet
  proves otherwise, and the pairs-board lesson (D-054) says the schema
  rejects *and silently ignores* talk it doesn't accept — only renders decide.
- **Cover-first tab reordering** touches the window list every other sheet
  sits in; a botched order shows as a blank first tab. Packet-first.
- **Image files in the twbx** must survive packaging and any GUI save by the
  user (the publish flow re-saves; a Tableau save rewrites the twb and could
  re-relative paths). Verified in wave 1, re-verified after the user's first
  publish save.
- **Consistency drift:** four polish axes over seven waves can drift texts
  from the gate PNGs; the wave order (language before composition before
  reader pass) is chosen so each wave touches `atlas_text.py` once and the
  gate re-renders everything each run.
- The watermark's green-white-green uses the FLAG green (`#008751` ideal),
  deliberately not the atlas's data green `#009E73` — decoration must not
  borrow a data colour. Encode both in `atlas_text.py` with that comment.

## Smallest useful version

Cover tab live (packet proved, tab first, illustration + title + credit +
watermark) and the defects sweep done — that is the polish that changes what
a visitor sees most per hour spent. Waves 4-6 raise the floor every
remaining hour.
