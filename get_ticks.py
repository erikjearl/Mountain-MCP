import csv
from bs4 import BeautifulSoup
from requests_html import HTMLSession

# get 'main-content-container' from html
def get_onx_stat_table_requests_html(url):
    session = HTMLSession()
    r = session.get(url)
    r.html.render(timeout=30)

    main_content_div = r.html.find("div.main-content-container", first=True)
    if main_content_div:
        
        return main_content_div.html
    else:
        return None

def parse_ticks_direct(html_str, route_name):
    soup = BeautifulSoup(html_str, "html.parser")

    # Find all <table class="table table-striped">
    all_tables = soup.find_all("table", class_="table table-striped")
    ticks_table = None

    for table in all_tables:
        # Check if this table has at least one row whose ID starts with "ticks."
        tick_row = table.find("tr", id=lambda x: x and x.startswith("ticks."))
        if tick_row:
            ticks_table = table
            break

    if not ticks_table:
        print("    Error: could not find any table with <tr> id='ticks.'")
        return

    rows = ticks_table.find_all("tr", id=lambda x: x and x.startswith("ticks."))

    results = []
    for row in rows:
        tds = row.find_all("td", recursive=False)
        if len(tds) < 2:
            continue

        # user name in td[0]
        user_link = tds[0].find("a")
        user_name = user_link.get_text(strip=True) if user_link else tds[0].get_text(strip=True)

        # date & details in td[1]
        strong_tag = tds[1].find("strong")
        date_text = strong_tag.get_text(strip=True) if strong_tag else ""

        details_div = tds[1].find("div", class_="small")
        details_text = details_div.get_text(" ", strip=True) if details_div else ""

        results.append((route_name, user_name, date_text, details_text))

    return results

def write_to_csv(results, csv_file="ticks_example.csv"):
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Route", "Name", "Date", "Details"])
        writer.writerows(results)
    print(f"Wrote {len(results)} rows to {csv_file}.")


def get_ticks(url):
    print(f"    Parsing Route: {url}")
    html_string = get_onx_stat_table_requests_html(url)
    route_name = url.rsplit('/', 1)[-1]
    ticks = parse_ticks_direct(html_string, route_name)
    return ticks

if __name__ == "__main__":
    url = "https://www.mountainproject.com/route/stats/105791087/knob-job"
    ticks = get_ticks(url)
    write_to_csv(ticks, "test-ticks.csv")