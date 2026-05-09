# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Scrapes Mountain Project (mountainproject.com) to collect **ticks** — records of individual climbers ascending specific routes — and stores them in CSVs for analysis. A tick captures: climber name, date, and details (style + pitch count + free-text notes).

## Dependencies

`requests_html` renders JavaScript via **pyppeteer** (headless Chromium). On a fresh environment, pyppeteer will auto-download Chromium on first run — this can take a few minutes and requires network access. Both `pyppeteer` and `playwright` are installed.

```bash
pip install requests beautifulsoup4 requests-html
```

## Running the scraper

```bash
# Edit main.py to set crag_name to the desired key from the CRAGS dict, then:
python main.py
```

Output is written to three timestamped CSV files per run:
- `ticks/ticks_<CRAG>_<YYYYMMDD>.csv`
- `routes/routes_<CRAG>_<YYYYMMDD>.csv`
- `routes/areas_<CRAG>_<YYYYMMDD>.csv`

The scraper paginates through all routes at the crag, fetches route metadata from the route page, renders each JavaScript-heavy stats page with `requests_html` for ticks, and retries failures automatically.

## Analyzing tick data

```bash
python ticks_analysis.py ticks/ticks_TAHQUITZ_20260507.csv
python ticks_analysis.py ticks/ticks_TAHQUITZ_20260507.csv ticks/ticks_MALIBU_CREEK_20260507.csv   # multiple files
```

Prints top 20 routes and top 20 climbers by tick count + pitch count. Edit `start_date`/`end_date` and `top_n` directly in the `if __name__ == "__main__"` block.

Set `routes_file` in the `if __name__` block to the matching `routes_<CRAG>_<YYYYMMDD>.csv` to show full route names and grades in the output instead of URL slugs. Leave it as `None` to use slug-only output (original behavior).

**Note:** `ticks_analysis.py` only reads ticks (and optionally routes). The areas CSV enables further grouping by wall/sub-area — see **What the data can answer** below.

## Scraping a single route (for debugging)

```bash
python get_ticks.py       # renders the stats page for the hardcoded URL, prints tick count
python get_route_info.py  # fetches the route page for two hardcoded URLs, prints parsed fields
python stats_table.py     # renders a stats page and saves the raw HTML to content.html
```

To test a different URL, edit the hardcoded URL in the `if __name__ == '__main__'` block at the bottom of whichever file you're running.

`html/` contains saved debug HTML snapshots (`content.html`, `onx-stats.table.html`) — these are artifacts from `stats_table.py` runs, not source files.

**`test.py` is a prototype, not a test suite.** It uses plain `requests` with no JS rendering. It will silently return empty results on most routes because Mountain Project stats pages require JavaScript to populate the tick table. Do not use it to validate behavior — use `get_ticks.py` instead.

**`failed_routes.py` can be run standalone** to manually retry specific URLs that are still failing after a full run. Uncomment the URLs in its `__main__` block and set `csv_file` to the target ticks CSV, then run `python failed_routes.py`. It appends recovered ticks to the existing CSV without overwriting it.

## Rate limiting

`SLEEP_TIME` (set in `main.py`) controls the sleep between tick-scrape attempts. Mountain Project will throttle or block aggressive scrapers — do not set it below ~9s. The failed-URL retry pass uses `SLEEP_TIME * 2` for the same reason. Route info fetches (plain HTTP, no JS) use a separate 5s sleep on retry only — they do not sleep on success since the JS rendering of the following ticks fetch provides natural delay.

## Architecture

The scrape pipeline is four stages:

1. **`get_routes.py`** — Given a crag ID, queries the Mountain Project route-finder twice (once for `type=rock`, once for `type=boulder`) and paginates until no new routes are found. Returns deduplicated `/route/stats/` URLs. Rock and boulder routes use different internal difficulty encodings on Mountain Project.

2. **`get_route_info.py`** — For each stats URL, converts it to the route page URL (`/route/stats/` → `/route/`) and fetches it with plain `requests` (no JS needed — route pages are server-rendered). Parses route name, grade, type, length, and the full area hierarchy from the breadcrumb. Returns a route row tuple and a list of area tuples. See **HTML parsing details** below.

