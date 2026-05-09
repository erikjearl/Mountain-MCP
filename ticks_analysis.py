import csv
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime


def parse_pitches(details):
    match = re.search(r'(\d+)\s+pitch', details)
    return int(match.group(1)) if match else 1


def load_routes(routes_file):
    """
    Loads a routes CSV and returns a dict mapping slug -> (name, grade, type).
    Returns empty dict if routes_file is None or doesn't exist.
    """
    if not routes_file or not os.path.exists(routes_file):
        if routes_file:
            print(f"Routes file not found: {routes_file}")
        return {}

    routes = {}
    with open(routes_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            routes[row['Route']] = (row.get('Name', ''), row.get('Grade', ''), row.get('Type', ''))
    return routes


def analyze_top_climbs(files, top_n=10, start_date=None, end_date=None, group_by="route", routes_file=None):
    if isinstance(files, str):
        files = [files]

    def parse_date(date_str):
        return datetime.strptime(date_str, "%Y-%m-%d")

    if start_date:
        start_date = parse_date(start_date)
    if end_date:
        end_date = parse_date(end_date)

    routes = load_routes(routes_file) if group_by == "route" else {}

    tick_counter = Counter()
    pitch_counter = defaultdict(int)

    for file in files:
        if not os.path.exists(file):
            print(f"File not found: {file}")
            continue

        with open(file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tick_date_str = row["Date"]

                try:
                    tick_date = datetime.strptime(tick_date_str, "%b %d, %Y")
                except ValueError:
                    continue

                if start_date and tick_date < start_date:
                    continue
                if end_date and tick_date > end_date:
                    continue

                key = row["Name"] if group_by == "climber" else row["Route"]
                tick_counter[key] += 1
                pitch_counter[key] += parse_pitches(row.get("Details", ""))

    title = "Climbers" if group_by == "climber" else "Routes"
    print(f"\n~~ Top {top_n} {title} ~~")
    print(f"{'Name':50} | Ticks | Pitches")
    print("-" * 70)
    for key, ticks in tick_counter.most_common(top_n):
        if group_by == "route" and routes:
            name, grade, rtype = routes.get(key, (key, '', ''))
            label = f"{name} ({grade} {rtype})".strip(" ()")
        else:
            label = key
        print(f"{label[:50]:50} | {ticks:5} | {pitch_counter[key]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ticks_analysis.py <ticks_file> [ticks_file2 ...]")
        sys.exit(1)

    files = sys.argv[1:]
    top_n = 20
    start_date = "2026-01-01"
    end_date = None

    # Optional: set to the matching routes CSV to show full route names and grades.
    # Example: "routes/routes_TAHQUITZ_20260507.csv"
    routes_file = None

    analyze_top_climbs(files, top_n, start_date, end_date, group_by="route", routes_file=routes_file)
    analyze_top_climbs(files, top_n, start_date, end_date, group_by="climber")
