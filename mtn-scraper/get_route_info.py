import re
import requests
from bs4 import BeautifulSoup, NavigableString


def _parse_breadcrumb(soup):
    """
    Extracts the area hierarchy from the route page breadcrumb.
    Returns a list of (area_id, name, parent_id, full_path) tuples,
    ordered from top-level geography down to the route's immediate parent area.
    'All Locations' is skipped since it's not a real area.
    """
    breadcrumb_div = soup.find('div', class_='mb-half small text-warm')
    if not breadcrumb_div:
        return []

    areas = []
    path_names = []

    for link in breadcrumb_div.find_all('a', href=True):
        href = link['href']
        if '/area/' not in href:
            continue
        parts = href.rstrip('/').split('/')
        try:
            area_id = int(parts[-2])
        except (IndexError, ValueError):
            continue
        name = link.get_text(strip=True)
        path_names.append(name)
        full_path = ' > '.join(path_names)
        parent_id = areas[-1][0] if areas else ''
        areas.append((area_id, name, parent_id, full_path))

    return areas


def parse_route_page(html_str, route_slug):
    """
    Parses a Mountain Project route page and returns:
      route_row: (slug, name, grade, type, length, area_id)
      areas:     list of (area_id, name, parent_id, full_path) from breadcrumb
    area_id in route_row is the route's immediate parent area.
    """
    soup = BeautifulSoup(html_str, 'html.parser')

    # Route name from h1 first text node (h1 also contains an edit-icon link)
    name = ''
    h1 = soup.find('h1')
    if h1:
        for content in h1.children:
            if isinstance(content, NavigableString):
                text = content.strip()
                if text:
                    name = text
                    break

    # Grade: YDS for sport/trad, Hueco (V-scale) for boulders
    # Use the first text node only — the span also contains a nested "YDS"/"Hueco" label
    grade = ''
    grade_span = soup.find('span', class_='rateYDS') or soup.find('span', class_='rateHueco')
    if grade_span:
        for content in grade_span.children:
            if isinstance(content, NavigableString):
                text = content.strip()
                if text:
                    grade = text
                    break

    # Type and length from the description-details table
    # The Type cell contains combined info, e.g. "Trad, 100 ft (30 m)"
    route_type = ''
    length = ''
    desc_table = soup.find('table', class_='description-details')
    if desc_table:
        for row in desc_table.find_all('tr'):
            tds = row.find_all('td')
            if len(tds) >= 2 and 'Type:' in tds[0].get_text():
                type_cell = tds[1].get_text(strip=True)
                length_match = re.search(r'(\d[\d,]*)\s*ft', type_cell)
                if length_match:
                    length = length_match.group(0)
                route_type = re.sub(r',?\s*\d[\d,]*\s*ft.*', '', type_cell).strip()
                break

    # Area hierarchy from breadcrumb — last entry is the route's immediate parent
    areas = _parse_breadcrumb(soup)
    area_id = areas[-1][0] if areas else ''

    route_row = (route_slug, name, grade, route_type, length, area_id)
    return route_row, areas


def get_route_info(stats_url):
    route_url = stats_url.replace('/route/stats/', '/route/')
    route_slug = stats_url.rsplit('/', 1)[-1]

    r = requests.get(route_url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
    r.raise_for_status()

    return parse_route_page(r.text, route_slug)


if __name__ == '__main__':
    test_urls = [
        'https://www.mountainproject.com/route/stats/105722065/illusion-dweller',
        'https://www.mountainproject.com/route/stats/105791087/knob-job',
    ]
    for url in test_urls:
        route_row, areas = get_route_info(url)
        slug, name, grade, rtype, length, area_id = route_row
        print(f"\n{name}")
        print(f"  slug={slug}  grade={grade}  type={rtype}  length={length}  area_id={area_id}")
        print("  Area hierarchy:")
        for a in areas:
            print(f"    {a[0]:>12}  {a[3]}")
