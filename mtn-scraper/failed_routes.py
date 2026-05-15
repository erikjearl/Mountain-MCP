import csv
import random
import time
from get_ticks import get_ticks
from get_route_info import get_route_info

def handle_failed_routes(failed_urls, csv_file, max_retries=5, sleep_time=10):
    """
    Given a list of failed route URLs, re-scrape them and append to the given CSV file.
    Returns a list of any URLs that are still failing after this process.
    """
    all_ticks = []
    still_failed_urls = []

    for i, url in enumerate(failed_urls):
        print(f"Scraping ticks for failed route {i+1}/{len(failed_urls)}: {url}")
        attempt = 1
        ticks = None

        while attempt <= max_retries:
            try:
                ticks = get_ticks(url)  
                if ticks is not None:
                    break
            except Exception as e:
                print(f"  -Attempt {attempt} failed with error: {e}")

            actual_sleep = random.uniform(sleep_time - 2, sleep_time + 2)
            print(f"  Waiting {actual_sleep:.1f} seconds before the next attempt...")
            time.sleep(actual_sleep)
            attempt += 1

        # If ticks is still None, it means we never succeeded
        if ticks is None:
            print(f"  -ERROR! Still cannot scrape ticks for: {url}")
            still_failed_urls.append(url)
            continue

        all_ticks.extend(ticks)

    # Append any new tick data to the CSV
    if all_ticks:
        with open(csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(all_ticks)

        print(f"\nAppended {len(all_ticks)} rows to {csv_file}.")
    else:
        print("\nNo new ticks found to append.")

    return still_failed_urls


def handle_failed_route_info(failed_urls, routes_csv_file, areas_seen, max_retries=5, sleep_time=10):
    """
    Retries get_route_info for URLs that failed in the main loop.
    Appends recovered route rows to routes_csv_file and updates areas_seen in-place.
    Returns list of URLs still failing after all retries.
    """
    new_rows = []
    still_failed = []

    for i, url in enumerate(failed_urls):
        print(f"Retrying route info {i+1}/{len(failed_urls)}: {url}")
        attempt = 1
        success = False

        while attempt <= max_retries:
            try:
                route_row, areas = get_route_info(url)
                for area in areas:
                    areas_seen.setdefault(area[0], area)
                new_rows.append(route_row)
                success = True
                break
            except Exception as e:
                print(f"  -Attempt {attempt} failed: {e}")

            actual_sleep = random.uniform(sleep_time - 2, sleep_time + 2)
            print(f"  Waiting {actual_sleep:.1f} seconds before the next attempt...")
            time.sleep(actual_sleep)
            attempt += 1

        if not success:
            print(f"  -ERROR! Still cannot scrape route info for: {url}")
            still_failed.append(url)

    if new_rows:
        with open(routes_csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(new_rows)
        print(f"\nAppended {len(new_rows)} route info rows to {routes_csv_file}.")
    else:
        print("\nNo route info recovered in retry pass.")

    return still_failed


if __name__ == "__main__":
    import os
    data_dir = os.environ.get('MTN_DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'mtn-data'))
    csv_file = os.path.join(data_dir, 'ticks', 'ticks_####.csv')  # replace #### with the actual filename
    failed_urls = [
                    # "https://www.mountainproject.com/route/stats/107694100/merryanne",
                    # "https://www.mountainproject.com/route/stats/119371997/balrog",
                    # "https://www.mountainproject.com/route/stats/123248837/itwillbegotten",
                    # "https://www.mountainproject.com/route/stats/124336318/flake-of-rust",
                    # "https://www.mountainproject.com/route/stats/124784096/rock-on-left",
                    # "https://www.mountainproject.com/route/stats/124912832/topped-off",
                    # "https://www.mountainproject.com/route/stats/124926407/lunch-rock-direct",
                    # "https://www.mountainproject.com/route/stats/125199924/acrobat",
                    # "https://www.mountainproject.com/route/stats/125324167/chimney-sweep",
                    # "https://www.mountainproject.com/route/stats/125596927/fare-thee-well",
                    # "https://www.mountainproject.com/route/stats/126584398/moments-of-zen",
                    # "https://www.mountainproject.com/route/stats/126872221/cam-jam",
                    # "https://www.mountainproject.com/route/stats/126876373/bolg",
                    # "https://www.mountainproject.com/route/stats/127310247/celebrimbor",
                    # "https://www.mountainproject.com/route/stats/108837861/the-shaman-and-the-priest",
                    # "https://www.mountainproject.com/route/stats/108837872/sacred-land",
                    # "https://www.mountainproject.com/route/stats/108837899/grinding-stone-mantle",
                    # "https://www.mountainproject.com/route/stats/118959708/quarantine-dreaming-vs-danger-noodle",
                    # "https://www.mountainproject.com/route/stats/125516302/flight-of-the-missionary"
    ]

    remaining_failed = handle_failed_routes(failed_urls, csv_file, max_retries=3, sleep_time=5)

    if remaining_failed:
        print("\nThese URLs are still failing after retries:")
        for url in remaining_failed:
            print(f"  {url}")
    else:
        print("\nAll previously failed URLs scraped successfully!")