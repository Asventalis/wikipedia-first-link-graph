import pickle
import requests
from bs4 import BeautifulSoup, NavigableString




##############################################################################################################
###################
# PRINT FUNCTIONS #
###################


def print_iteration_start(iteration_count, iterations):
    if iterations != -1:
        print("ITERATION", iteration_count, "OF", iterations)
    else:
        print("ITERATION", iteration_count)


def print_iteration_end(iteration_count, iterations):
    if iterations != -1:
        print("ITERATION", iteration_count, "OF", iterations, "COMPLETED SUCCESSFULLY\n")
    else:
        print("ITERATION", iteration_count, "COMPLETED SUCCESSFULLY\n")


def evidence_print(surrounding_char, text):
    length = len(text) + 4
    print(surrounding_char*length)
    print(surrounding_char + f" {text} " + surrounding_char)
    print(surrounding_char*length)




##############################################################################################################
##################
# MAIN FUNCTIONS #
##################


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


def get_all_links_not_in_brackets(node, verbose=False, recursive=False, indent=0):
    if verbose: print(" "*indent + "initiating search for links only outside brackets. Going through all children...")
    ignore = False
    counter = 0
    if verbose:
        for child in node.children:
            counter += 1
            child_outerHTML = str(child)
            print(" "*indent + f"{counter}:", child_outerHTML)
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
        elif (not ignore) and recursive:
            control_string = ' and is not ignored: starting recursive search...\n\n'
            print(" "*indent + f"{ignore_string} {counter}: {tag_name} node{control_string}")
            links += get_all_links_not_in_brackets(child, verbose=verbose, recursive=recursive, indent=indent+4)
            continue
        else:
            control_string = ''
        if verbose: print(" "*indent + f"{ignore_string} {counter}: {tag_name} node{control_string}")
    if verbose: print(" "*indent + "search completed. Returning all links found\n\n")
    return links


def load(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)


def save(filename, data):
    with open(filename, 'wb') as f:
        pickle.dump(data, f)


def generate_random_wikipedia_link(max_tries=10, verbose=False):
    if verbose: print("generating random Wikipedia link")
    url = 'https://en.wikipedia.org/wiki/Special:Random'
    response = HTTP_request(url, max_tries=max_tries, verbose=verbose)
    if response is None:
        return None
    random_link = response.url
    return random_link


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


def explore_path(link, instances, max_tries=10, verbose=False):
    path = []
    counter = 0
    path.append(link)
    if verbose: print("PATH")
    if verbose: print(f"{counter}. {link}")
    next_link = get_next_link(link, max_tries, verbose)
    while next_link != -1 and next_link is not None and next_link not in path and next_link not in instances:
        counter += 1
        path.append(next_link)
        if verbose: print(f"{counter}. {next_link}")
        next_link = get_next_link(next_link, max_tries, verbose)
    return path, next_link, counter


