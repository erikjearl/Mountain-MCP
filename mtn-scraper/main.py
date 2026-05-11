import csv
import gc
import os
import random
import time
from datetime import datetime
from get_routes import get_routes
from get_ticks import get_ticks
from get_route_info import get_route_info
from failed_routes import handle_failed_routes

# CRAG IDS
CRAGS = {
    # SO CAL
    "MISSION_GORGE": 105790250,
    "SANTEE_BOULDERS": 105915801,
    "MT_WOODSON": 105791148,
    "EL_CAJON_MTN": 105793290,
    "BLACK_MOUNTAIN": 105991127,
    "HOLCOMB": 105805238,
    "MALIBU_CREEK": 105870845,
    "TAHQUITZ": 105788031,
    "SUICIDE_ROCK": 105788036,

    # NOR CAL
    "SOUTH_BAY": 124936699,
    "NW_BAY": 124936802,
    "EAST_BAY": 124936753,

    # AZ
    "ATLANTIS": 105792118,
    "MC_DOWELLS": 105787825,
    "PIMA_CANYON": 106671948,

    # JOSH
    "JTREE_HV": 119538702,
    "JTREE_CENTRAL": 119538644,
    "JTREE_LHORSE": 105720588,
    "JTREE_QUAILS": 105720621,
    "JTREE_PINTO": 119538586,
}

# Quick local override — set this to any key from CRAGS to run without env vars
HARD_CODE_CRAG = 'MT_WOODSON'

# Resolve which crag to scrape.
# If only CRAG_NAME is set, it must be a key in the CRAGS dict above.
# Examples:
#   CRAG_NAME=YOSEMITE CRAG_ID=105833381   ← any crag, no code change needed
#   CRAG_NAME=TAHQUITZ                      ← looks up id from CRAGS dict
_env_name = os.environ.get('CRAG_NAME')
_env_id   = os.environ.get('CRAG_ID')

if _env_id and not _env_name:
    raise SystemExit("CRAG_ID is set but CRAG_NAME is not. Set both together.")

if _env_name and _env_id:
    try:
        crag_id = int(_env_id)
    except ValueError:
        raise SystemExit(f"CRAG_ID='{_env_id}' is not a valid integer.")
    crag_name = _env_name
elif _env_name:
    if _env_name not in CRAGS:
        raise SystemExit(f"Unknown CRAG_NAME '{_env_name}'. Either add it to CRAGS or also set CRAG_ID.")
    crag_name = _env_name
    crag_id   = CRAGS[_env_name]
elif HARD_CODE_CRAG:
    crag_name = HARD_CODE_CRAG
    crag_id   = CRAGS[crag_name]
else:
    raise SystemExit("No crag specified. Set CRAG_NAME (+ CRAG_ID if not in CRAGS dict), or set HARD_CODE_CRAG.")

DATA_DIR = os.environ.get('MTN_DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'mtn-data'))
os.makedirs(os.path.join(DATA_DIR, 'ticks'), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, 'routes'), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, 'routes', 'areas'), exist_ok=True)

date_stamp = datetime.now().strftime("%Y%m%d")
ticks_csv_file  = os.path.join(DATA_DIR, 'ticks',  f'ticks_{crag_name}_{date_stamp}.csv')
routes_csv_file = os.path.join(DATA_DIR, 'routes', f'routes_{crag_name}_{date_stamp}.csv')
areas_csv_file  = os.path.join(DATA_DIR, 'routes', 'areas', f'areas_{crag_name}_{date_stamp}.csv')

SLEEP_TIME = 3
failed_urls = []
failed_route_info_urls = []
total_ticks = 0
total_routes = 0
areas_seen = {}  # area_id -> (area_id, name, parent_id, full_path)

print(f"Scraping crag: {crag_name} (id={crag_id})")

route_urls = get_routes(crag_id)
print(f"Found {len(route_urls)} routes.\n")

with open(ticks_csv_file, "w", newline="", encoding="utf-8") as ticks_f, \
     open(routes_csv_file, "w", newline="", encoding="utf-8") as routes_f:

    ticks_writer = csv.writer(ticks_f)
    ticks_writer.writerow(["Route", "Name", "Date", "Details"])

    routes_writer = csv.writer(routes_f)
    routes_writer.writerow(["Route", "Name", "Grade", "Type", "Length", "AreaID"])

    for i, url in enumerate(route_urls):
        print(f"Scraping route {i+1}/{len(route_urls)}: {url}")

        # Fetch route metadata (plain requests, no JS needed)
        route_info_attempt = 1
        route_info_max_retries = 3
        while route_info_attempt <= route_info_max_retries:
            try:
                route_row, areas = get_route_info(url)
                routes_writer.writerow(route_row)
                routes_f.flush()
                total_routes += 1
                for area in areas:
                    areas_seen.setdefault(area[0], area)
                break
            except Exception as e:
                print(f"  -Route info attempt {route_info_attempt} failed: {e}")
                if route_info_attempt < route_info_max_retries:
                    time.sleep(5)
                else:
                    print(f"  -ERROR! Giving up on route info: {url}")
                    failed_route_info_urls.append(url)
            route_info_attempt += 1

        # Fetch ticks (JS-rendered stats page)
        max_retries = 3
        attempt = 1
        ticks = None

        while attempt <= max_retries:
            try:
                ticks = get_ticks(url)
                if ticks is not None:
                    break
            except Exception as e:
                print(f"  -Attempt {attempt} failed with error: {e}")

            time.sleep(random.uniform(SLEEP_TIME - 2, SLEEP_TIME + 2))
            attempt += 1

        if ticks is None:
            print(f"  -ERROR! SKIPPING TICKS: {url}")
            failed_urls.append(url)
            continue

        ticks_writer.writerows(ticks)
        ticks_f.flush()
        total_ticks += len(ticks)
        gc.collect()

print(f"Wrote {total_routes} rows to {routes_csv_file}.")
print(f"Wrote {total_ticks} rows to {ticks_csv_file}.")

# Write areas CSV — collected across all routes, deduplicated by area_id
with open(areas_csv_file, "w", newline="", encoding="utf-8") as areas_f:
    areas_writer = csv.writer(areas_f)
    areas_writer.writerow(["AreaID", "Name", "ParentID", "FullPath"])
    for area in areas_seen.values():
        areas_writer.writerow(area)
print(f"Wrote {len(areas_seen)} rows to {areas_csv_file}.")


## HANDLE FAILED URLS
if failed_urls:
    print("\nFailed URLs")
    for failed_url in failed_urls:
        print(f"  {failed_url}")

    print("\nRetrying failed URLs...")
    time.sleep(random.uniform(SLEEP_TIME - 2, SLEEP_TIME + 2))
    failed_urls = handle_failed_routes(failed_urls, ticks_csv_file, sleep_time=(SLEEP_TIME * 2))

    if failed_urls:
        print("\nStill failing URLs")
        for failed_url in failed_urls:
            print(f"  {failed_url}")
    else:
        print("\nAll failed URLs successfully scraped.")

else:
    print("\nNo URLs failed")

if failed_route_info_urls:
    print("\nRoutes with missing info (route page could not be scraped):")
    for url in failed_route_info_urls:
        print(f"  {url}")
else:
    print("\nAll route info scraped successfully.")

if failed_urls or failed_route_info_urls:
    raise SystemExit(1)
