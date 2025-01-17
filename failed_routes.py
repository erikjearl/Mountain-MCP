import csv
import time
from get_ticks import get_ticks

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

            print(f"  Waiting {sleep_time} seconds before the next attempt...")
            time.sleep(sleep_time)
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


if __name__ == "__main__":
    csv_file = "ticks_####.csv"
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