import copy
from bs4 import BeautifulSoup, NavigableString


# this version appends all a nodes in a div and returns the div
def get_all_links_not_in_brackets(p, verbose=False):
    soup = BeautifulSoup("<html></html>", "html.parser") 
    new_div = soup.new_tag('div')
    if verbose: print("initiating search for links only outside brackets. Going through all children...")
    ignore = False
    counter = 0
    if verbose:
        for child in p.children:
            counter += 1
            child_outerHTML = str(child)
            print(f"{counter}:", child_outerHTML)
    counter = 0
    nested_count = 0
    for child in p.children:
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
        elif child.name == 'a' and not ignore:
            new_div.append(copy.deepcopy(child))
            control_string = ' and is not ignored: <a> node added'
        else:
            control_string = ''
        if verbose: print(f"{ignore_string} {counter}: {tag_name} node{control_string}")
    if verbose: print("search completed. Returning all links found")
    return new_div

# this version returns a list of all href of the a nodes found
def get_all_links_not_in_brackets(p, verbose=False):
    if verbose: print("initiating search for links only outside brackets. Going through all children...")
    ignore = False
    counter = 0
    if verbose:
        for child in p.children:
            counter += 1
            child_outerHTML = str(child)
            print(f"{counter}:", child_outerHTML)
    counter = 0
    nested_count = 0
    links = []
    for child in p.children:
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
        elif child.name == 'a' and not ignore:
            links.append(child['href'])
            control_string = f' and is not ignored: link {child['href']} added'
        else:
            control_string = ''
        if verbose: print(f"{ignore_string} {counter}: {tag_name} node{control_string}")
    if verbose: print("search completed. Returning all links found")
    return links