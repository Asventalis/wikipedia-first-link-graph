import pickle
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import json



def HTTP_request(url, max_tries=10, verbose=False):
    tries = 0
    response = None
    while response is None and tries < max_tries:
        if verbose and tries > 0: print("retrying... (try", tries, "of", max_tries, ")")
        if verbose: print("sending HTTP request for:", url)
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            print("ERROR:", url, "caused Http Error:", errh)
            response = None
        except requests.exceptions.ConnectionError as errc:
            print("ERROR:", url, "caused Error Connecting:", errc)
            response = None
        except requests.exceptions.Timeout as errt:
            print("ERROR:", url, "caused Timeout Error:", errt)
            response = None
        except requests.exceptions.RequestException as err:
            print("ERROR:", url, "caused Unidentified Error:", err)
            response = None
        tries += 1
    
    if response is None:
        if verbose: print("max tries reached, operation failed")
        return None
    if verbose: print("response received successfully")
    return response


def get_all_links_not_in_brackets(node, verbose=False):
    if verbose: print("initiating search for links only outside brackets. Going through all children...")
    ignore = False
    counter = 0
    if verbose:
        for child in node.children:
            counter += 1
            child_outerHTML = str(child)
            print(f"{counter}:", child_outerHTML)
    counter = 0
    nested_count = 0
    links = []
    for child in node.children:
        counter += 1
        child_outerHTML = str(child)
        ignore_string = '(ignoring)     >' if ignore else '(not ignoring) >'
        control_string = ''
        tag_name = f"<{child.name}>" if child.name is not None else "text"
        if isinstance(child, NavigableString):
            if '(' in child:
                ignore = True
                nested_count += 1
                control_string = ' and contains (: activate ignoring' if nested_count == 1 else ''
            if ')' in child:
                nested_count -= 1
                ignore = False if nested_count == 0 else True
                control_string = ' and contains ): deactivate ignoring' if nested_count == 0 else ''
        elif (child.name == 'a') and ('href' in child.attrs) and (not ignore):
            links.append(child['href'])
            control_string = f' and is not ignored: link {child['href']} added'
        else:
            control_string = ''
        if verbose: print(f"{ignore_string} {counter}: {tag_name} node{control_string}")
    if verbose: print("search completed. Returning all links found")
    return links


