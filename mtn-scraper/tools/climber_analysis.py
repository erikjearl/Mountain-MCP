import csv
import glob
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'mtn-data')


def find_latest(subdir, prefix, crag):
    """Returns path to the most recent CSV matching prefix_CRAG_YYYYMMDD.csv, or None."""
    pattern = os.path.join(DATA_DIR, subdir, f"{prefix}_{crag}_????????.csv")
    matches = sorted(glob.glob(pattern))
    return matches[-1] if matches else None


def load_route_pitches(routes_file):
    """
    Loads a routes CSV and returns a dict mapping route slug → pitch count (int).
    Requires a routes CSV produced by the current scraper (must have a Pitches column).
    Returns an empty dict if routes_file is None or not found.
    """
    if not routes_file or not os.path.exists(routes_file):
        if routes_file:
            print(f"Warning: routes file not found: {routes_file}")
        return {}

    pitches = {}
    with open(routes_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        has_pitches_col = 'Pitches' in (reader.fieldnames or [])
        if not has_pitches_col:
            print(f"Warning: routes file has no Pitches column (old schema) — re-scrape to get accurate pitch counts.")
        for row in reader:
            try:
                pitches[row['Route']] = int(row['Pitches'])
            except (KeyError, ValueError):
                pitches[row['Route']] = 1
    return pitches


def analyze_climbers(ticks_files, routes_file, top_n=20, start_date=None, end_date=None):
    """
    Counts ticks and pitches per climber across one or more ticks CSVs.

    Pitch count per tick is taken from the routes CSV Pitches field (route-level pitch
    count — how many pitches the route has). This is more reliable than parsing the
    Details string, which is often absent or reflects a partial ascent.

    Falls back to 1 pitch per tick when the route is not found in the routes CSV.
    """
    route_pitches = load_route_pitches(routes_file)
    if not route_pitches:
        print("Warning: no route pitch data loaded — all ticks counted as 1 pitch.\n"
              "Set routes_file to the matching routes CSV for accurate pitch counts.")

    tick_counter = Counter()
    pitch_counter = defaultdict(int)
    skipped = 0

    for path in ticks_files:
        if not os.path.exists(path):
            print(f"File not found: {path}")
            continue
        with open(path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                try:
                    tick_date = datetime.strptime(row['Date'], "%b %d, %Y")
                except ValueError:
                    skipped += 1
                    continue

                if start_date and tick_date < start_date:
                    continue
                if end_date and tick_date > end_date:
                    continue

                climber = row['Name']
                route = row['Route']
                pitches = route_pitches.get(route, 1)

                tick_counter[climber] += 1
                pitch_counter[climber] += pitches

    if skipped:
        print(f"Skipped {skipped} rows with unparseable dates.")

    date_range = ""
    fmt = lambda d: d.strftime('%b %d, %Y')
    if start_date:
        display_end = end_date if end_date else datetime.now()
        date_range = f" ({fmt(start_date)} to {fmt(display_end)})"
    elif end_date:
        date_range = f" (through {fmt(end_date)})"
    print(f"\n~~ Top {top_n} Climbers{date_range} ~~")
    print(f"{'Name':40} | {'Ticks':>5} | {'Pitches':>7}")
    print("-" * 60)
    for climber, ticks in tick_counter.most_common(top_n):
        print(f"{climber[:40]:40} | {ticks:5} | {pitch_counter[climber]:7}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/climber_analysis.py <CRAG_NAME>")
        print("  CRAG_NAME: e.g. TAHQUITZ, JTREE_HV, MISSION_GORGE")
        print("  Edit start_date, end_date, and top_n in this script.")
        sys.exit(1)

    crag = sys.argv[1].upper()
    top_n = 25
    start_date = "2026-01-01"   # e.g. "2026-01-01"
    end_date = None     # e.g. "2026-12-31"

    ticks_file = find_latest("ticks", "ticks", crag)
    routes_file = find_latest("routes", "routes", crag)

    if not ticks_file:
        print(f"Error: no ticks data found for crag '{crag}' in {DATA_DIR}/ticks/")
        sys.exit(1)

    print(f"Ticks:  {os.path.basename(ticks_file)}")
    if routes_file:
        print(f"Routes: {os.path.basename(routes_file)}")

    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        scrape_date_str = os.path.basename(ticks_file).rsplit("_", 1)[-1].replace(".csv", "")
        try:
            end_date = datetime.strptime(scrape_date_str, "%Y%m%d")
        except ValueError:
            end_date = datetime.now()

    analyze_climbers([ticks_file], routes_file, top_n, start_date, end_date)
