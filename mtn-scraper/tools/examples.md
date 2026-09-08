# Running the analysis tools

Copy-paste these into your terminal. All commands assume you're in the `mtn-scraper/` directory:

```bash
cd /Users/erikjearl/Developer/Mountain-MCP/mtn-scraper
```

The tools read CSVs from `../mtn-data/`. Crags currently available: `LOVERS_LEAP`, `PHANTOM_SPIRES`, `YOSEMITE_VALLEY_NORTH`.

---

## route_analysis.py — top routes grouped by area

Takes a crag name and auto-finds the latest ticks/routes/areas CSVs. Prints the top routes by tick count, grouped by wall/area, with grade, type, pitch totals, unique climber counts, and send%.

```bash
python tools/route_analysis.py LOVERS_LEAP
python tools/route_analysis.py PHANTOM_SPIRES
python tools/route_analysis.py YOSEMITE_VALLEY_NORTH
```

Crag name is case-insensitive (`lovers_leap` works too). To change `top_n`, `start_date`, or `end_date`, edit the `if __name__ == "__main__"` block (currently `top_n=25`, `start_date="2026-01-01"`).

---

## climber_analysis.py — top climbers by ticks & pitches

Same auto-find behavior. Ranks climbers by tick count and total pitches (pitch counts pulled from the routes CSV).

```bash
python tools/climber_analysis.py LOVERS_LEAP
python tools/climber_analysis.py PHANTOM_SPIRES
python tools/climber_analysis.py YOSEMITE_VALLEY_NORTH
```

Defaults: `top_n=25`, `start_date="2026-01-01"`. Edit the bottom of the script to change them.

---

## ticks_analysis.py — top routes AND climbers from explicit files

Unlike the other two, this one takes explicit CSV file path(s) as arguments (not a crag name). Prints top routes then top climbers. Pass multiple ticks files to combine crags.

```bash
# Single crag
python tools/ticks_analysis.py ../mtn-data/ticks/ticks_LOVERS_LEAP_20260904.csv

# Multiple crags combined
python tools/ticks_analysis.py \
  ../mtn-data/ticks/ticks_LOVERS_LEAP_20260904.csv \
  ../mtn-data/ticks/ticks_PHANTOM_SPIRES_20260904.csv
```

To resolve route slugs to full names + grades, set `routes_file` in the `__main__` block to the matching routes CSV, e.g. `"../mtn-data/routes/routes_LOVERS_LEAP_20260904.csv"`. Defaults: `top_n=20`, `start_date="2026-01-01"`.

---

## Notes

- **`route_analysis.py` and `climber_analysis.py`** take a **crag name** and auto-pick the newest matching CSVs.
- **`ticks_analysis.py`** takes **file paths** and lets you combine multiple crags in one report.
- Date filtering, `top_n`, and (for ticks_analysis) `routes_file` are set by editing the script's `__main__` block — they are not command-line flags.
