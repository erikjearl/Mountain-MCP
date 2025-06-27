import csv
import os
from collections import Counter
from datetime import datetime

def analyze_top_climbs(file, top_n=10, start_date=None, end_date=None, group_by="route"):
    """
    Analyze top climbs or climbers from a tick CSV file.
    group_by: "climber" (default) or "route"
    """
    if not os.path.exists(file):
        print(f"File not found: {file}")
        return

    # Parse input dates
    def parse_date(date_str):
        return datetime.strptime(date_str, "%Y-%m-%d")

    if start_date:
        start_date = parse_date(start_date)
    if end_date:
        end_date = parse_date(end_date)

    counter = Counter()

    with open(file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tick_date_str = row["Date"]

            try:
                tick_date = datetime.strptime(tick_date_str, "%b %d, %Y")
            except ValueError:
                continue  # Skip malformed dates

            if start_date and tick_date < start_date:
                continue
            if end_date and tick_date > end_date:
                continue

            key = row["Name"] if group_by == "climber" else row["Route"]
            counter[key] += 1

    title = "Climbers" if group_by == "climber" else "Routes"
    print(f"\n~~ Top {top_n} {title} ~~")
    print(f"{'Name':40} | Count")
    print("-" * 55)
    for name, count in counter.most_common(top_n):
        print(f"{name:40} | {count}")


### ~~ USAGE ~~ ###
file = "ticks/ticks_MT_WOODSON_02-Jun-25.csv"

top_n = 20
start_date = "2025-01-01"
end_date = None
group_by = "route" # 'route' or 'climber'
analyze_top_climbs(file, top_n, start_date, end_date, group_by)

group_by = "climber" # 'route' or 'climber'
analyze_top_climbs(file, top_n, start_date, end_date, group_by)