3. **`get_ticks.py`** — The stats pages are JavaScript-rendered, so `requests_html` drives a headless Chromium to get the DOM. `parse_ticks_direct()` then finds the tick table by looking for `<tr id="ticks.*">` rows and extracts user name, date, and details. See **HTML parsing details** below.

4. **`main.py`** — Orchestrates the loop: for each route URL, fetch route info (3 attempts, 5s sleep) then fetch ticks (3 attempts, 9s sleep). Writes ticks and routes incrementally with `flush()` after each row. Collects areas in a dict (deduplicating by area ID) and writes the areas CSV after the loop. Hands still-failing tick URLs to `failed_routes.py` for a second pass with a longer sleep. Failing route info URLs are logged at the end.

## Output schemas

**`ticks/ticks_<CRAG>_<YYYYMMDD>.csv`**
```
Route,Name,Date,Details
```
- `Route` — URL slug (last path segment of the stats URL), e.g. `illusion-dweller`
- `Name` — Mountain Project username
- `Date` — `"Apr 21, 2026"` format
- `Details` — free text beginning with style tag: `Lead / Onsight.`, `Lead / Redpoint.`, `Lead / Fell/Hung.`, `Lead / Flash.`, `TR`, `Follow`, `Solo`, `Boulder`. Multi-pitch routes include `· X pitch` in the details; `parse_pitches()` in `ticks_analysis.py` extracts this with a regex.

**`routes/routes_<CRAG>_<YYYYMMDD>.csv`**
```
Route,Name,Grade,Type,Length,AreaID
```
- `Route` — URL slug, joins to `ticks.Route`
- `Name` — full route name, e.g. `Illusion Dweller`
- `Grade` — YDS grade for rock routes (e.g. `5.10b`), V-scale for boulders (e.g. `V3`)
- `Type` — raw type string from Mountain Project: `Trad`, `Sport`, `Boulder`, `TR`, or combinations like `Trad, Sport`. A route labeled only `TR` or `Toprope` is a top-rope-only route.
- `Length` — route length in feet, e.g. `100 ft`. Empty for boulders.
- `AreaID` — numeric Mountain Project area ID of the route's immediate parent area; joins to `areas.AreaID`

**`routes/areas_<CRAG>_<YYYYMMDD>.csv`**
```
AreaID,Name,ParentID,FullPath
```
- `AreaID` — numeric Mountain Project area ID extracted from the area URL (e.g. `106621111`)
- `Name` — area display name, e.g. `Sentinel - W Face`
- `ParentID` — parent area's numeric ID (empty for top-level geography)
- `FullPath` — full breadcrumb from top-level geography down to this area, e.g. `California > Joshua Tree NP > Hidden Valley Area > Real Hidden Valley > Sentinel > Sentinel - W Face`

One row per unique area encountered across all routes in the crag. Many routes share the same wall, so a crag with 300 routes typically has ~20–40 unique areas.

**Join chain:** `ticks.Route` → `routes.Route` → `routes.AreaID` → `areas.AreaID`

**Data model:**
```
areas
  AreaID (PK) │ Name              │ ParentID  │ FullPath
  ─────────────┼───────────────────┼───────────┼──────────────────────────────────────
  106621111    │ Sentinel - W Face │ 105720693 │ California > ... > Sentinel - W Face

routes
  Route (PK)         │ Name             │ Grade  │ Type │ Length │ AreaID (FK→areas)
  ────────────────────┼──────────────────┼────────┼──────┼────────┼──────────────────
  illusion-dweller   │ Illusion Dweller │ 5.10b  │ Trad │ 100 ft │ 106621111

ticks
  Route (FK→routes) │ Name            │ Date         │ Details
  ───────────────────┼─────────────────┼──────────────┼──────────────────────────
  illusion-dweller  │ Erik Earl       │ Apr 21, 2026 │ Lead / Onsight. Great route
```

**Important:** `Route` slug is unique within a crag's URL space but may collide across crags (two crags can have a route named "the-crack"). Always filter or join within a single crag's set of CSVs.

## What the data can answer

