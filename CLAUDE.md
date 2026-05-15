# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## What this project does

Scrapes Mountain Project (mountainproject.com) to collect **ticks** — records of individual climbers ascending specific routes — and stores them as CSVs. An MCP server then exposes the data to AI assistants via structured tools.

## Project structure

```
mtn-scraper/          ← Python scraper (headless Chromium, BS4)
  main.py             ← orchestrator: resolves crag, runs pipeline, writes CSVs
  get_routes.py       ← stage 1: discover route stats URLs from crag ID
  get_route_info.py   ← stage 2: fetch route metadata (name, grade, type, length, pitches, areas)
  get_ticks.py        ← stage 3: JS-render stats pages, parse tick rows
  failed_routes.py    ← second-pass retry for both ticks and route info that failed in main loop
  requirements.txt
  Dockerfile / .dockerignore
  tools/
    ticks_analysis.py ← standalone CLI: top routes + climbers from CSVs
  archive/            ← debug HTML snapshots, prototype scripts
  deployments/        ← Kubernetes Job YAML files (one per crag)

mtn-data/             ← CSV data written by scraper, read by MCP server
  ticks/              ← ticks_<CRAG>_<YYYYMMDD>.csv
  routes/             ← routes_<CRAG>_<YYYYMMDD>.csv
    areas/            ← areas_<CRAG>_<YYYYMMDD>.csv
  data-context.md     ← full CSV schemas, join model, data caveats (read before touching data)

mtn-mcp/              ← MCP server (TypeScript/Node.js)
  src/
    index.ts          ← server entry: registers tools + resources, stdio transport
    data-loader.ts    ← CSV loaders, grade utilities (ydsToNum, vGradeToNum), parseStyle
    tools/
      ticks.ts        ← climber_profile, top_routes
      routes.ts       ← crag_overview, area_breakdown, route_info, find_routes, list_crags
      beta.ts         ← route_beta (mines tick freetext for gear/conditions/notes)
      gear.ts         ← suggest_gear (heuristic cam rack for trad routes)
  dist/               ← compiled JS output (not committed)
  rock_climbing_context.md  ← climbing domain knowledge (grades, gear, disciplines)
  .mcp.json           ← Claude Code MCP registration
```

## Context files — read these before working on each sub-project

- `mtn-data/data-context.md` — CSV schemas, join model, Mountain Project URL structure, data caveats. Critical when working on any data layer or MCP tool.
- `mtn-mcp/rock_climbing_context.md` — climbing domain: YDS/V-scale grades, tick styles, crack sizes, cam sizing tables. Critical when working on any AI-facing feature.

---

## mtn-scraper

### Dependencies

```bash
pip install -r requirements.txt
# requirements.txt pins: requests, beautifulsoup4, requests-html, pyppeteer
```

`requests_html` drives headless Chromium via pyppeteer. On a fresh environment, pyppeteer downloads Chromium on first run (requires network). The Docker image pre-bakes Chromium at build time.

### Running locally

Set `HARD_CODE_CRAG` in `main.py` to the key you want, then:

```bash
cd mtn-scraper
python main.py
```

Or use environment variables instead of editing the file:

```bash
# Named crag (must exist in the CRAGS dict in main.py)
CRAG_NAME=TAHQUITZ python main.py

# Arbitrary crag not in the dict — supply both vars
CRAG_NAME=YOSEMITE CRAG_ID=105833381 python main.py

# Override data output directory (default: ../mtn-data)
MTN_DATA_DIR=/some/other/path CRAG_NAME=TAHQUITZ python main.py
```

Output is three timestamped CSVs per run:
- `mtn-data/ticks/ticks_<CRAG>_<YYYYMMDD>.csv`
- `mtn-data/routes/routes_<CRAG>_<YYYYMMDD>.csv`
- `mtn-data/routes/areas/areas_<CRAG>_<YYYYMMDD>.csv`

Exits with code 1 if any URLs permanently failed (useful for CI/CD detection).

### Running with Docker

```bash
cd mtn-scraper
docker build -t mtn-scraper .
docker run -e CRAG_NAME=TAHQUITZ -v /path/to/mtn-data:/mtn-proj-data mtn-scraper
```

The image pre-downloads Chromium at build time. `MTN_DATA_DIR` defaults to `/mtn-proj-data` inside the container — mount your data volume there.

### Kubernetes

`deployments/` contains one Job YAML per crag. Each job runs a single scrape and exits. Data is written to a PVC named `mtn-data-pvc`.

```bash
kubectl apply -f mtn-scraper/deployments/job-tahquitz.yaml
```

To scrape a crag not in the pre-made YAMLs, copy any job file and set `CRAG_NAME` (+ `CRAG_ID` if needed) in the env section.

