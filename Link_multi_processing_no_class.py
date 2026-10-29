import pickle
import requests
from bs4 import BeautifulSoup, NavigableString
import multiprocessing
import threading
from concurrent.futures import ThreadPoolExecutor
import time
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


def load(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)


def save(filename, data):
    with open(filename, 'wb') as f:
        pickle.dump(data, f)

# Generate a random Wikipedia  Returns None if it fails to make the HTTP request
def generate_random_wikipedia_link(max_tries=10, verbose=False):
    if verbose: print("generating random Wikipedia link")
    url = 'https://en.wikipedia.org/wiki/Special:Random'
    response = HTTP_request(url, max_tries=max_tries, verbose=verbose)
    if response is None:
        return None
    random_link = response.url
    return random_link

# Return the next link from a Wikipedia page. Returns None if it finds no link following the rules and -1 if it fails to make the HTTP request
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

# Repeteadly generate random Wikipedia links and explore the paths they lead to. Save the results in the instances, loops and failed_paths attributes
def link_search(lock, instances, loops, failed_paths, iterations = -1, max_tries = 10, verbose_level = 0):
    verbose = verbose_level > 0
    nested_verbose_1 = verbose_level > 1
    nested_verbose_2 = verbose_level > 2
    iteration_count = 0
    while True:
        if iterations != -1:
            if verbose: print("iteration", iteration_count, "of", iterations)
            if iteration_count >= iterations:
                if verbose: print("max iterations reached, stopping")
                break
        else:
            if verbose: print("iteration", iteration_count)
        

        if verbose: print("generating random ..")
        link = generate_random_wikipedia_link(max_tries, nested_verbose_2)
        if link is None:
            if verbose: print("failed to generate random link, skipping iteration")
            continue
        if verbose: print("random link generated:", link)


        with lock:
            link_known = link in instances
        if link_known:
            if verbose: print("link already in instances, skipping iteration")
            continue
    
        if verbose: print("link not in instances. Initiating path exploration...")
        if verbose: print("="*23+"PATH"+"="*23)
        link_list = []
        counter = 0
        link_list.append(link)
        if verbose: print(f"{counter}. {link}")


        next_link = get_next_link(link, max_tries, nested_verbose_2)
        known_instance_in_path = False
        while next_link != -1 and not known_instance_in_path and next_link is not None and next_link not in link_list:
            counter += 1
            link_list.append(next_link)
            if verbose: print(f"{counter}. {next_link}")
            next_link = get_next_link(next_link, max_tries, nested_verbose_1)
            lock.acquire()
            known_instance_in_path = all([instance in instances for instance in link_list])
            if not known_instance_in_path:
                lock.release()
        
        if next_link == -1:
            if verbose: print("F"*50)
            if verbose: print("CONNECTION ERROR. EXPLORATION FAILED")
            if verbose: print("F"*50)
            with lock:
                if verbose: print("dumping path into failed_paths...")
                failed_paths.append(link_list)
                if verbose: print("saving changes...")
                save('failed_paths.pkl', list(failed_paths))
            if verbose: print("changes saved successfully, skipping iteration")
            continue
        elif known_instance_in_path:
            counter += 1
            link_list.append(next_link)
            if verbose: print(f"{counter}. {next_link}")

            length = counter + 1
            counter = 0
            while counter < length and link_list[counter] not in instances:
                counter += 1
            next_link = link_list[counter]
            link_list = link_list[:counter]
            counter -= 1
            if verbose: print("X"*50)
            if verbose: print(f"LINK ({counter}) ALREADY KNOWN. EXPLORATION SUCCESSFUL")
            if verbose: print("X"*50)
            with lock:
                if verbose: print("adding path to instances...")
                known_instance = instances[next_link]
                for j in range(len(link_list)):
                    instances[link_list[j]] = {
                        "next_link": link_list[j+1] if j+1 < len(link_list) else next_link,
                        "loop": -1,
                        "converges_to": known_instance["converges_to"],
                        "distance_from_loop": known_instance["distance_from_loop"] + len(link_list) - j
                    }
                if verbose: print("saving changes...")
                save('instances.pkl', dict(instances))
        elif next_link is None:
            if verbose: print("_"*50)
            if verbose: print(f"NEW DEAD-END LOOP FOUND. EXPLORATION SUCCESSFUL")
            if verbose: print("_"*50)
            with lock:
                if verbose: print("adding new dead-end loop to loops...")
                loops.append(link_list[counter:])
                loop_index = len(loops) - 1
                if verbose: print("adding path to instances...")
                for j in range(counter):
                    instances[link_list[j]] = {
                        "next_link": link_list[j+1],
                        "loop": -1,
                        "converges_to": loop_index,
                        "distance_from_loop": counter - j
                    }
                instances[link_list[counter]] = {
                    "next_link": next_link, # None
                    "loop": loop_index,
                    "converges_to": loop_index,
                    "distance_from_loop": 0
                }
                if verbose: print("saving changes...")
                save('instances.pkl', dict(instances))
                save('loops.pkl', list(loops))
        elif next_link in link_list:
            index = link_list.index(next_link)
            if verbose: print("O"*50)
            if verbose: print(f"NEW LOOP FOUND FROM ({index}) TO ({counter}). EXPLORATION SUCCESSFUL")
            if verbose: print("O"*50)
            with lock:
                if verbose: print("adding new loop to loops...")
                loops.append(link_list[index:])
                loop_index = len(loops) - 1
                if verbose: print("adding path to instances...")
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
                if verbose: print("saving changes...")
                save('instances.pkl', dict(instances))
                save('loops.pkl', list(loops))
        if verbose: print("changes saved successfully")
        if iterations != -1:        
            if verbose: print("iteration", iteration_count, "of", iterations, "completed successfully")
        else:
            if verbose: print("iteration", iteration_count, "completed successfully")
        iteration_count += 1        


