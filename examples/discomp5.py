# Run 'discoronode.py' program to start processes to execute
# computations sent by this client, along with this program.

# Distributed computing example where this client sends computation to
# remote discoro process to run as remote coroutines. At any time at
# most one computation coroutine is scheduled at a process (due to
# ProcScheduler). This example shows how to use 'execute' method of
# ProcScheduler / NodeScheduler to submit comutations and get their
# results easily.

# This example can be combined with in-memory processing (see
# 'discoro_client5.py') and streaming (see 'discoro_client6.py') for
# efficient processing of data and communication.

import logging, random
import asyncoro.discoro as discoro
import asyncoro.disasyncoro as asyncoro
from asyncoro.discoro_schedulers import ProcScheduler


# this generator function is sent to remote discoro servers to run
# coroutines there
def compute(n, coro=None):
    import time
    yield coro.sleep(n)
    raise StopIteration(time.asctime()) # result of 'compute' is current time


def client_proc(computation, n, coro=None):

    def exec_proc(n, coro=None):
        # execute computation; result of computation is result of
        # 'yield' which is also result of this coroutine (obtained
        # with 'finish' method below)
        yield job_scheduler.execute(compute, n)
        # results can be processed here (as they become available), or
        # in-line as done below

    # Use ProcScheduler to run at most one coroutine at a server process
    # This should be created before scheduling computation
    job_scheduler = ProcScheduler(computation)

    if (yield computation.schedule()):
        raise Exception('schedule failed')

    # execute n jobs (coroutines) and get their results. Note that
    # number of jobs created can be more than number of server
    # processes available; the scheduler will use as many processes as
    # necessary, running one job at a server process
    jobs = [asyncoro.Coro(exec_proc, random.uniform(3, 10)) for _ in range(n)]
    for job in jobs:
        print('result: %s' % (yield job.finish()))

    yield job_scheduler.finish(close=True)


if __name__ == '__main__':
    import sys
    asyncoro.logger.setLevel(logging.DEBUG)
    n = 10 if len(sys.argv) == 1 else int(sys.argv[1])
    # if scheduler is not already running (on a node as a program),
    # start private scheduler:
    discoro.Scheduler()
    # send 'compute' generator function; 'depends' can include files, functions, objets
    computation = discoro.Computation([compute])
    asyncoro.Coro(client_proc, computation, n).value()