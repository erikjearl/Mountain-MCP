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

Output is written to `ticks/ticks_<CRAG_NAME>.csv`. The scraper paginates through all routes at the crag, renders each JavaScript-heavy stats page with `requests_html`, and retries failures automatically.

## Analyzing tick data

```bash
python ticks_analysis.py ticks/ticks_TAHQUITZ.csv
python ticks_analysis.py ticks/ticks_TAHQUITZ.csv ticks/ticks_MALIBU_CREEK.csv   # multiple files
```

Prints top 20 routes and top 20 climbers by tick count + pitch count. Edit `start_date`/`end_date` and `top_n` directly in the `if __name__ == "__main__"` block.

## Scraping a single route (for debugging)

```bash
python get_ticks.py     # hits the hardcoded URL at the bottom of the file
python stats_table.py   # renders a route stats page and saves HTML to content.html
```

`html/` contains saved debug HTML snapshots (`content.html`, `onx-stats.table.html`) — these are artifacts from `stats_table.py` runs, not source files.

**`test.py` is a prototype, not a test suite.** It uses plain `requests` with no JS rendering. It will silently return empty results on most routes because Mountain Project stats pages require JavaScript to populate the tick table. Do not use it to validate behavior — use `get_ticks.py` instead.

## Rate limiting

`SLEEP_TIME = 10` (seconds between route scrapes) in `main.py` is intentional. Mountain Project will throttle or block aggressive scrapers. Do not reduce it. The failed-URL retry pass uses `SLEEP_TIME * 2` (20s) for the same reason.

## Architecture

The scrape pipeline is three stages:

1. **`get_routes.py`** — Given a crag ID, queries the Mountain Project route-finder twice (once for `type=rock`, once for `type=boulder`) and paginates until no new routes are found. Returns deduplicated `/route/stats/` URLs. Rock and boulder routes use different internal difficulty encodings on Mountain Project.

2. **`get_ticks.py`** — The stats pages are JavaScript-rendered, so `requests_html` drives a headless Chromium to get the DOM. `parse_ticks_direct()` then finds the tick table by looking for `<tr id="ticks.*">` rows and extracts user name, date, and details.

3. **`main.py`** — Orchestrates the loop with retry logic (3 attempts, 10s sleep), writes rows incrementally to avoid memory buildup, then hands any still-failing URLs to `failed_routes.py` for a second pass with a longer sleep.

## Tick data schema

```
Route,Name,Date,Details
```
- `Route` — URL slug (last path segment of the stats URL)
- `Name` — Mountain Project username
- `Date` — `"Apr 21, 2026"` format
- `Details` — free text beginning with style tag: `Lead / Onsight.`, `Lead / Redpoint.`, `Lead / Fell/Hung.`, `Lead / Flash.`, `TR`, `Follow`, `Solo`, `Boulder`. Multi-pitch routes include `· X pitch` in the details; `parse_pitches()` in `ticks_analysis.py` extracts this with a regex.

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

Defined in `main.py`'s `CRAGS` dict. SoCal crags (Tahquitz, Malibu Creek, Mt. Woodson, Mission Gorge, etc.), NorCal Bay Area clusters, Arizona (McDownells, Pima Canyon), and Joshua Tree sectors. CSVs for already-scraped crags live in `ticks/` (flat for SoCal) and `ticks/jtree/` (Joshua Tree sub-areas).

To find a new crag's ID: navigate to the area on Mountain Project — the numeric ID is in the URL: `mountainproject.com/area/105790250/mission-gorge` → ID is `105790250`.

Mountain Project URL structure:
- Area page: `/area/<id>/<name>`
- Route page: `/route/<id>/<name>`
- Stats page (what we scrape): `/route/stats/<id>/<name>`

## Planned web UI

`website.txt` outlines a future web application with: a crag selector by ID, a "collect data" button that runs the full scrape with a progress bar, retry-failed-URLs controls, and a crag dashboard showing most recent tick (who, what route, when). The current scripts are the backend logic for this planned UI.
