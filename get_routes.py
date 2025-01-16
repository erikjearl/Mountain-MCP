import requests
from bs4 import BeautifulSoup
import time

def get_route_urls(page_url):
    """
    Returns all /route/ links found on the given page URL.
    """
    response = requests.get(page_url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=True)

    route_urls = []
    for link in links:
        href = link['href']
        if '/route/' in href:
            # Convert to absolute URL if needed
            if href.startswith('/'):
                full_url = "https://www.mountainproject.com" + href
            else:
                full_url = href

            route_urls.append(full_url)

    return list(set(route_urls))  # deduplicate before returning


def get_all_pages(base_url):
    """
    Iterates pages (page=1, page=2, ...) until there are no more new routes.
    Returns a list of all unique /route/ URLs found across all pages.
    """
    all_route_urls = set()
    page_num = 1

    while True:
        page_url = f"{base_url}&page={page_num}"
        print(f"    Scraping: {page_url}")

        # Get routes for this page
        page_routes = get_route_urls(page_url)

        # If we find no routes on this page, assume we’re done
        if not page_routes:
            break

        # Check how many new routes we just found
        before_count = len(all_route_urls)
        all_route_urls.update(page_routes)
        after_count = len(all_route_urls)
        newly_added = after_count - before_count

        # If there were zero new routes, it probably means we’ve reached the end
        if newly_added == 0:
            break

        # Move on to the next page
        page_num += 1

        # (Optional) small delay to be polite to the server
        time.sleep(1)

    return sorted(all_route_urls)


def get_routes(id):
    print(f"    Scraping routes for crag ID: {id}")
    base_url = (
        "https://www.mountainproject.com/route-finder"
        "?selectedIds="+str(id)+
        "&type=rock"
        "&stars=0&diffMinrock=800&diffMaxrock=12400"
    )
    all_links = get_all_pages(base_url)
    return all_links

if __name__ == '__main__':
    id = 105790250
    all_links = get_routes(id)
    print(f"\nFound {len(all_links)} total route links:")