With ticks only:
- Who are the most active climbers at a crag?
- Which routes get the most traffic overall or within a date range?
- How many pitches has a given climber completed?

With ticks + routes:
- What grade range sees the most traffic? (join on Grade)
- Are Trad or Sport routes more popular at this crag?
- Which specific routes are being onsighted vs. fell/hung? (Details field + Grade)
- What's the hardest route with the most ticks? (popularity vs. difficulty)

With ticks + routes + areas:
- Which sub-area (wall) is the busiest?
- Is Hidden Valley more trafficked than Real Hidden Valley?
- What's the grade distribution of routes climbed in a specific area?
- Which area has the most unique climbers vs. repeat visitors?

## HTML parsing details

### Route page (`/route/<id>/<name>`) — `get_route_info.py`

Fetched with plain `requests`, no JS rendering required.

**Route name** — `<h1>` first NavigableString child. The `<h1>` also contains a nested `<a>` edit-icon link, so `get_text()` on the whole tag would include "Suggest change". Instead, iterate `h1.children` and take the first `NavigableString`.

**Grade** — `<span class="rateYDS">` for rock/trad/sport routes, `<span class="rateHueco">` for boulders. Each grade span also contains a nested `<span class="small">` with the system label ("YDS", "Hueco"), so again take only the first NavigableString child rather than calling `get_text()` on the whole span.

**Type and Length** — `<table class="description-details">` contains multiple label/value row pairs. Find the row where the first `<td>` contains `"Type:"`. The second `<td>` holds a combined string like `"Trad, 100 ft (30 m)"` or just `"Boulder"`. Parse with:
- Length: `re.search(r'(\d[\d,]*)\s*ft', type_cell)` → e.g. `100 ft`
- Type: strip the length portion with `re.sub(r',?\s*\d[\d,]*\s*ft.*', '', type_cell)` → e.g. `Trad`

**Area hierarchy** — `<div class="mb-half small text-warm">` is the breadcrumb. Iterate all `<a href="/area/...">` links in order (skipping the "All Locations" link which goes to `/route-guide`, not `/area/`). For each area link:
- AreaID: second-to-last path segment of the URL, e.g. `/area/106621111/the-sentinel-west-face` → `106621111`
- Name: link text
- ParentID: previous area's ID in the list (empty for first)
- FullPath: accumulate names joined by ` > `

The last area in the list is the route's immediate parent (the wall or sub-area).

### Stats page (`/route/stats/<id>/<name>`) — `get_ticks.py`

Requires JavaScript rendering — `requests_html` drives headless Chromium via pyppeteer. Renders `div.main-content-container` and returns its HTML.

**Tick count check** — `h3:-soup-contains('Ticks') span.small.text-muted` contains the total tick count. If it parses to `0`, skip table parsing and return `[]`.

**Tick table** — find all `<table class="table table-striped">` and pick the one that contains a `<tr id="ticks.*">` row. Each such row has two `<td>` cells:
- Cell 0: username in an `<a>` tag
- Cell 1: date in a `<strong>` tag; details in a `<div class="small">`

## Climbing domain context

**Disciplines**
- **Sport climbing** — bolted routes, leader clips pre-installed protection. YDS grades (5.0–5.15d). `diffMinrock=800&diffMaxrock=12400` in Mountain Project's internal encoding.
- **Trad climbing** — leader places removable gear (cams, nuts) into cracks as they climb; follower removes it. Same YDS grades. Common at Tahquitz, Joshua Tree. Frequently multi-pitch (5–7+ pitches).
- **Bouldering** — no rope, V-scale grades (V0–V17). `diffMinboulder=20000&diffMaxboulder=21700`. Scraped with `type=boulder`.
- **Pitch** — one rope-length section of a multi-pitch route. `ticks_analysis.py` sums pitches to weight long routes appropriately.

**YDS grades**
- 5.0–5.9: accessible range. 5.9 was historically the hardest possible grade when the system was invented at Tahquitz in the 1950s (the route "Open Book" defined it).
- 5.10+: subdivided a/b/c/d (5.10a = easiest, 5.10d = hardest within that number). 5.10a and 5.10d are a huge gap.
- R/X suffix = sparse or no protection; a fall can be very consequential.

