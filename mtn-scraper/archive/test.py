import requests
from bs4 import BeautifulSoup
import csv

def scrape_ticks(url, output_csv="ticks.csv"):
    # 1. Fetch the page
    resp = requests.get(url)
    resp.raise_for_status()
    
    # 2. Parse HTML with BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # 3. Find all <table class="table table-striped">
    all_tables = soup.find_all("table", class_="table table-striped")
    ticks_table = None
    
    for table in all_tables:
        # Check if this table has any <tr> whose id starts with "ticks."
        potential_ticks = table.find("tr", id=lambda x: x and x.startswith("ticks."))
        if potential_ticks:
            # Found the correct table
            ticks_table = table
            break
    
    if not ticks_table:
        print("Could not find a table containing ticks.* rows.")
        return
    
    # 4. Extract each Ticks row (id="ticks.something")
    tbody = ticks_table.find("tbody")
    rows = tbody.find_all("tr", id=lambda x: x and x.startswith("ticks.")) if tbody else []
    
    print(f"Found {len(rows)} tick rows.")
    
    # 5. Write results to CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Date", "Details"])  # customize columns if needed

        for row in rows:
            tds = row.find_all("td", recursive=False)
            if len(tds) < 2:
                continue
            
            # --- Name or "Private Tick" is in the first <td> ---
            user_td = tds[0]
            user_a = user_td.find("a")
            if user_a:
                name = user_a.get_text(strip=True)
            else:
                # e.g. "Private Tick"
                name = user_td.get_text(strip=True)
            
            # --- Date & style/notes are in the second <td> ---
            info_td = tds[1]
            date_tag = info_td.find("strong")
            date_text = date_tag.get_text(strip=True) if date_tag else ""
            
            # The rest of the text (e.g., "Lead / Onsight. Some notes...")
            info_div = info_td.find("div", class_="small")
            details_text = info_div.get_text(" ", strip=True) if info_div else ""
            
            writer.writerow([name, date_text, details_text])
    
    print(f"Done. Saved {len(rows)} rows to {output_csv}.")

if __name__ == "__main__":
    url = "https://www.mountainproject.com/route/stats/105792696/the-tower"
    scrape_ticks(url, "ticks.csv")
