import pickle
import requests
from bs4 import BeautifulSoup, NavigableString
from multiprocessing import RLock, Process, Manager, freeze_support
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


class Link:
    manager = None
    known_instances = None
    loops = None
    failed_paths = None

    @staticmethod
    def save(lock=RLock(), instances_file = 'instances.pkl', loops_file = 'loops.pkl', failed_paths_file = 'failed_paths.pkl'):
        with lock:
            with open(instances_file, 'wb') as f:
                pickle.dump(Link.known_instances, f)
            with open(loops_file, 'wb') as f:
                pickle.dump(Link.loops, f)
            with open(failed_paths_file, 'wb') as f:
                pickle.dump(Link.failed_paths, f)

    @staticmethod
    def load(lock=RLock(), instances_file = 'instances.pkl', loops_file = 'loops.pkl', failed_paths_file = 'failed_paths.pkl'):
        with lock:
            with open(instances_file, 'rb') as f:
                Link.known_instances = pickle.load(f)
            with open(loops_file, 'rb') as f:
                Link.loops = pickle.load(f)
            with open(failed_paths_file, 'rb') as f:
                Link.failed_paths = pickle.load(f)
    
    @staticmethod
    def initialize():
        Link.manager = Manager()
        Link.known_instances = Link.manager.dict()
        Link.loops = Link.manager.list()
        Link.failed_paths = Link.manager.list()
        Link.load()

    # Generate a random Wikipedia link. Returns None if it fails to make the HTTP request
    @staticmethod
    def generate_random_wikipedia_link(max_tries=10, verbose=False):
        if verbose: print("generating random Wikipedia link")
        url = 'https://en.wikipedia.org/wiki/Special:Random'
        response = HTTP_request(url, max_tries=max_tries, verbose=verbose)
        if response is None:
            return None
        random_link = response.url
        return random_link

    # Return the next link from a Wikipedia page. Returns None if it finds no link following the rules and -1 if it fails to make the HTTP request
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
            
            if ':' in link.split('/wiki/')[1]:
                special_word = link.split('/wiki/')[1].split(':')[0]
                if verbose: print(f"link {link} contains :{special_word}, skipping")
                continue
            elif 'cite_note' in link:
                if verbose: print(f"link {link} is a cite note, skipping")
                continue
            elif  not link.startswith('https://en.wikipedia.org/'):
                if verbose: print(f"link {link} is not in the Wikipedia domain, skipping")
                continue
            else:
                if verbose: print("next link found:", link)
                return link
        if verbose: print("no valid link found inside the page")
        return None

    # Repeteadly generate random Wikipedia links and explore the paths they lead to. Save the results in the instances, loops and failed_paths attributes
    @staticmethod
    def link_search(lock, iterations = -1, max_tries = 10, verbose_level = 0):
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
            if verbose: print("generating random link...")
            link = Link.generate_random_wikipedia_link(max_tries, nested_verbose_2)
            if link is None:
                if verbose: print("failed to generate random link, skipping iteration")
                continue
            if verbose: print("random link generated:", link)
            with lock:
                link_not_known = link not in Link.known_instances
            if link_not_known:
                if verbose: print("link not in instances. Initiating path exploration...")
                if verbose: print("="*23+"PATH"+"="*23)
                link_list = []
                counter = 0
                link_list.append(link)
                if verbose: print(f"{counter}. {link}")
                next_link = next_link = Link.get_next_link(link, max_tries, nested_verbose_2)
                known_instance_in_path = False
                while next_link != -1 and next_link is not None and next_link not in link_list and not known_instance_in_path:
                    counter += 1
                    link_list.append(next_link)
                    if verbose: print(f"{counter}. {next_link}")
                    next_link = Link.get_next_link(next_link, max_tries, nested_verbose_1)
                    with lock:
                        known_instance_in_path = all([instance in Link.known_instances for instance in link_list])
                lock.acquire() # acquire the lock before adding new elements to instances, loops or failed_paths and saving the changes
                if next_link == -1:
                    if verbose: print("F"*50)
                    if verbose: print("CONNECTION ERROR. EXPLORATION FAILED")
                    if verbose: print("F"*50)
                    if verbose: print("dumping path into failed_paths...")
                    Link.failed_paths.append(link_list)
                    Link.save(lock)
                    lock.release() # release the lock after adding the failed path to failed_paths and saving the changes
                    if verbose: print("changes saved successfully, skipping iteration")
                    continue
                if next_link is None:
                    if verbose: print("_"*50)
                    if verbose: print(f"NEW DEAD-END LOOP FOUND. EXPLORATION SUCCESSFUL")
                    if verbose: print("_"*50)
                    if verbose: print("adding new dead-end loop to loops...")
                    Link.loops.append(link_list[counter:])
                    loop_index = len(Link.loops) - 1
                    if verbose: print("adding path to instances...")
                    for j in range(counter):
                        Link.known_instances[link_list[j]] = {
                            "next_link": link_list[j+1],
                            "loop": -1,
                            "converges_to": loop_index,
                            "distance_from_loop": counter - j
                        }
                    Link.known_instances[link_list[counter]] = {
                        "next_link": next_link, # None
                        "loop": loop_index,
                        "converges_to": loop_index,
                        "distance_from_loop": 0
                    }
                elif next_link in Link.known_instances:
                    if verbose: print(f"{counter+1}. {next_link}")
                    if verbose: print("X"*50)
                    if verbose: print(f"LINK ({counter+1}) ALREADY KNOWN. EXPLORATION SUCCESSFUL")
                    if verbose: print("X"*50)
                    if verbose: print("adding path to instances...")
                    known_link = Link.known_instances[next_link]
                    for j in range(len(link_list)):
                        Link.known_instances[link_list[j]] = {
                            "next_link": link_list[j+1] if j+1 < len(link_list) else next_link,
                            "loop": -1,
                            "converges_to": known_link["converges_to"],
                            "distance_from_loop": known_link["distance_from_loop"] + len(link_list) - j
                        }
                elif next_link in link_list:
                    index = link_list.index(next_link)
                    if verbose: print("O"*50)
                    if verbose: print(f"NEW LOOP FOUND FROM ({index}) TO ({counter}). EXPLORATION SUCCESSFUL")
                    if verbose: print("O"*50)
                    if verbose: print("adding new loop to loops...")
                    Link.loops.append(link_list[index:])
                    loop_index = len(Link.loops) - 1
                    if verbose: print("adding path to instances...")
                    for j in range(index):
                        Link.known_instances[link_list[j]] = {
                            "next_link": link_list[j+1],
                            "loop": -1,
                            "converges_to": loop_index,
                            "distance_from_loop": index - j
                        }
                    for j in range(index, len(link_list)):
                        Link.known_instances[link_list[j]] = {
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
            if verbose: print("saving changes...")
            Link.save(lock)
            lock.release() # release the lock after adding new elements to instances and/or loops and saving the changes
            if verbose: print("changes saved successfully")

    @staticmethod
    def link_search_multi(processes_number, iterations=-1, max_tries=10):
        processes = []
        single_process_iterations = iterations // processes_number
        extra_iteration_processes_count = iterations % processes_number
        lock = RLock()
        for i in range(processes_number):
            if i < extra_iteration_processes_count:
                p = Process(target=Link.link_search, args=(lock, single_process_iterations + 1, max_tries))
            else:
                p = Process(target=Link.link_search, args=(lock, single_process_iterations, max_tries))
            processes.append(p)

        for p in processes:
            p.start()

        for p in processes:
            p.join()

    @staticmethod
    def max_distance_link():
        with Link.lock:
            return max(Link.known_instances, key=lambda instance: Link.known_instances[instance]['distance_from_loop'])

    def max_distance_instance():
        return Link.max_distance_link()

    @staticmethod
    def max_size_loop_index():
        with Link.lock:
            return max(Link.loops, key=len)

    @staticmethod
    def max_size_loop():
        return len(Link.max_size_loop_index())

    @staticmethod
    def loop_affiliates(loop_index):
        with Link.lock:
            return [instance for instance in Link.known_instances if Link.known_instances[instance]['converges_to'] == loop_index and Link.known_instances[instance]['loop'] == -1]

    @staticmethod    
    def loop_affiliates_count(loop_index):
        return Link.loop_affiliates(loop_index)

    @staticmethod
    def loop_max_distance_instance(loop_index):
        return max(Link.loop_affiliates(loop_index), key=lambda instance: Link.known_instances[instance]['distance_from_loop'])

    @staticmethod
    def instances_count():
        with Link.lock:
            return len(Link.known_instances)

    @staticmethod
    def loops_count():
        with Link.lock:
            return len(Link.loops)

    @staticmethod
    def longest_path_in_loop(loop_index):
        with Link.lock:
            path = []
            next_instance = Link.loop_max_distance_instance(loop_index)
            while Link.known_instances[next_instance]['loop'] == -1:
                path.append(next_instance)
                next_instance = Link.known_instances[next_instance]['next_link']
            return path

    @staticmethod
    def loops_ordered_by_size():
        with Link.lock:
            return sorted(Link.loops, key=len, reverse=True)

    @staticmethod
    def dead_ends():
        with Link.lock:
            return [instance for instance in Link.instances if instance['next_link'] == None]

    @staticmethod
    def dead_ends_count():
        return len(Link.dead_ends())


def test():
    # calculate the time it takes for different number of processes to explore 1000 iterations
    start = time.time()
    Link.link_search_multi(4, 20)
    end = time.time()
    print("4 processes:", end - start)

    start = time.time()
    Link.link_search_multi(8, 20)
    end = time.time()
    print("16 processes:", end - start)


if __name__ == '__main__':
    freeze_support()
    Link.initialize()
    test()
