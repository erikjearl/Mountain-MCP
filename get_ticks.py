import asyncio
import csv
from bs4 import BeautifulSoup
from requests_html import HTMLSession

# get 'main-content-container' from html
def get_onx_stat_table_requests_html(url):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    session = HTMLSession()
    try:
        r = session.get(url)
        r.html.render(timeout=30)
        main_content_div = r.html.find("div.main-content-container", first=True)
        if main_content_div:
            return main_content_div.html
        return None
    finally:
        session.close()
        loop.close()

from bs4 import BeautifulSoup

def parse_ticks_direct(html_str, route_name):
    """
    Parses the HTML string to extract ticks for a given route.
    """
    soup = BeautifulSoup(html_str, "html.parser")

    # 1) Check how many total ticks are reported
    #    Look for something like: 
    #    <h3>Ticks <span class="small text-muted">0</span></h3>
    ticks_count_span = soup.select_one("h3:-soup-contains('Ticks') span.small.text-muted")

    # If we found the span, parse out the number
    if ticks_count_span:
        ticks_count_str = ticks_count_span.get_text(strip=True)
        try:
            ticks_count = int(ticks_count_str)
            # If the page says Ticks 0, then there's nothing to parse
            if ticks_count == 0:
                print(f"    Ticks reported as 0 for {route_name}")
                return []
        except ValueError:
            # If it's not a number for some reason, just ignore.
            pass

    # 2) Now proceed to find the actual table with tick rows if ticks_count > 0
    #    or if we couldn't parse the count for some reason.
    ticks_table = None
    all_tables = soup.find_all("table", class_="table table-striped")
    for table in all_tables:
        tick_row = table.find("tr", id=lambda x: x and x.startswith("ticks."))
        if tick_row:
            ticks_table = table
            break

    if not ticks_table:
        print(f"    ERROR: No ticks table found for {route_name}")
        return None

    # 3) Extract the rows
    rows = ticks_table.find_all("tr", id=lambda x: x and x.startswith("ticks."))
    results = []

    for row in rows:
        tds = row.find_all("td", recursive=False)
        if len(tds) < 2:
            # If the table format doesn't match expectations, skip
            continue

        # user name in the first <td>
        user_link = tds[0].find("a")
        user_name = user_link.get_text(strip=True) if user_link else tds[0].get_text(strip=True)

        # date & details in the second <td>
        strong_tag = tds[1].find("strong")
        date_text = strong_tag.get_text(strip=True) if strong_tag else ""

        details_div = tds[1].find("div", class_="small")
        details_text = details_div.get_text(" ", strip=True) if details_div else ""

        results.append((route_name, user_name, date_text, details_text))

    return results


def get_ticks(url):
    print(f"    Parsing Route: {url}")
    html_string = get_onx_stat_table_requests_html(url)
    route_name = url.rsplit('/', 1)[-1]
    ticks = parse_ticks_direct(html_string, route_name)
    return ticks


if __name__ == "__main__":
    url = "https://www.mountainproject.com/route/stats/105791087/knob-job"
    ticks = get_ticks(url)
    print(f"\nREPORT: Found {len(ticks)} ticks")