# SuperFastPython.com
# example of shared list among processes using a manager
from time import sleep
from random import random
from multiprocessing import Process
from multiprocessing import Manager
 
# task executed in a new process
def task(number, shared_list):
    # generate a number between 0 and 1
    value = random()
    # block for a fraction of a second
    sleep(value)
    # store the value in the shared list
    shared_list.append((number, value))
 
# protect the entry point
if __name__ == '__main__':
    # create the manager
    with Manager() as manager:
        # create the shared list
        shared_list = manager.list()
        # create many child processes
        processes = [Process(target=task, args=(i, shared_list)) for i in range(50)]
        # start all processes
        for process in processes:
            process.start()
        # wait for all processes to complete
        for process in processes:
            process.join()
        # report the number of items stored
        print(f'List: {len(shared_list)}')
        # print the list
        print(shared_list)