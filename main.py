import csv
import gc
import time
from get_routes import get_routes
from get_ticks import get_ticks
from failed_routes import handle_failed_routes

# CRAG IDS
CRAGS = {
    "MISSION_GORGE": 105790250,
    "SANTEE_BOULDERS": 105915801,
    "MT_WOODSON": 105791148,
    "EL_CAJON_MTN": 105793290,
    "JTREE_HV": 119538702,
    "JTREE_CENTRAL": 119538644,
    "ARIZONA": 105708962,
    "ATLANTIS": 105792118,
    "MC_DOWELLS": 105787825,
    "PIMA_CANYON": 106671948,
    "BLACK_MOUNTAIN": 105991127,
    "TAHQUITZ": 105788031,
    "SUICIDE_ROCK": 105788036
}

# Select the crag
crag_name = "JTREE_HV"
crag_id = CRAGS[crag_name]
csv_file = f"ticks_{crag_name}.csv"


SLEEP_TIME = 10
failed_urls = []
total_ticks = 0

# get all routes in the crag
route_urls = get_routes(crag_id)
print(f"Found {len(route_urls)} routes.\n")

# get ticks from routes, writing incrementally to avoid holding everything in memory
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Route", "Name", "Date", "Details"])

    for i, url in enumerate(route_urls):
        print(f"Scraping ticks for route {i+1}/{len(route_urls)}: {url}")
        max_retries = 3
        attempt = 1
        ticks = None

        while attempt <= max_retries:
            try:
                ticks = get_ticks(url)
                if ticks is not None:
                    break

            except Exception as e:
                print(f"-Attempt {attempt} failed with error: {e}")

            time.sleep(SLEEP_TIME)
            attempt += 1

        if ticks is None:
            print(f"-ERROR! SKIPPING ROUTE: {url}")
            failed_urls.append(url)
            continue

        writer.writerows(ticks)
        total_ticks += len(ticks)
        gc.collect()

print(f"Wrote {total_ticks} rows to {csv_file}.")


## HANDLE FAILED URLS
if failed_urls:
    print("\nFailed URLs")
    for failed_url in failed_urls:
        print(f"  {failed_url}")
    
    print("\nRetrying failed URLs...")
    time.sleep(SLEEP_TIME)
    failed_urls = handle_failed_routes(failed_urls, csv_file, sleep_time=(SLEEP_TIME * 2))
    
    if failed_urls:
        print("\nStill failing URLs")
        for failed_url in failed_urls:
            print(f"  {failed_url}")
    else:
        print("\nAll failed URLs successfully scraped.")

else:
    print("\nNo URLs failed")