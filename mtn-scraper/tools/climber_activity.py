"""
climber_activity.py — Who was at the crag recently, and what did they climb?

Lists every climber who logged a tick in the given time window, grouped by
climber and sorted by most-active first.  For each climber shows every route
they did: date, full route name, grade, type, pitch count, and tick style.

Usage
-----
  python tools/climber_activity.py <CRAG_NAME>           # last 3 days
  python tools/climber_activity.py <CRAG_NAME> --days 7  # last N days
  python tools/climber_activity.py <CRAG_NAME> --start 2026-05-20 --end 2026-05-25

CRAG_NAME examples: TAHQUITZ, JTREE_HV, MISSION_GORGE, BLACK_MOUNTAIN
"""

import argparse
import csv
import glob
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'mtn-data')

# Ordered most-specific-first so substring matching picks the right tag.
STYLE_TAGS = [
    'Lead / Onsight', 'Lead / Flash', 'Lead / Redpoint', 'Lead / Pinkpoint',
    'Lead / Fell/Hung', 'Lead',
    'Solo', 'TR', 'Follow', 'Boulder',
    'Flash', 'Send', 'Attempt',
]

SEND_STYLES = {
    'Lead / Onsight', 'Lead / Flash', 'Lead / Redpoint', 'Lead / Pinkpoint',
    'Solo', 'Flash', 'Send',
}


# ── helpers ──────────────────────────────────────────────────────────────────

def find_latest(subdir, prefix, crag):
    """Return the most-recent CSV matching prefix_CRAG_YYYYMMDD.csv, or None."""
    pattern = os.path.join(DATA_DIR, subdir, f"{prefix}_{crag}_????????.csv")
    matches = sorted(glob.glob(pattern))
    return matches[-1] if matches else None


def scrape_date_from_path(path):
    """Extract the embedded date from a filename like ticks_TAHQUITZ_20260525.csv."""
    stem = os.path.basename(path).replace('.csv', '')
    date_str = stem.rsplit('_', 1)[-1]
    try:
        return datetime.strptime(date_str, '%Y%m%d')
    except ValueError:
        return datetime.now()


def load_routes(routes_file):
    """Return dict: slug → {name, grade, type, pitches}."""
    if not routes_file or not os.path.exists(routes_file):
        if routes_file:
            print(f"Warning: routes file not found: {routes_file}")
        return {}
    routes = {}
    with open(routes_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if 'Pitches' not in (reader.fieldnames or []):
            print("Warning: routes file has no Pitches column — re-scrape for accurate pitch counts.")
        for row in reader:
            try:
                pitches = int(row.get('Pitches', 1))
            except ValueError:
                pitches = 1
            routes[row['Route']] = {
                'name':    row.get('Name', row['Route']),
                'grade':   row.get('Grade', ''),
                'type':    row.get('Type', '').split(',')[0].strip(),
                'pitches': pitches,
            }
    return routes


def parse_style(details):
    for tag in STYLE_TAGS:
        if tag in details:
            return tag
    return None


# ── core analysis ─────────────────────────────────────────────────────────────

def build_climber_map(ticks_file, routes, start_date, end_date):
    """
    Returns a dict:
      climber_name → [
        {date, route_slug, route_name, grade, type, pitches, style, send},
        ...
      ]
    sorted within each climber by date ascending.
    Also returns skipped-row count.
    """
    climbers = defaultdict(list)
    skipped = 0

    with open(ticks_file, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                tick_date = datetime.strptime(row['Date'].strip(), "%b %d, %Y")
            except ValueError:
                skipped += 1
                continue

            if tick_date < start_date or tick_date > end_date:
                continue

            slug    = row['Route']
            meta    = routes.get(slug, {})
            details = row.get('Details', '')
            style   = parse_style(details)

            climbers[row['Name']].append({
                'date':       tick_date,
                'route_slug': slug,
                'name':       meta.get('name', slug),
                'grade':      meta.get('grade', ''),
                'type':       meta.get('type', ''),
                'pitches':    meta.get('pitches', 1),
                'style':      style or '',
                'send':       style in SEND_STYLES,
            })

    # Sort each climber's ticks by date
    for ticks in climbers.values():
        ticks.sort(key=lambda t: t['date'])

    return dict(climbers), skipped


def print_report(climbers, start_date, end_date):
    fmt = lambda d: d.strftime('%b %d, %Y')
    date_range = f"{fmt(start_date)} – {fmt(end_date)}"

    # Sort climbers: most ticks first, then alphabetical on ties
    ordered = sorted(climbers.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    total_ticks = sum(len(v) for v in climbers.values())
    print(f"\n~~ Climber Activity  {date_range} ~~")
    print(f"{len(climbers)} climbers · {total_ticks} ticks\n")

    for climber, ticks in ordered:
        send_count = sum(1 for t in ticks if t['send'])
        pitch_total = sum(t['pitches'] for t in ticks)
        header = (
            f"  {climber}"
            f"  [{len(ticks)} tick{'s' if len(ticks) != 1 else ''}"
            f", {pitch_total} pitch{'es' if pitch_total != 1 else ''}"
            f", {send_count} send{'s' if send_count != 1 else ''}]"
        )
        print(header)

        for t in ticks:
            label = t['name']
            meta_parts = [p for p in [t['grade'], t['type']] if p]
            if t['pitches'] and t['pitches'] > 1:
                meta_parts.append(f"{t['pitches']}p")
            meta = f"  ({', '.join(meta_parts)})" if meta_parts else ''
            style_tag = f"  {t['style']}" if t['style'] else ''
            date_str = t['date'].strftime('%b %d')
            print(f"    {date_str}  {label}{meta}{style_tag}")

        print()


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="List every climber active at a crag in a time window.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('crag', metavar='CRAG_NAME',
                        help='e.g. TAHQUITZ, JTREE_HV, MISSION_GORGE')
    parser.add_argument('--days', type=int, default=3,
                        help='Window size in days ending at the scrape date (default: 3)')
    parser.add_argument('--start', metavar='YYYY-MM-DD',
                        help='Explicit start date (overrides --days)')
    parser.add_argument('--end', metavar='YYYY-MM-DD',
                        help='Explicit end date (default: scrape date)')
    args = parser.parse_args()

    crag = args.crag.upper()

    ticks_file  = find_latest('ticks',       'ticks',  crag)
    routes_file = find_latest('routes',      'routes', crag)

    if not ticks_file:
        print(f"Error: no ticks data found for crag '{crag}' in {DATA_DIR}/ticks/")
        sys.exit(1)

    print(f"Ticks:  {os.path.basename(ticks_file)}")
    if routes_file:
        print(f"Routes: {os.path.basename(routes_file)}")
    else:
        print("Warning: no routes file found — route names and grades will not be resolved.")

    # Resolve date window
    scrape_dt = scrape_date_from_path(ticks_file)

    if args.end:
        end_date = datetime.strptime(args.end, '%Y-%m-%d')
    else:
        end_date = scrape_dt

    if args.start:
        start_date = datetime.strptime(args.start, '%Y-%m-%d')
    else:
        start_date = end_date - timedelta(days=args.days - 1)

    routes = load_routes(routes_file)

    climbers, skipped = build_climber_map(ticks_file, routes, start_date, end_date)

    if skipped:
        print(f"Skipped {skipped} rows with unparseable dates.")

    if not climbers:
        print(f"\nNo ticks found between {start_date.strftime('%b %d, %Y')} and {end_date.strftime('%b %d, %Y')}.")
        sys.exit(0)

    print_report(climbers, start_date, end_date)


if __name__ == '__main__':
    main()
