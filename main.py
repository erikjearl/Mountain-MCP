import csv
import time
from get_routes import get_routes
from get_ticks import get_ticks
from failed_routes import handle_failed_routes

# CRAG IDS
MISSION_GORGE = 105790250
ATLANTIS = 105792118
PIMA_CANYON = 106671948

crag_id = PIMA_CANYON
csv_file = f"ticks_{crag_id}.csv"
SLEEP_TIME = 10
all_ticks = []
failed_urls = []

# get all routes in the crag
route_urls = get_routes(crag_id)
print(f"Found {len(route_urls)} routes.\n")

# get ticks from routes
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

    all_ticks.extend(ticks)

with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Route", "Name", "Date", "Details"])
    writer.writerows(all_ticks)

print(f"Wrote {len(all_ticks)} rows to {csv_file}.")


## HANDLE FAILED URLS
if failed_urls:
    print("\nFailed URLs")
    for failed_url in failed_urls:
        print(f"  {failed_url}")
    
    print("\nRetrying failed URLs...")
    failed_urls = handle_failed_routes(failed_urls, csv_file, sleep_time=SLEEP_TIME)
    
    if failed_urls:
        print("\nStill failing URLs")
        for failed_url in failed_urls:
            print(f"  {failed_url}")
    else:
        print("\nAll failed URLs successfully scraped.")

else:
    print("\nNo URLs failed")