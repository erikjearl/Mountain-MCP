import csv
import glob
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'mtn-data')

SEND_STYLES = {'Lead / Onsight', 'Lead / Flash', 'Lead / Redpoint', 'Lead / Pinkpoint', 'Solo', 'Flash', 'Send'}
ATTEMPT_STYLES = {'Lead / Fell/Hung', 'Attempt'}
# Lead / Flash must come before bare Flash so substring match hits the more specific tag first.
STYLE_TAGS = [
    'Lead / Onsight', 'Lead / Flash', 'Lead / Redpoint', 'Lead / Pinkpoint',
    'Lead / Fell/Hung', 'Lead',
    'Solo', 'TR', 'Follow', 'Boulder',
    'Flash', 'Send', 'Attempt',
]


def find_latest(subdir, prefix, crag):
    """Returns path to the most recent CSV matching prefix_CRAG_YYYYMMDD.csv, or None."""
    pattern = os.path.join(DATA_DIR, subdir, f"{prefix}_{crag}_????????.csv")
    matches = sorted(glob.glob(pattern))
    return matches[-1] if matches else None


def load_routes(routes_file):
    """Returns dict: slug → {name, grade, type, pitches, area_id}"""
    if not routes_file or not os.path.exists(routes_file):
        if routes_file:
            print(f"Warning: routes file not found: {routes_file}")
        return {}
    routes = {}
    with open(routes_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if 'Pitches' not in (reader.fieldnames or []):
            print("Warning: routes file has no Pitches column (old schema) — re-scrape for accurate pitch counts.")
        for row in reader:
            try:
                pitches = int(row.get('Pitches', 1))
            except ValueError:
                pitches = 1
            routes[row['Route']] = {
                'name': row.get('Name', row['Route']),
                'grade': row.get('Grade', ''),
                'type': row.get('Type', '').split(',')[0].strip(),
                'pitches': pitches,
                'area_id': row.get('AreaID', ''),
            }
    return routes


def load_areas(areas_file):
    """Returns dict: area_id (str) → short name"""
    if not areas_file or not os.path.exists(areas_file):
        return {}
    areas = {}
    with open(areas_file, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            areas[row['AreaID']] = row['Name']
    return areas


def parse_style(details):
    for tag in STYLE_TAGS:
        if tag in details:
            return tag
    return None


def analyze_routes(ticks_file, routes, areas, top_n=25, start_date=None, end_date=None):
    tick_counter = Counter()
    pitch_totals = defaultdict(int)
    unique_climbers = defaultdict(set)
    send_counts = defaultdict(int)
    attempt_counts = defaultdict(int)
    skipped = 0

    with open(ticks_file, newline='', encoding='utf-8') as f:
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

            slug = row['Route']
            meta = routes.get(slug, {})
            pitches = meta.get('pitches', 1)
            style = parse_style(row.get('Details', ''))

            tick_counter[slug] += 1
            pitch_totals[slug] += pitches
            unique_climbers[slug].add(row['Name'])
            if style in SEND_STYLES:
                send_counts[slug] += 1
                attempt_counts[slug] += 1
            elif style in ATTEMPT_STYLES:
                attempt_counts[slug] += 1

    if skipped:
        print(f"Skipped {skipped} rows with unparseable dates.")

    top = tick_counter.most_common(top_n)

    # Group by area, rank areas by combined tick count
    area_groups = defaultdict(list)
    for slug, ticks in top:
        area_id = routes.get(slug, {}).get('area_id', '')
        area_groups[area_id].append((slug, ticks))
    area_order = sorted(area_groups, key=lambda aid: sum(t for _, t in area_groups[aid]), reverse=True)

    fmt = lambda d: d.strftime('%b %d, %Y')
    date_range = ""
    if start_date:
        display_end = end_date if end_date else datetime.now()
        date_range = f" ({fmt(start_date)} to {fmt(display_end)})"
    elif end_date:
        date_range = f" (through {fmt(end_date)})"

    print(f"\n~~ Top {top_n} Routes by Area{date_range} ~~")

    for area_id in area_order:
        group = area_groups[area_id]
        area_name = areas.get(area_id, area_id or "Unknown Area")
        area_ticks = sum(t for _, t in group)
        print(f"\n[ {area_name} ]  {area_ticks} ticks · {len(group)} routes")
        print(f"  {'Route (grade, type, pitches)':45} | {'Ticks':>5} | {'Pitches':>7} | {'Climbers':>8} | {'Send%':>5}")
        print("  " + "-" * 85)
        for slug, ticks in group:
            meta = routes.get(slug, {})
            name = meta.get('name', slug)
            grade = meta.get('grade', '')
            rtype = meta.get('type', '')
            pitches = meta.get('pitches', 1)
            label = f"{name} ({grade} {rtype} {pitches}p)".strip()
            total_pitches = pitch_totals[slug]
            climbers = len(unique_climbers[slug])
            attempts = attempt_counts[slug]
            sends = send_counts[slug]
            send_pct = f"{100 * sends // attempts}%" if attempts > 0 else "—"
            print(f"  {label[:45]:45} | {ticks:5} | {total_pitches:7} | {climbers:8} | {send_pct:>5}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/route_analysis.py <CRAG_NAME>")
        print("  CRAG_NAME: e.g. TAHQUITZ, JTREE_HV, MISSION_GORGE")
        print("  Edit top_n, start_date, end_date in this script.")
        sys.exit(1)

    crag = sys.argv[1].upper()
    top_n = 25
    start_date = "2025-01-01"
    end_date = None

    ticks_file  = find_latest("ticks",          "ticks",  crag)
    routes_file = find_latest("routes",          "routes", crag)
    areas_file  = find_latest("routes/areas",    "areas",  crag)

    if not ticks_file:
        print(f"Error: no ticks data found for crag '{crag}' in {DATA_DIR}/ticks/")
        sys.exit(1)

    print(f"Ticks:  {os.path.basename(ticks_file)}")
    if routes_file:
        print(f"Routes: {os.path.basename(routes_file)}")
    if areas_file:
        print(f"Areas:  {os.path.basename(areas_file)}")

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

    routes = load_routes(routes_file)
    areas  = load_areas(areas_file)

    if not routes:
        print("Warning: no route metadata — grades, types, and pitches will not be shown.")
    if not areas:
        print("Warning: no areas data — area names will not be shown.")

    analyze_routes(ticks_file, routes, areas, top_n, start_date, end_date)