def handle_path_insertion(link_list, next_link, counter, instances, loops, failed_paths, verbose):
    if next_link == -1:
        if verbose: print("dumping path into failed_paths")
        failed_paths.append(link_list)
    elif next_link is None:
        if verbose: evidence_print("_", "DEAD-END LOOP FOUND. EXPLORATION SUCCESSFUL")
        if verbose: print("adding new dead-end loop to loops")
        loops.append(link_list[counter:])
        loop_index = len(loops) - 1
        if verbose: print("adding path to instances")
        for j in range(counter):
            instances[link_list[j]] = {
                "next_link": link_list[j+1],
                "loop": -1,
                "converges_to": loop_index,
                "distance_from_loop": counter - j
            }
        instances[link_list[counter]] = {
            "next_link": next_link,
            "loop": loop_index,
            "converges_to": loop_index,
            "distance_from_loop": 0
        }
    elif next_link in instances:
        if verbose: print(f"{counter+1}. {next_link}")
        if verbose: evidence_print("X", f"LINK ({counter+1}) ALREADY KNOWN. EXPLORATION SUCCESSFUL")
        if verbose: print("adding path to instances")
        known_link = instances[next_link]
        for j in range(len(link_list)):
            instances[link_list[j]] = {
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
        loops.append(link_list[index:])
        loop_index = len(loops) - 1
        if verbose: print("adding path to instances")
        for j in range(index):
            instances[link_list[j]] = {
                "next_link": link_list[j+1],
                "loop": -1,
                "converges_to": loop_index,
                "distance_from_loop": index - j
            }
        for j in range(index, len(link_list)):
            instances[link_list[j]] = {
                "next_link": link_list[j+1] if j+1 < len(link_list) else next_link,
                "loop": loop_index,
                "converges_to": loop_index,
                "distance_from_loop": 0
            }


def link_search(instances, loops, failed_paths, iterations = -1, max_tries = 10, verbose_level = 0):
    verbose = verbose_level > 0
    nested_verbose_1 = verbose_level > 1
    nested_verbose_2 = verbose_level > 2
    iteration_count = 0
    while True:
        if iterations != -1 and iteration_count >= iterations:
            if verbose: print("MAX ITERATIONS REACHED. TERMINATING...")
            break
        if verbose: print_iteration_start(iteration_count, iterations)
        if verbose: print("generating random link...")
        link = generate_random_wikipedia_link(max_tries, nested_verbose_2)
        if link is None:
            if verbose: print("failed to generate random link, skipping iteration")
            continue
        if verbose: print("random link generated:", link)
        if link in instances:
            if verbose: print("link already in instances, skipping iteration")
            continue
        if verbose: print("link not in instances. Initiating path exploration...")
        link_list, next_link, counter = explore_path(link, instances, max_tries, nested_verbose_1)
        if next_link == -1:
            if verbose: evidence_print("F", "CONNECTION ERROR. EXPLORATION FAILED")
            handle_path_insertion(link_list, next_link, counter, instances, loops, failed_paths, nested_verbose_2)
            if verbose: print("skipping iteration")
            continue
        if next_link is None:
            if verbose: evidence_print("_", "DEAD-END LOOP FOUND. EXPLORATION SUCCESSFUL")
            handle_path_insertion(link_list, next_link, counter, instances, loops, failed_paths, nested_verbose_2)
        elif next_link in instances:
            if verbose: print(f"{counter+1}. {next_link}")
            if verbose: evidence_print("X", f"LINK ({counter+1}) ALREADY KNOWN. EXPLORATION SUCCESSFUL")
            handle_path_insertion(link_list, next_link, counter, instances, loops, failed_paths, nested_verbose_2)
        else:
            index = link_list.index(next_link)
            if verbose: evidence_print("O", f"NEW LOOP FOUND FROM ({index}) TO ({counter}). EXPLORATION SUCCESSFUL")
            handle_path_insertion(link_list, next_link, counter, instances, loops, failed_paths, nested_verbose_2)
        iteration_count += 1
        if verbose: print("Saving changes...")
        save("instances.pkl", instances)
        save("loops.pkl", loops)
        save("failed_paths.pkl", failed_paths)
        if verbose: print("Changes saved successfully")
        if verbose: print_iteration_end(iteration_count, iterations)




##############################################################################################################
##############
# STATISTICS #
##############


def max_distance_link(instances):
    return  max(instances, key=lambda instance: instances[instance]['distance_from_loop'])


def max_distance_instance(instances):
    return instances[max_distance_link(instances)]


def max_size_loop_index(loops):
    return max(loops, key=len)


def max_size_loop(loops):
    return loops[max_size_loop_index(loops)]


def loop_affiliates(instances, loop_index):
    return [instance for instance in instances if instances[instance]['converges_to'] == loop_index and instances[instance]['loop'] == -1]


def loop_affiliates_count(instances, loop_index):
    return loop_affiliates(instances, loop_index)


def loop_max_distance_instance(instances, loop_index):
    return max(loop_affiliates(instances, loop_index), key=lambda instance: instances[instance]['distance_from_loop'])


def longest_path_in_loop(instances, loop_index):
    path = []
    next_instance = loop_max_distance_instance(instances, loop_index)
    while instances[next_instance]['loop'] == -1:
        path.append(next_instance)
        next_instance = instances[next_instance]['next_link']
    return path


def loops_ordered_by_size(loops):
    return sorted(loops, key=len, reverse=True)


def dead_ends(instances):
    return [instance for instance in instances if instance['next_link'] == None]
