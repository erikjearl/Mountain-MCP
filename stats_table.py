from requests_html import HTMLSession

def get_onx_stat_table_requests_html(url):
    session = HTMLSession()
    r = session.get(url)
    # Increase the timeout and wait for more JS to load
    r.html.render(timeout=30)

    # Find the first div with the class "main-content-container"
    main_content_div = r.html.find("div.main-content-container", first=True)
    if main_content_div:
        # Return just the HTML of that specific element
        return main_content_div.html
    else:
        return None

if __name__ == "__main__":
    stats_url = "https://www.mountainproject.com/route/stats/126649895/high-anxiety"
    html_snippet = get_onx_stat_table_requests_html(stats_url)

    if not html_snippet:
        print("Could not find <div class='main-content-container'> in the rendered DOM.")
    else:
        print("Got main-content-container HTML!")
        with open("content.html", "w", encoding="utf-8") as file:
            file.write(html_snippet)
