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
CRAG_NAME=TAHQUITZ python main.py
```

MCP server:
```bash
cd mtn-mcp
npm install && npm run build
```

See `CLAUDE.md` for full usage details.