class Link:
    instances = {}
    loops = []
    failed_paths = []

    # def __init__(self, url):
    #     self.url = url
    #     self.loop = -2
    #     self.converges_to = -1
    #     self.distance_from_loop = -1
    #     self.first_link = Link.get_next_link(url)


    @staticmethod
    def save(instances_file = 'instances.pkl', loops_file = 'loops.pkl', failed_paths_file = 'failed_paths.pkl'):
        with open(instances_file, 'wb') as f:
            pickle.dump(Link.instances, f)
        with open(loops_file, 'wb') as f:
            pickle.dump(Link.loops, f)
        with open(failed_paths_file, 'wb') as f:
            pickle.dump(Link.failed_paths, f)

    @staticmethod
    def load(instances_file = 'instances.pkl', loops_file = 'loops.pkl', failed_paths_file = 'failed_paths.pkl'):
        with open(instances_file, 'rb') as f:
            print(f.name)
            Link.instances = pickle.load(f)
        with open(loops_file, 'rb') as f:
            Link.loops = pickle.load(f)
        with open(failed_paths_file, 'rb') as f:
            Link.failed_paths = pickle.load(f)

    # Genera random link da Wikipedia. Ritorna None se non riesce a fare la richiesta HTTP
    @staticmethod
    def generate_random_wikipedia_link(max_tries=10, verbose=False):
        if verbose: print("generating random Wikipedia link")
        url = 'https://en.wikipedia.org/wiki/Special:Random'
        response = HTTP_request(url, max_tries=max_tries, verbose=verbose)
        if response is None:
            return None
        random_link = response.url
        return random_link

    # Ritorna il primo link di una pagina Wikipedia. Ritorna None se non riesce a fare la richiesta HTTP o a trovare il link
    @staticmethod
    def get_next_link(url, max_tries=10, verbose=False):
        if verbose: print("scraping next link from:", url)
        response = HTTP_request(url, max_tries=max_tries, verbose=verbose)
        if response is None:
            return -1

        # response.encoding = 'utf-8'
        # with open('pretty_print.html', 'w', encoding='utf-8') as f:
        #     f.write(response.text)

        html_content = response.text
        soup = BeautifulSoup(html_content, 'lxml')

        p_elements = soup.select('div.mw-content-ltr.mw-parser-output > p:not([class])')
        if not p_elements:
            if verbose: print("no p elements found inside the page")
            return None
        
        links = []
        for p in p_elements:
            links += get_all_links_not_in_brackets(p, verbose=verbose)

        if not links:
            if verbose: print("no link found inside the page")
            return None
        
        for link in links:
            if '#' in link:
                link = link.split('#')[0]
            if link.startswith('/wiki/'):
                link = 'https://en.wikipedia.org' + link
            
            if  not link.startswith('https://en.wikipedia.org/'):
                if verbose: print(f"link {link} is not in the Wikipedia domain, skipping")
                continue
            elif 'cite_note' in link:
                if verbose: print(f"link {link} is a cite note, skipping")
                continue
            elif ':' in link.split('/wiki/')[1]:
                special_word = link.split('/wiki/')[1].split(':')[0]
                if verbose: print(f"link {link} contains :{special_word}, skipping")
                continue
            else:
                if verbose: print("next link found:", link)
                return link
        if verbose: print("no valid link found inside the page")
        return None

    @staticmethod
    def link_search(iterations = -1, max_tries = 10, verbose_level = 0):
        verbose = verbose_level > 0
        nested_verbose_1 = verbose_level > 1
        nested_verbose_2 = verbose_level > 2
        iteration_count = 0
        while True:
            if iterations != -1:
                if verbose: print("ITERATION", iteration_count, "OF", iterations)
                if iteration_count >= iterations:
                    if verbose: print("MAX ITERATIONS REACHED, STOPPING SEARCH")
                    break
            else:
                if verbose: print("ITERATION", iteration_count)
            if verbose: print("generating random link...")
            link = Link.generate_random_wikipedia_link(max_tries, nested_verbose_2)
            if link is None:
                if verbose: print("failed to generate random link, skipping iteration")
                continue
            if verbose: print("random link generated:", link)
            if link not in Link.instances:
                if verbose: print("link not in instances. Initiating path exploration...")
                if verbose: print("PATH")
                link_list = []
                counter = 0
                link_list.append(link)
                if verbose: print(f"{counter}. {link}")
                next_link = next_link = Link.get_next_link(link, max_tries, nested_verbose_1)
                while next_link is not None and next_link not in link_list and next_link not in Link.instances:
                    counter += 1
                    link_list.append(next_link)
                    if verbose: print(f"{counter}. {next_link}")
                    next_link = Link.get_next_link(next_link, max_tries, nested_verbose_1)
                
                if next_link == -1:
                    if verbose: print("F"*50)
                    if verbose: print("CONNECTION ERROR. EXPLORATION FAILED")
                    if verbose: print("F"*50)
                    if verbose: print("dumping path into failed_paths")
                    Link.failed_paths.append(link_list)
                    if verbose: print("skipping iteration")
                    continue
                elif next_link is None:
                    counter
                    if verbose: print("_"*50)
                    if verbose: print(f"NEW DEAD-END LOOP FOUND. EXPLORATION SUCCESSFUL")
                    if verbose: print("_"*50)
                    if verbose: print("adding new dead-end loop to loops")
                    Link.loops.append(link_list[counter:])
                    loop_index = len(Link.loops) - 1
                    if verbose: print("adding path to instances")
                    for j in range(counter):
                        Link.instances[link_list[j]] = {
                            "next_link": link_list[j+1],
                            "loop": -1,
                            "converges_to": loop_index,
                            "distance_from_loop": counter - j
                        }
                    Link.instances[link_list[counter]] = {
                        "next_link": next_link,
                        "loop": loop_index,
                        "converges_to": loop_index,
                        "distance_from_loop": 0
                    }

                elif next_link in Link.instances:
                    if verbose: print(f"{counter+1}. {next_link}")
                    if verbose: print("X"*50)
                    if verbose: print(f"LINK ({counter+1}) ALREADY KNOWN. EXPLORATION SUCCESSFUL")
                    if verbose: print("X"*50)
                    if verbose: print("adding path to instances")
                    known_link = Link.instances[next_link]
                    for j in range(len(link_list)):
                        Link.instances[link_list[j]] = {
                            "next_link": link_list[j+1] if j+1 < len(link_list) else next_link,
                            "loop": -1,
                            "converges_to": known_link["converges_to"],
                            "distance_from_loop": known_link["distance_from_loop"] + len(link_list) - j
                        }
                else:
                    index = link_list.index(next_link)
                    if verbose: print("O"*50)
                    if verbose: print(f"NEW LOOP FOUND FROM ({index}) TO ({counter}). EXPLORATION SUCCESSFUL")
                    if verbose: print("O"*50)
                    if verbose: print("adding new loop to loops")
                    Link.loops.append(link_list[index:])
                    loop_index = len(Link.loops) - 1
                    if verbose: print("adding path to instances")
                    for j in range(index):
                        Link.instances[link_list[j]] = {
                            "next_link": link_list[j+1],
                            "loop": -1,
                            "converges_to": loop_index,
                            "distance_from_loop": index - j
                        }
                    for j in range(index, len(link_list)):
                        Link.instances[link_list[j]] = {
                            "next_link": link_list[j+1] if j+1 < len(link_list) else next_link,
                            "loop": loop_index,
                            "converges_to": loop_index,
                            "distance_from_loop": 0
                        }
            else:
                if verbose: print("link already in instances, skipping iteration")
                continue
            if iterations != -1:        
                if verbose: print("iteration", iteration_count, "of", iterations, "completed successfully")
            else:
                if verbose: print("iteration", iteration_count, "completed successfully")
            iteration_count += 1
            if verbose: print("Saving changes...")
            Link.save()
            if verbose: print("Changes saved successfully\n\n")

    @staticmethod
    def max_distance_link():
        return  max(Link.instances, key=lambda instance: Link.instances[instance]['distance_from_loop'])
    
    def max_distance_instance():
        return Link.instances[Link.max_distance_key()]

    @staticmethod
    def max_size_loop_index():
        return max(Link.loops, key=len)

    @staticmethod
    def max_size_loop():
        return len(Link.max_size_loop_key())
    
    @staticmethod
    def loop_affiliates(loop_index):
        return [instance for instance in Link.instances if Link.instances[instance]['converges_to'] == loop_index and Link.instances[instance]['loop'] == -1]

    @staticmethod    
    def loop_affiliates_count(loop_index):
        return Link.loop_affiliates(loop_index)

    @staticmethod
    def loop_max_distance_instance(loop_index):
        return max(Link.loop_affiliates(loop_index), key=lambda instance: Link.instances[instance]['distance_from_loop'])

    @staticmethod
    def instances_count():
        return len(Link.instances)
    
    @staticmethod
    def loops_count():
        return len(Link.loops)
    
    @staticmethod
    def longest_path_in_loop(loop_index):
        path = []
        next_instance = Link.loop_max_distance_instance(loop_index)
        while Link.instances[next_instance]['loop'] == -1:
            path.append(next_instance)
            next_instance = Link.instances[next_instance]['next_link']
        return path
    
    def loops_ordered_by_size():
        return sorted(Link.loops, key=len, reverse=True)
    
    @staticmethod
    def dead_ends():
        with Link.lock:
            Link.load()
            return [instance for instance in Link.instances if instance['next_link'] == None]
    
    @staticmethod
    def dead_ends_count():
        return len(Link.dead_ends())

Link.load()
Link.link_search(1,verbose_level=1)

# pretty print of the instances in json format
# print(json.dumps(Link.instances, indent=4))
#print(len(Link.instances))

# max_dist = -1
# for instance in Link.instances.keys():
#     if Link.instances[instance]['distance_from_loop'] > max_dist:
#         max_dist = Link.instances[instance]['distance_from_loop']
#         max_distance_instance = instance

# # now print the path followed by the max distance instance
# next_it = max_distance_instance
# while Link.instances[next_it]['loop'] == -1:
#     next_it = Link.instances[next_it]['next_link']
#     print(next_it)


# pretty print of the loops in json format
# print(json.dumps(Link.loops, indent=4))

# pretty print of the failed_paths in json format
# print(json.dumps(Link.failed_paths, indent=4))

# Link.get_next_link('https://en.wikipedia.org/wiki/Continent', verbose=True)



# print(json.dumps(Link.loop_max_distance_instance(0), indent=4))
# print(json.dumps(Link.longest_path_in_loop(0), indent=4))
# print(json.dumps(Link.loops_ordered_by_size()[:10], indent=4))