def link_search_multiprocessing(processes_number, iterations=-1, max_tries=10):
    with multiprocessing.Manager() as manager:
        lock = multiprocessing.RLock()

        instances = manager.dict(load('instances.pkl'))
        loops = manager.list(load('loops.pkl'))
        failed_paths = manager.list(load('failed_paths.pkl'))

        # instances = manager.dict()
        # loops = manager.list()
        # failed_paths = manager.list()

        single_process_iterations = iterations // processes_number
        extra_iteration_processes_count = iterations % processes_number
        
        processes = []
        for i in range(processes_number):
            if i < extra_iteration_processes_count:
                p = multiprocessing.Process(target=link_search, args=(lock, instances, loops, failed_paths, single_process_iterations + 1, max_tries))
            else:
                p = multiprocessing.Process(target=link_search, args=(lock, instances, loops, failed_paths, single_process_iterations, max_tries))
            processes.append(p)

        for p in processes:
            p.start()

        for p in processes:
            p.join()


def link_search_multithreading(threads_number, iterations=-1, max_tries=10):
    lock = threading.RLock()

    instances = load('instances.pkl')
    loops = load('loops.pkl')
    failed_paths = load('failed_paths.pkl')

    single_thread_iterations = iterations // threads_number
    extra_iteration_threads_count = iterations % threads_number

    with ThreadPoolExecutor(max_workers=threads_number) as executor:
        for i in range(threads_number):
            if i < extra_iteration_threads_count:
                executor.submit(link_search, lock, instances, loops, failed_paths, single_thread_iterations + 1, max_tries)
            else:
                executor.submit(link_search, lock, instances, loops, failed_paths, single_thread_iterations, max_tries)


def max_distance_link(instances):
    return max(instances, key=lambda instance: instances[instance]['distance_from_loop'])


def max_distance_instance(instances):
    return max_distance_link(instances)


def max_size_loop_index(loops):
    return max(loops, key=len)


def max_size_loop(loops):
    return len(max_size_loop_index(loops))


def loop_affiliates(instances, loop_index):
    return [instance for instance in instances if instances[instance]['converges_to'] == loop_index and instances[instance]['loop'] == -1]

    
def loop_affiliates_count(instances, loop_index):
    return loop_affiliates(instances, loop_index)


def loop_max_distance_link(instances, loop_index):
    return max(loop_affiliates(instances, loop_index), key=lambda instance: instances[instance]['distance_from_loop'])


def loop_max_distance_instance(instances, loop_index):
    return instances[loop_max_distance_link(instances, loop_index)]


def longest_path_in_loop(instances, loop_index):
    path = []
    next_link = loop_max_distance_link(instances, loop_index)
    while instances[next_link]['loop'] == -1:
        path.append(next_link)
        next_link = instances[next_link]['next_link']
    return path


def loops_ordered_by_size(loops):
    return sorted(loops, key=len, reverse=True)


def dead_ends(instances):
    return [instance for instance in instances if instance['next_link'] == None]


def dead_ends_count():
    return len(dead_ends())


def p_test(n_processes, iterations):
    # calculate the time it takes for different number of processes to explore 1000 iterations
    start = time.time()
    link_search_multiprocessing(n_processes, iterations)
    end = time.time()
    print(f"{n_processes} processes and {iterations} iterations:", end - start)


def t_test(n_threads, iterations):
    # calculate the time it takes for different number of threads to explore iterations
    start = time.time()
    link_search_multithreading(n_threads, iterations)
    end = time.time()
    print(f"{n_threads} threads and {iterations} iterations:", end - start)


if __name__ == '__main__':
    for i in range(6):
        p_test(16-2*i, 64)
        t_test(16-2*i, 64)
