# Wikipedia First-Link Graph

Explores the "getting to Philosophy" phenomenon: starting from a random Wikipedia article and repeatedly following the first link of the body text that is not inside parentheses, most paths end in the same loop. The scraper fetches pages with `requests`, finds the first valid link with BeautifulSoup (skipping parenthesised text by tracking bracket depth, citations, and namespace pages), and records every visited article in a persistent graph with its distance to the attractor; new paths stop as soon as they hit a known article, a loop or a dead end. Statistics such as the largest loop, the farthest article and the number of dead ends can then be queried. A multiprocessing version runs several explorations in parallel with a shared lock.

## How to run
Python 3 with `requests`, `beautifulsoup4`, `lxml`. `python Link.py` (or `Link_multi_processing.py` for parallel runs) starts the search and saves state in `instances.pkl`, `loops.pkl`, `failed_paths.pkl`; `parse_all_articles.py` lists all article URLs through the MediaWiki API.

## Notes
- The `.pkl` files with the collected graph are not included in the repository.
- `wikipedia_phylosophy_search.py` is the original function-based version; `pretty_print.html` is a saved page used to debug the link parser.
