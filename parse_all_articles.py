import requests

# Define the base URL for the Wikipedia API
base_url = "https://en.wikipedia.org/w/api.php"

# Define parameters for the initial API request
params = {
    "action": "query",
    "format": "json",
    "list": "allpages",
    "aplimit": "max",  # Set to retrieve maximum number of pages
}

# Make the initial API request
response = requests.get(base_url, params=params)
data = response.json()

# Extract the titles of all articles from the initial response
titles = [page["title"] for page in data["query"]["allpages"]]
for title in titles:
    full_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
    # append the full URL to a file named "all_articles.txt"
    with open("all_articles.txt", "a", encoding='utf-8') as file:
        file.write(full_url + "\n")

# Check if there are more results to fetch
while "continue" in data:
    # Get the value of "apcontinue" to continue from
    continue_param = data["continue"]["apcontinue"]
    
    # Add "apcontinue" to the parameters for the next request
    params["apcontinue"] = continue_param
    
    # Make the next API request
    response = requests.get(base_url, params=params)
    data = response.json()
    # get list of all titles
    titles = [page["title"] for page in data["query"]["allpages"]]
    for title in titles:
        full_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
        # append the full URL to a file named "all_articles.txt"
        with open("all_articles.txt", "a", encoding='utf-8') as file:
            file.write(full_url + "\n")
    print(f"Added {len(titles)} articles to all_articles.txt")

# Print the full URLs of all articles
    