**Trad crack sizes and technique** (crack width drives both technique and gear selection)

| Crack type | Width | Technique |
|---|---|---|
| Thin finger | 7–15mm | Fingertips only, first knuckle |
| Finger crack | 15–28mm | 1–2 knuckles inserted, twist to lock |
| Ring lock / thin hand | 28–42mm | Wrist torqued, ring finger creates lock |
| Hand crack | 38–55mm | Full hand jam — thumb tucked, heel of hand locks. The most comfortable crack type. |
| Fist crack | 65–90mm | Fist inserted, fingers flex outward to grip |
| Off-width (OW) | 90–200mm | Arm bars, chicken wings, knee locks — awkward and feared |
| Chimney | 200mm+ | Entire body inside; back on one wall, feet on the other |

Hand cracks (~C4 #1–#2 range) are considered the classic, enjoyable crack style. Off-width is widely disliked.

**Cam sizing — Black Diamond C4** (double-axle, industry standard)

| Size | Color | Range (mm) | Crack type |
|---|---|---|---|
| 0.3 | Blue | 13.8–23.4 | Finger |
| 0.4 | Gray | 15.5–26.7 | Finger |
| 0.5 | Purple | 19.6–33.5 | Finger–ring lock |
| 0.75 | Green | 23.9–41.2 | Ring lock |
| #1 | Red | 30.2–52.1 | Ring lock–hand |
| #2 | Yellow | 37.2–64.9 | Hand |
| #3 | Blue | 50.7–87.9 | Hand–fist |
| #4 | Gray | 66.0–114.7 | Fist–OW |
| #5 | Purple | 85.4–148.5 | OW |
| #6 | Green | 114.1–195.0 | OW |

The #1 and #2 are the most-used cams on any rack; many climbers carry doubles of each. The BD Z4 extends below the C4 down to 7.5mm (sizes #0–#0.75) for very thin seams.

**Cam sizing — Totem Cam** (independent lobes, excels in flares and pin scars)

| Size | Color | Range (mm) | Approx C4 equivalent |
|---|---|---|---|
| 0.50 | Black | 11.7–18.9 | C4 0.3 |
| 0.65 | Blue | 13.8–22.5 | C4 0.4 |
| 0.80 | Yellow | 17.0–27.7 | C4 0.5 |
| 1.00 | Purple | 20.9–34.2 | C4 0.75 |
| 1.25 | Green | 25.7–42.3 | C4 1 |
| 1.50 | Red | 31.6–52.2 | C4 1–2 |
| 1.80 | Orange | 39.7–64.2 | C4 2 |

Totem only covers the finger-to-hand range (up to ~64mm / C4 #2). No Totem equivalent exists for fist or off-width. Their independent lobe design self-equalizes in flared or uneven cracks — a significant advantage at granite crags like Joshua Tree where cracks are often polished and slightly flared.

## Crag IDs

Defined in `main.py`'s `CRAGS` dict. SoCal crags (Tahquitz, Malibu Creek, Mt. Woodson, Mission Gorge, etc.), NorCal Bay Area clusters, Arizona (McDownells, Pima Canyon), and Joshua Tree sectors.

Output CSVs per crag live in:
- `ticks/ticks_<CRAG>_<YYYYMMDD>.csv`
- `routes/routes_<CRAG>_<YYYYMMDD>.csv`
- `routes/areas_<CRAG>_<YYYYMMDD>.csv`

To find a new crag's ID: navigate to the area on Mountain Project — the numeric ID is in the URL: `mountainproject.com/area/105790250/mission-gorge` → ID is `105790250`.

Mountain Project URL structure:
- Area page: `/area/<id>/<name>`
- Route page: `/route/<id>/<name>`
- Stats page (what we scrape): `/route/stats/<id>/<name>`

## Planned web UI

`website.txt` outlines a future web application with: a crag selector by ID, a "collect data" button that runs the full scrape with a progress bar, retry-failed-URLs controls, and a crag dashboard showing most recent tick (who, what route, when). The current scripts are the backend logic for this planned UI.
