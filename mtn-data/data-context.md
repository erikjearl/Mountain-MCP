# Mountain Project Data — Context for AI

This document explains what the data in this folder is, where it came from, how it is structured, and what questions it can answer. Read this before writing any query, tool, or analysis against these CSVs.

---

## What is Mountain Project?

Mountain Project (mountainproject.com) is the largest community-maintained rock climbing database in North America. Climbers use it to look up routes (name, grade, type, description) and log their ascents ("ticks") with style, date, and notes.

A **tick** represents one climber completing one ascent of one route on one date. Routes accumulate ticks over years — tick counts are a proxy for real-world popularity, not quality.

---

## Three-Table Data Model

Everything in this dataset is built from three tables that join in a chain:

```
areas  ──────────────────────────────────────────────────────────────────
  AreaID (PK) │ Name              │ ParentID  │ FullPath
  ─────────────┼───────────────────┼───────────┼────────────────────────
  106621111    │ Sentinel - W Face │ 105720693 │ California > ... > Sentinel - W Face

routes  ─────────────────────────────────────────────────────────────────
  Route (PK)        │ RouteID   │ Name             │ Grade  │ Type │ Length │ Pitches │ AreaID (FK)
  ───────────────────┼───────────┼──────────────────┼────────┼──────┼────────┼─────────┼────────────
  illusion-dweller  │ 105722065 │ Illusion Dweller │ 5.10b  │ Trad │ 100 ft │ 1       │ 106621111

ticks  ──────────────────────────────────────────────────────────────────
  Route (FK)        │ Name       │ Date         │ Details
  ───────────────────┼────────────┼──────────────┼────────────────────────────────────
  illusion-dweller  │ Erik Earl  │ Apr 21, 2026 │ Apr 21, 2026 ·  Lead / Onsight.
```

**Join chain:** `ticks.Route` → `routes.Route` → `routes.AreaID` → `areas.AreaID`

- **Ticks** are the primary unit of activity — one row per climber per ascent per route.
- **Routes** add metadata: grade, type, wall location, pitch count.
- **Areas** add geographic grouping: which wall, which section of the crag.

**What the ticks file alone cannot tell you** — for any of the following you must join to routes (and optionally areas):

| Question | Requires |
|---|---|
| Is this route Trad, Sport, Boulder, or TR? | `routes.Type` |
| What grade is this route? | `routes.Grade` |
| How many pitches does this route have? | `routes.Pitches` |
| Which wall or sub-area is this route on? | `routes.AreaID` → `areas.Name` |
| What is the full geographic path (state → crag → wall)? | `routes.AreaID` → `areas.FullPath` |

**Practical example:** If you open `ticks_BLACK_MOUNTAIN_20260514.csv` and want to know whether the activity is mostly bouldering or sport climbing, you cannot determine that from the ticks file. Load `routes_BLACK_MOUNTAIN_20260514.csv` and join on `Route` to get `Type` per tick. Then load `areas_BLACK_MOUNTAIN_20260514.csv` and join on `AreaID` to understand which wall each route sits on.

---

## Mountain Project URL Structure

Route IDs and slugs both come from Mountain Project URLs. Understanding this helps interpret the data.

| Page type | URL pattern | Example |
|---|---|---|
| Area page | `/area/<id>/<name>` | `/area/105788031/tahquitz` |
| Route page | `/route/<id>/<name>` | `/route/105722065/illusion-dweller` |
| Stats page (ticks) | `/route/stats/<id>/<name>` | `/route/stats/105722065/illusion-dweller` |

- **Route ID** — Numeric, stable. The slug (name portion) can change if someone renames a route on Mountain Project, but the ID never changes. Stored as `RouteID` in the routes CSV.
- **Route slug** — The last path segment, e.g. `illusion-dweller`. This is the join key between ticks and routes — stored as `Route` in both CSVs.
- **Area ID** — Numeric identifier for each geographic area (crag, wall, sub-wall). Hierarchical: a crag contains walls, walls contain routes.

To construct a direct Mountain Project link to a route: `https://www.mountainproject.com/route/<RouteID>/<Route>`

---

## Folder Structure

```
mtn-data/
├── ticks/
│   └── ticks_<CRAG>_<YYYYMMDD>.csv     ← one file per crag per scrape run
├── routes/
│   ├── routes_<CRAG>_<YYYYMMDD>.csv    ← route metadata, one file per crag
│   └── areas/
│       └── areas_<CRAG>_<YYYYMMDD>.csv ← area hierarchy, one file per crag
```

**Naming convention:** `<CRAG>` is a short key (e.g., `TAHQUITZ`, `JTREE_CENTRAL`). `<YYYYMMDD>` is the scrape date. When multiple files exist for the same crag, use the most recent date.

