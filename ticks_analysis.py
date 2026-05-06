import csv
import os
import re
from collections import Counter, defaultdict
from datetime import datetime

def parse_pitches(details):
    match = re.search(r'(\d+)\s+pitch', details)
    return int(match.group(1)) if match else 1

def analyze_top_climbs(file, top_n=10, start_date=None, end_date=None, group_by="route"):
    """
    Analyze top climbs or climbers from a tick CSV file.
    group_by: "climber" (default) or "route"
    """
    if not os.path.exists(file):
        print(f"File not found: {file}")
        return

    def parse_date(date_str):
        return datetime.strptime(date_str, "%Y-%m-%d")

    if start_date:
        start_date = parse_date(start_date)
    if end_date:
        end_date = parse_date(end_date)

    tick_counter = Counter()
    pitch_counter = defaultdict(int)

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
    print(f"{'Name':40} | Ticks | Pitches")
    print("-" * 60)
    for name, ticks in tick_counter.most_common(top_n):
        print(f"{name:40} | {ticks:5} | {pitch_counter[name]}")


### ~~ USAGE ~~ ###
file = "ticks/ticks_TAHQUITZ.csv"

top_n = 20
start_date = "2025-01-01"
end_date = None
group_by = "route" # 'route' or 'climber'
analyze_top_climbs(file, top_n, start_date, end_date, group_by)

group_by = "climber" # 'route' or 'climber'
analyze_top_climbs(file, top_n, start_date, end_date, group_by)
