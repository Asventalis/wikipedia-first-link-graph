import wikipedia_phylosophy_search as wps
from bs4 import BeautifulSoup

# instances = wps.load("instances.pkl")
# loops = wps.load("loops.pkl")
# failed_paths = wps.load("failed_paths.pkl")
# wps.link_search(instances, loops, failed_paths, verbose_level=1)


url = "https://en.wikipedia.org/wiki/Philosophy"
max_tries = 5
verbose = True

response = wps.HTTP_request(url, max_tries=max_tries, verbose=verbose)

html_content = response.text
soup = BeautifulSoup(html_content, 'lxml')

p_elements = soup.select('div.mw-content-ltr.mw-parser-output > p:not([class])')
if not p_elements:
    if verbose: print("no p elements found inside the page")

links = []
for p in p_elements:
    links += wps.get_all_links_not_in_brackets(p, verbose=verbose, recursive=True)