**One crag = one set of three CSVs.** Always use ticks, routes, and areas files with the same `<CRAG>_<YYYYMMDD>` suffix together. Route slugs can collide across crags (two crags can both have a route named `the-crack`) — never mix files from different crags in a join.

---

## CSV Schemas

### `ticks/ticks_<CRAG>_<YYYYMMDD>.csv`

```
Route, Name, Date, Details
```

| Column | Type | Description |
|---|---|---|
| `Route` | string | URL slug of the route, e.g. `illusion-dweller`. Foreign key → `routes.Route`. |
| `Name` | string | Mountain Project username of the climber who logged the tick. |
| `Date` | string | Date of the ascent in `"Mon DD, YYYY"` format, e.g. `"Apr 21, 2026"`. |
| `Details` | string | Raw text from the Mountain Project stats page. Contains date (repeated), optional pitch count, style tag, and optional free-text notes. |

#### Details field format

The `Details` string always begins with the date, followed by an optional pitch count and style tag:

```
<Date> · [N pitches. ] <Style>[. <notes>]
<Date> • No names/notes
<Date>
```

- Separator after date: `·` (U+00B7 middle dot) or `•` (U+2022 bullet).
- The date is always present and repeats the `Date` column — Mountain Project embeds it in the details text.
- Pitch count (`N pitches.`) appears **before** the style tag when present.
- `• No names/notes` is Mountain Project's placeholder when the climber entered no note.
- Date-only entries (no separator, no style) occur occasionally.

**Concrete examples:**
```
Apr 21, 2026 ·  Lead / Redpoint. Cold day, bring doubles on #2.
Apr 4, 2026 · 4 pitches.  Lead / Onsight. Lead with Casey. Fun day!
Apr 18, 2026 • No names/notes
Dec 30, 2026 ·  TR.
Mar 1, 2026 ·  Follow.
Sep 29, 2025 ·  Lead.
Sep 5, 2025
```

**Known style tags:** `Lead / Onsight`, `Lead / Flash`, `Lead / Redpoint`, `Lead / Pinkpoint`, `Lead / Fell/Hung`, `Lead` (no sub-style), `Follow`, `TR`, `Solo`, `Boulder`.

**Parsing the Details field:**
1. Strip the date prefix and separator with: `^[A-Z][a-z]+ \d{1,2}, \d{4}\s*[·•]\s*`
2. Extract pitch count (tick-level, how many pitches this climber did on this visit): `(\d+)\s+pitch` — if absent, default to **1 for roped routes, 0 for boulders** (this is different from the route-level `Pitches` column, which always defaults to 1).
3. Match style against the known style tags above, longest-first.
4. Everything after the style tag and period is free-text notes.

---

### `routes/routes_<CRAG>_<YYYYMMDD>.csv`

```
Route, RouteID, Name, Grade, Type, Length, Pitches, AreaID
```

| Column | Type | Description |
|---|---|---|
| `Route` | string | URL slug. Primary key. Joins to `ticks.Route`. |
| `RouteID` | string | Mountain Project numeric route ID, e.g. `105722065`. Stable across slug renames. Use to build a direct MP link: `mountainproject.com/route/<RouteID>/<Route>`. |
| `Name` | string | Full route name, e.g. `Illusion Dweller`. |
| `Grade` | string | `5.10b` (YDS) for roped routes, `V3` (V-scale) for boulders. |
| `Type` | string | `Trad`, `Sport`, `Boulder`, `TR`, or combinations like `Trad, Sport`. See type values below. |
| `Length` | string | Route length in feet, e.g. `100 ft`. Empty when Mountain Project has no length listed. |
| `Pitches` | integer | **Route-level** pitch count — how many pitches the route has in total. Parsed from Mountain Project (e.g. `Trad, 500 ft, 4 pitches` → 4). Defaults to `1` when not stated, for both single-pitch roped routes and boulder problems. This is distinct from the tick-level pitch count in `Details`, which is how many pitches a specific climber did on a specific visit. |
| `AreaID` | integer | Mountain Project area ID of the route's immediate parent (the wall or sub-area). Foreign key → `areas.AreaID`. |

**Type values:**
- `Trad` — leader places removable gear (cams, nuts) into cracks
- `Sport` — leader clips pre-drilled bolts
- `Boulder` — unroped boulder problem; no length, no pitched ascent
- `TR` — top-rope only; no lead anchors exist on the route
- `Trad, Sport` — mixed (bolts and gear placements)
- `Alpine`, `Aid` — less common; mountaineering or aid climbing

**Grade ordering:** YDS grades are ordinal, not alphabetical. Sort order: `5.8 < 5.9 < 5.10a < 5.10b < 5.10c < 5.10d < 5.11a`. String sorting gives wrong results (`5.9 > 5.10a` alphabetically). Use a grade-to-number conversion before sorting or bucketing.

