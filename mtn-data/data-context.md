# Mountain Project Data — Context for AI

This document explains what the data in this folder is, where it came from, how it is structured, and what questions it can answer.

---

## What is Mountain Project?

Mountain Project (mountainproject.com) is the largest community-maintained rock climbing database in North America. Climbers use it to:
- Look up routes at a crag (name, grade, type, description, photos)
- Log their ascents ("ticks") with style, date, and notes
- Browse area hierarchies (state → park → wall → route)

The site is a mix of crowd-sourced route information and personal tick logs. A tick represents one climber completing one ascent of one route on one date. Routes accumulate ticks over years, making tick counts a measure of a route's real-world popularity.

---

## Mountain Project URL Structure

Understanding the URL structure is important for interpreting the data, since route slugs are derived from it.

| Page type | URL pattern | Example |
|---|---|---|
| Area page | `/area/<id>/<name>` | `/area/105788031/tahquitz` |
| Route page | `/route/<id>/<name>` | `/route/105722065/illusion-dweller` |
| Stats page (ticks) | `/route/stats/<id>/<name>` | `/route/stats/105722065/illusion-dweller` |

- **Area ID** — A numeric identifier for each geographic area (crag, wall, sub-wall, state, park). Hierarchical: a crag contains walls, which contain routes.
- **Route ID** — A numeric identifier for each route. Stable; the slug (name portion) can change but the ID does not.
- **Route slug** — The last path segment of the URL, e.g. `illusion-dweller`. This is what the `Route` column contains in both the ticks and routes CSVs.

The stats page (`/route/stats/`) is the page scraped for tick data. It requires JavaScript to render — the tick table is populated client-side.

---

## What Data We Collect

For each crag (defined by its Mountain Project area ID), the scraper collects:

1. **All routes** — both rock/trad/sport routes and boulder problems, via the Mountain Project route-finder API.
2. **Route metadata** — name, grade, type (Trad/Sport/Boulder/TR), length, and the full area hierarchy (which wall, which sub-area, which park, etc.).
3. **Ticks** — every logged ascent on the stats page: climber username, date, and details (style + pitch count + free-text notes).

The scraper does **not** collect: ratings, photos, descriptions, comments, gear lists, or any user profile data beyond the username that appears on tick entries.

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

**Naming convention:** `<CRAG>` is a short key (e.g., `TAHQUITZ`, `JTREE_CENTRAL`, `MISSION_GORGE`). `<YYYYMMDD>` is the date the scrape was run. Multiple files for the same crag represent different scrape runs — use the most recent date for current data.

**One crag = one set of three CSVs.** The ticks, routes, and areas files for the same `<CRAG>_<YYYYMMDD>` suffix are always used together. Do not mix files from different crags in a join without first filtering by crag, because route slugs can collide across crags (two different crags can both have a route called `the-crack`).

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
| `Details` | string | Scraped from Mountain Project stats page. Always begins with the date, then an optional pitch count, then a style tag, then optional free-text notes. |

**Details field format (actual):**
```
<Date> · [N pitches. ] <Style>[. <notes>]
<Date> • No names/notes
<Date>
```

- The date repeats the `Date` column value — Mountain Project includes it in the stats page details div.
- Separator after date: `·` (U+00B7 middle dot) or `•` (U+2022 bullet).
- Pitch count is **before** the style tag, not after (e.g., `4 pitches.  Lead / Onsight.`).
- `• No names/notes` is Mountain Project's default when no note is entered.
- Date-only entries (no separator, no style) occur occasionally.

Example Details values:
```
Apr 21, 2026 ·  Lead / Redpoint. Cold day, bring doubles on #2.
Apr 4, 2026 · 4 pitches.  Lead / Onsight. Lead with Casey. Fun day!
Apr 18, 2026 • No names/notes
Dec 30, 2026 ·  TR.
Mar 1, 2026 ·  Follow.
Sep 29, 2025 ·  Lead.
Sep 5, 2025
```

Known style tags: `Lead / Onsight`, `Lead / Flash`, `Lead / Redpoint`, `Lead / Pinkpoint`, `Lead / Fell/Hung`, `Lead` (no sub-style), `Follow`, `TR`, `Solo`, `Boulder`.

**Parsing:** Strip date prefix + optional pitch count before applying style matching. Regex for pitch count: `(\d+)\s+pitch` — if not present in the full string, treat as 1 pitch for roped routes, 0 for boulders.

### `routes/routes_<CRAG>_<YYYYMMDD>.csv`

