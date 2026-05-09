# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Scrapes Mountain Project (mountainproject.com) to collect **ticks** — records of individual climbers ascending specific routes — and stores them in CSVs for analysis. A tick captures: climber name, date, and details (style + pitch count + free-text notes).

## Dependencies

`requests_html` renders JavaScript via **pyppeteer** (headless Chromium). On a fresh environment, pyppeteer will auto-download Chromium on first run — this can take a few minutes and requires network access. Both `pyppeteer` and `playwright` are installed.

```bash
pip install requests beautifulsoup4 requests-html
```

## Project structure

```
mtn-scraper/   ← scraper code, tools, archive
mtn-data/      ← all collected CSV data (written by scraper, read by tools/bot)
  ticks/
  routes/
    areas/
```

The MCP bot section (`mtn-mp-bot/`) is planned but not yet created.

## Running the scraper

```bash
cd mtn-scraper
# Edit main.py to set crag_name to the desired key from the CRAGS dict, then:
python main.py
```

Output is written to three timestamped CSV files per run:
- `mtn-data/ticks/ticks_<CRAG>_<YYYYMMDD>.csv`
- `mtn-data/routes/routes_<CRAG>_<YYYYMMDD>.csv`
- `mtn-data/routes/areas/areas_<CRAG>_<YYYYMMDD>.csv`

The scraper paginates through all routes at the crag, fetches route metadata from the route page, renders each JavaScript-heavy stats page with `requests_html` for ticks, and retries failures automatically.

## Analyzing tick data

```bash
cd mtn-scraper
python tools/ticks_analysis.py ../mtn-data/ticks/ticks_TAHQUITZ_20260507.csv
python tools/ticks_analysis.py ../mtn-data/ticks/ticks_TAHQUITZ_20260507.csv ../mtn-data/ticks/ticks_MALIBU_CREEK_20260507.csv   # multiple files
```

Prints top 20 routes and top 20 climbers by tick count + pitch count. Edit `start_date`/`end_date` and `top_n` directly in the `if __name__ == "__main__"` block.

Set `routes_file` in the `if __name__` block to the matching `../mtn-data/routes/routes_<CRAG>_<YYYYMMDD>.csv` to show full route names and grades in the output instead of URL slugs. Leave it as `None` to use slug-only output (original behavior).

**Note:** `ticks_analysis.py` only reads ticks (and optionally routes). The areas CSV enables further grouping by wall/sub-area — see **What the data can answer** below.

## Scraping a single route (for debugging)

```bash
cd mtn-scraper
python get_ticks.py       # renders the stats page for the hardcoded URL, prints tick count
python get_route_info.py  # fetches the route page for two hardcoded URLs, prints parsed fields
python archive/stats_table.py  # renders a stats page and saves raw HTML to archive/html/content.html
```

To test a different URL, edit the hardcoded URL in the `if __name__ == '__main__'` block at the bottom of whichever file you're running.

`archive/html/` contains saved debug HTML snapshots (`content.html`, `onx-stats.table.html`) — these are artifacts from `stats_table.py` runs, not source files.

**`archive/test.py` is a prototype, not a test suite.** It uses plain `requests` with no JS rendering. It will silently return empty results on most routes because Mountain Project stats pages require JavaScript to populate the tick table. Do not use it to validate behavior — use `get_ticks.py` instead.

**`failed_routes.py` can be run standalone** to manually retry specific URLs that are still failing after a full run. Uncomment the URLs in its `__main__` block and set `csv_file` to the target ticks CSV, then run `python failed_routes.py`. It appends recovered ticks to the existing CSV without overwriting it.

## Rate limiting

`SLEEP_TIME` (set in `main.py`) controls the sleep between tick-scrape attempts. Mountain Project will throttle or block aggressive scrapers. The failed-URL retry pass uses `SLEEP_TIME * 2` for the same reason. Route info fetches (plain HTTP, no JS) use a separate 5s sleep on retry only — they do not sleep on success since the JS rendering of the following ticks fetch provides natural delay.

## Architecture

The scrape pipeline is four stages:

1. **`get_routes.py`** — Given a crag ID, queries the Mountain Project route-finder twice (once for `type=rock`, once for `type=boulder`) and paginates until no new routes are found. Returns deduplicated `/route/stats/` URLs. Rock and boulder routes use different internal difficulty encodings on Mountain Project.

2. **`get_route_info.py`** — For each stats URL, converts it to the route page URL (`/route/stats/` → `/route/`) and fetches it with plain `requests` (no JS needed — route pages are server-rendered). Parses route name, grade, type, length, and the full area hierarchy from the breadcrumb. Returns a route row tuple and a list of area tuples. See **HTML parsing details** below.

3. **`get_ticks.py`** — The stats pages are JavaScript-rendered, so `requests_html` drives a headless Chromium to get the DOM. `parse_ticks_direct()` then finds the tick table by looking for `<tr id="ticks.*">` rows and extracts user name, date, and details. See **HTML parsing details** below.

4. **`main.py`** — Orchestrates the loop: for each route URL, fetch route info (3 attempts, 5s sleep) then fetch ticks (3 attempts, ~5s sleep). Writes ticks and routes incrementally with `flush()` after each route. Collects areas in a dict (deduplicating by area ID) and writes the areas CSV after the loop. Hands still-failing tick URLs to `failed_routes.py` for a second pass with a longer sleep. Failing route info URLs are logged at the end.

## Output schemas

Full schemas, join model, and query examples are documented in `mtn-data/data-context.md`.

**Quick reference — three CSVs per crag run:**
- `mtn-data/ticks/ticks_<CRAG>_<YYYYMMDD>.csv` → `Route, Name, Date, Details`
- `mtn-data/routes/routes_<CRAG>_<YYYYMMDD>.csv` → `Route, Name, Grade, Type, Length, AreaID`
- `mtn-data/routes/areas/areas_<CRAG>_<YYYYMMDD>.csv` → `AreaID, Name, ParentID, FullPath`

Join chain: `ticks.Route` → `routes.Route` → `routes.AreaID` → `areas.AreaID`

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

## Crag IDs

Defined in `main.py`'s `CRAGS` dict. SoCal crags (Tahquitz, Malibu Creek, Mt. Woodson, Mission Gorge, etc.), NorCal Bay Area clusters, Arizona (McDownells, Pima Canyon), and Joshua Tree sectors.

Output CSVs per crag live in:
- `mtn-data/ticks/ticks_<CRAG>_<YYYYMMDD>.csv`
- `mtn-data/routes/routes_<CRAG>_<YYYYMMDD>.csv`
- `mtn-data/routes/areas/areas_<CRAG>_<YYYYMMDD>.csv`

To find a new crag's ID: navigate to the area on Mountain Project — the numeric ID is in the URL: `mountainproject.com/area/105790250/mission-gorge` → ID is `105790250`.

Mountain Project URL structure:
- Area page: `/area/<id>/<name>`
- Route page: `/route/<id>/<name>`
- Stats page (what we scrape): `/route/stats/<id>/<name>`

## Planned web UI

`archive/website.txt` outlines a future web application with: a crag selector by ID, a "collect data" button that runs the full scrape with a progress bar, retry-failed-URLs controls, and a crag dashboard showing most recent tick (who, what route, when). The current scripts are the backend logic for this planned UI.