---

### `routes/areas/areas_<CRAG>_<YYYYMMDD>.csv`

```
AreaID, Name, ParentID, FullPath
```

| Column | Type | Description |
|---|---|---|
| `AreaID` | integer | Mountain Project numeric area ID. Primary key. |
| `Name` | string | Area display name, e.g. `Sentinel - W Face`. |
| `ParentID` | integer | Parent area's ID. Empty for top-level geography (e.g., "California"). |
| `FullPath` | string | Full breadcrumb from top geography down to this area, e.g. `California > Joshua Tree NP > Hidden Valley Area > Real Hidden Valley > Sentinel > Sentinel - W Face`. |

One row per unique area encountered across all routes in the crag. A crag with 300 routes typically has 20–40 unique areas (many routes share the same wall). The areas table does not contain every Mountain Project area — only the ones that appear as parent areas for the scraped routes.

---

## What the Data Can Answer

**With ticks only:**
- Who are the most active climbers at a crag?
- Which routes get the most traffic overall or in a date range?
- How many pitches has a climber logged? (extract pitch count from `Details`, weight by it)
- What's the trend in activity over time?

**With ticks + routes:**
- What grade range sees the most traffic? (join on `Grade`)
- Are Trad or Sport routes more popular at this crag?
- Which routes are onsighted most often vs. fell/hung? (filter `Details` style)
- What is the hardest route with the most ticks? (popularity vs. difficulty)
- For multi-pitch routes, how do pitch-weighted ascents compare to raw tick counts? (use `routes.Pitches` as the weight when a tick's `Details` has no explicit pitch count)
- How does pitch count (`Pitches`) correlate with tick volume? (are long routes or short routes more popular?)

**With ticks + routes + areas:**
- Which wall (sub-area) is the busiest?
- What's the grade distribution of routes being climbed in a specific area?
- Which area has the most unique climbers vs. repeat visitors?
- Where do climbers go to warm up at this crag? (lower grades, high tick counts by area)

**With RouteID:**
- Construct a direct Mountain Project link for any route: `https://www.mountainproject.com/route/<RouteID>/<Route>`

---

## Key Caveats and Data Limitations

**Ticks are self-reported.** Not every climber logs ascents on Mountain Project. Tick counts undercount real traffic. Relative comparisons (route A vs. route B) are more reliable than absolute counts.

**Popular routes are capped at ~250 ticks per scrape.** Mountain Project's stats page renders a limited number of ticks before requiring a scroll or pagination action. The scraper captures the initial render only, so any route with more than ~250 ticks in the dataset is almost certainly truncated. The ticks collected are the most recent ones (Mountain Project displays newest-first). Approximately 7% of routes in the current dataset hit this ceiling. Historical tick data for high-traffic routes is incomplete.

**Private ticks are excluded.** Mountain Project allows private ticks that don't appear on the public stats page. The scraper cannot see them.

**Route slug collisions across crags.** The `Route` slug is unique within a crag but not globally. Always scope joins to a single crag's CSV set.

**Scrape date matters.** Each CSV is a snapshot at the time of the scrape. The filename's `<YYYYMMDD>` tells you when data was collected. New ticks logged after the scrape date are not included.

**Pitches defaults to 1, even for boulders.** The `Pitches` column in the routes CSV defaults to 1 when Mountain Project does not state a pitch count. Boulder problems are not pitched climbs, but they are stored as `Pitches = 1` rather than 0. When using `Pitches` for pitch-weighted analysis, consider filtering out boulders (`Type` contains `Boulder`) to avoid inflating pitch counts.

**Empty Type and Length fields are valid.** Some routes on Mountain Project have no type or no length set — these appear as empty strings, not errors.

---

## Crags in This Dataset

| Key | Location | Character |
|---|---|---|
| `TAHQUITZ` | Idyllwild, CA | Granite multi-pitch trad. Historic; where YDS was invented. |
| `SUICIDE_ROCK` | Idyllwild, CA | Granite trad/sport, adjacent to Tahquitz. |
| `JTREE_CENTRAL` | Joshua Tree NP, CA | Granite crack climbing, high desert. |
| `JTREE_HV` | Joshua Tree NP, CA | Hidden Valley sector — most popular JTree area. |
| `MISSION_GORGE` | San Diego, CA | Sport-dominant, single-pitch. |
| `MT_WOODSON` | Poway, CA | Granite bouldering and sport. |
| `MALIBU_CREEK` | Malibu, CA | Conglomerate, mixed sport/trad. |

Additional crags defined in the scraper but not yet collected appear in `mtn-scraper/main.py`'s `CRAGS` dict.