```
Route, Name, Grade, Type, Length, AreaID
```

| Column | Type | Description |
|---|---|---|
| `Route` | string | URL slug. Primary key. Joins to `ticks.Route`. |
| `Name` | string | Full route name, e.g. `Illusion Dweller`. |
| `Grade` | string | `5.10b` (YDS) for rock routes, `V3` (V-scale) for boulders. |
| `Type` | string | `Trad`, `Sport`, `Boulder`, `TR`, or combinations like `Trad, Sport`. |
| `Length` | string | Route length in feet, e.g. `100 ft`. Empty for boulders. |
| `AreaID` | integer | Mountain Project area ID of the route's immediate parent (the wall or sub-area). Foreign key → `areas.AreaID`. |

**Type values:**
- `Trad` — leader places removable gear
- `Sport` — leader clips pre-drilled bolts
- `Boulder` — unroped boulder problem
- `TR` — top-rope only (no lead anchors; the route can only be done from above)
- `Trad, Sport` — mixed (has both bolts and gear placements)
- `Alpine`, `Aid` — less common; mountaineering or aid climbing context

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

One row per unique area encountered across all routes in the crag. A crag with 300 routes typically has 20–40 unique areas (many routes share the same wall).

---

## Data Model and Join Chain

```
areas
  AreaID (PK) │ Name              │ ParentID  │ FullPath
  ─────────────┼───────────────────┼───────────┼──────────────────────────────────────
  106621111    │ Sentinel - W Face │ 105720693 │ California > ... > Sentinel - W Face

routes
  Route (PK)         │ Name             │ Grade  │ Type │ Length │ AreaID (FK → areas)
  ────────────────────┼──────────────────┼────────┼──────┼────────┼────────────────────
  illusion-dweller   │ Illusion Dweller │ 5.10b  │ Trad │ 100 ft │ 106621111

ticks
  Route (FK → routes) │ Name       │ Date         │ Details
  ─────────────────────┼────────────┼──────────────┼──────────────────────────
  illusion-dweller     │ Erik Earl  │ Apr 21, 2026 │ Lead / Onsight. Great route
```

**Join chain:** `ticks.Route` → `routes.Route` → `routes.AreaID` → `areas.AreaID`

Ticks are the primary unit of activity. Routes add metadata (grade, type, wall). Areas add geographic grouping (which wall, which section of the crag).

---

## What the Data Can Answer

**With ticks only:**
- Who are the most active climbers at a crag?
- Which routes get the most traffic overall or within a date range?
- How many pitches has a given climber logged (weighted ascent volume)?
- What's the trend in activity at a crag over time?

**With ticks + routes:**
- What grade range sees the most traffic? (join on `Grade`)
- Are Trad or Sport routes more popular at this crag?
- Which routes are being onsighted most often vs. fell/hung? (filter `Details`)
- What's the hardest route with the most ticks? (popularity vs. difficulty)
- How does pitch-weighted traffic differ from raw tick counts?

**With ticks + routes + areas:**
- Which wall (sub-area) is the busiest?
- Is one sector of a crag more trafficked than another?
- What's the grade distribution of routes being climbed in a specific area?
- Which area has the most unique climbers vs. repeat visitors?
- Where at the crag do climbers go to warm up (lower grades, high traffic)?

---

## Key Caveats and Data Limitations

**Ticks are self-reported.** Not every climber logs their ascents on Mountain Project. Tick counts undercount real traffic — they reflect the subset of climbers who use the platform and bother to log. Relative comparisons (route A vs. route B) are more reliable than absolute counts.

**Private ticks are excluded.** Mountain Project allows users to log private ticks that don't appear on the public stats page. These are invisible to the scraper.

**Route slug collisions across crags.** The `Route` slug is unique within a crag's URL space but not across crags. Two different crags can both have a route called `the-crack`. Always scope queries to a single crag's set of CSVs.

**Scrape date matters.** Each CSV is a snapshot of Mountain Project at the time of the scrape. New ticks logged after the scrape date are not included. The filename's `<YYYYMMDD>` tells you when the data was collected.

**Area hierarchy is route-centric.** The areas CSV only contains areas that appear as parent areas for routes in the scraped crag. It does not contain every Mountain Project area in the region — only the ones needed to describe the scraped routes.

**Boulder vs. rock route IDs.** Mountain Project uses different internal difficulty encodings for rock vs. boulder problems. The scraper queries both separately and combines them. Boulders have V-scale grades; rock routes have YDS grades. The `Grade` column is always the raw string from Mountain Project.

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