### Analyzing tick data (standalone CLI)

```bash
cd mtn-scraper
python tools/ticks_analysis.py ../mtn-data/ticks/ticks_TAHQUITZ_<DATE>.csv
python tools/ticks_analysis.py ../mtn-data/ticks/ticks_TAHQUITZ_<DATE>.csv ../mtn-data/ticks/ticks_MALIBU_CREEK_<DATE>.csv
```

Prints top 20 routes and top 20 climbers by tick count and pitch count. Edit `start_date`, `end_date`, `top_n`, and `routes_file` directly in the `if __name__ == "__main__"` block at the bottom of the script. Set `routes_file` to the matching routes CSV to resolve slugs to full names.

### Scraping a single route (debugging)

```bash
cd mtn-scraper
python get_ticks.py        # renders stats page for hardcoded URL, prints ticks
python get_route_info.py   # fetches route page for hardcoded URLs, prints parsed fields
python archive/stats_table.py  # renders stats page, saves HTML to archive/html/content.html
```

Edit the hardcoded URL in the `if __name__ == '__main__'` block of whichever file you're running.

**`archive/test.py`** uses plain requests with no JS rendering — will silently return empty results on most routes. Use `get_ticks.py` instead.

**`failed_routes.py`** can be run standalone to manually retry specific URLs. Uncomment URLs in its `__main__` block and set `csv_file`, then run `python failed_routes.py`. Appends to the existing CSV without overwriting.

### Rate limiting

`SLEEP_TIME` in `main.py` controls the sleep between tick-scrape attempts (default: 3s with ±2s jitter). Both second-pass retry functions use `SLEEP_TIME * 2`. Route info fetches (plain HTTP) don't sleep on success during the main loop — the JS render of the following ticks fetch provides natural delay.

### Architecture

Four pipeline stages:

1. **`get_routes.py`** — Queries the Mountain Project route-finder API twice (rock + boulder) for a crag ID, paginates until no new routes appear, returns deduplicated `/route/stats/` URLs.

2. **`get_route_info.py`** — Converts stats URL → route URL, fetches with plain `requests` (server-rendered). Extracts route ID from the stats URL. Parses name, grade, type, length, pitch count, and the area breadcrumb hierarchy.

3. **`get_ticks.py`** — JS-renders the stats page with `requests_html` + pyppeteer. Parses `<tr id="ticks.*">` rows, extracts username, date, and the details div.

4. **`main.py`** — For each URL: fetch route info (3 attempts), then fetch ticks (3 attempts, jittered sleep). Flushes ticks and routes CSVs after each route. After the main loop: runs a second-pass retry for failed route info (`handle_failed_route_info`), then a second-pass retry for failed ticks (`handle_failed_routes`). Writes areas CSV after both retry passes so any recovered routes' areas are included.

### Crag IDs

Defined in `main.py`'s `CRAGS` dict. To add a new crag, navigate to it on Mountain Project and copy the numeric ID from the URL: `mountainproject.com/area/105790250/mission-gorge` → ID is `105790250`. Add it to `CRAGS` or pass it via `CRAG_ID` env var.

---

## mtn-mcp

TypeScript MCP server that exposes the CSV data via 9 tools and 2 resources over stdio transport.

### Build and run

```bash
cd mtn-mcp
npm install
npm run build        # tsc → dist/
npm run dev          # tsx (no build needed, for development)
node dist/index.js   # production
```

### Claude Code integration

`.mcp.json` in `mtn-mcp/` registers the server with Claude Code for this project. Restart Claude Code after modifying it. The path in `args` is absolute — update it if the repo moves.

### Tools (9 total)

| Tool | Description |
|---|---|
| `list_crags` | List all crags that have CSV data in `mtn-data/` |
| `crag_overview` | Grade distribution, type breakdown, top routes, busiest months, active climbers + walls |
| `area_breakdown` | All walls/sub-areas ranked by tick count with route count, types, grade range |
| `route_info` | Grade, type, length, wall location, and tick count for a specific route |
| `find_routes` | Search routes by grade, type, and/or area name |
| `route_beta` | Mines all tick freetext for gear mentions, condition/quality keywords, and recent notes |
| `suggest_gear` | Heuristic cam rack recommendation for a trad route based on grade and length |
| `climber_profile` | Grade pyramid (sends only), style breakdown, hardest sends, pitch totals, favorite walls. Supports date filtering. |
| `top_routes` | Most-ticked routes at a crag, with optional type/date filters |

### Resources (2 total)

| URI | Content |
|---|---|
| `mtn://context/climbing` | `rock_climbing_context.md` — climbing domain knowledge |
| `mtn://context/data` | `mtn-data/data-context.md` — CSV schemas and data model |

