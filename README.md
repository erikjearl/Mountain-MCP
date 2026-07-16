# mtn-proj

Scrapes tick data from Mountain Project and exposes it through an MCP server so an AI assistant can answer questions about climbing areas, routes, and climber history.

## What's in here

**`mtn-scraper/`** — Python scraper that collects routes and ticks from Mountain Project's stats pages. Runs headless Chromium to handle the JS-rendered tick tables. Outputs three CSVs per crag (ticks, routes, areas). Can run locally or as a Kubernetes Job.

**`mtn-data/`** — The collected CSV data. One set of files per crag, timestamped by scrape date.

**`mtn-mcp/`** — A TypeScript MCP server that reads the CSVs and exposes tools for exploring crags, looking up route beta, analyzing climber tick history, and suggesting gear. Connects to Claude Code via `.mcp.json`.

## Setup

Scraper:
```bash
cd mtn-scraper
pip install -r requirements.txt
```

MCP server:
```bash
cd mtn-mcp
npm install && npm run build
```

## Running the scraper — pull an area from the CLI

The scraper takes a crag via the `CRAG_NAME` environment variable. Crag selection is driven by the `CRAGS` dict in `mtn-scraper/main.py`, which maps a name to its Mountain Project area ID.

```bash
cd mtn-scraper

# Pull Tahquitz (a known crag in the CRAGS dict)
CRAG_NAME=TAHQUITZ python main.py

# Other known crags — same pattern
CRAG_NAME=SUICIDE_ROCK python main.py
CRAG_NAME=GUNKS python main.py
```

Each run writes three timestamped CSVs into `../mtn-data/`:
- `ticks/ticks_TAHQUITZ_<YYYYMMDD>.csv`
- `routes/routes_TAHQUITZ_<YYYYMMDD>.csv`
- `routes/areas/areas_TAHQUITZ_<YYYYMMDD>.csv`

### Docker

The image pre-bakes Chromium (needed to render the JS tick tables). Mount your data dir at `/mtn-proj-data`:

```bash
docker build -t mtn-scraper .
docker run -e CRAG_NAME=TAHQUITZ -v "$(pwd)/../mtn-data:/mtn-proj-data" mtn-scraper
```

### Analyze the pulled ticks (no MCP server needed)

```bash
python tools/ticks_analysis.py ../mtn-data/ticks/ticks_TAHQUITZ_<YYYYMMDD>.csv
```

See `CLAUDE.md` for full usage details, the complete crag list, Kubernetes jobs, and rate-limiting knobs.
