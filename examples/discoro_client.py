# Run 'discoro.py' (server for getting computations from clients and
# running them as coroutines) with this program

# Example where this client sends computation to remote discoro server
# to run that computation as remote coroutine. Remote coroutines and
# client can use message passing to exchange data.

import sys, logging, random
if sys.version_info.major >= 3:
    import disasyncoro3 as asyncoro
else:
    import disasyncoro as asyncoro

import discoro

# objects of C are exchanged between client and servers
class C(object):
    def __init__(self, i):
        self.i = i
        self.n = None

    def __repr__(self):
        return '%d: %.3f' % (self.i, self.n)

# this generator function is sent to remote discoro servers to run
# coroutines there
def compute(obj, client, coro=None):
    # obj is an instance of C
    import math
    # this coroutine and client can use message passing;
    # get data from client
    n = yield coro.receive()
    obj.n = math.sqrt(n)
    yield coro.sleep(obj.n)
    # send result back to client
    yield client.deliver(obj, timeout=3)

def heartbeat(peer, interval=5, coro=None):
    # check heartbeat of peer
    coro.set_daemon()
    no_pulse = 0
    while True:
        yield coro.sleep(interval)
        if (yield peer.deliver({'cmd':'ping', 'coro':coro}, timeout=3)) == 1:
            no_pulse = 0
        else:
            no_pulse += interval
            if no_pulse > (5 * interval):
                asyncoro.logger.warning('peer %s is not responding' % peer)

def client_proc(computation, location, coro=None):
    server = yield asyncoro.Coro.locate('discoro_server', location, timeout=2)
    if not server:
        raise Exception('server not found at %s' % location)
    # if lot of messages are sent to server, it may be efficient to
    # stream messages; similarly, if lot of data is sent back, the
    # function 'compute' can set the streaming to this client
    yield scheduler.peer(location.addr, tcp_port=location.port, stream_send=True)

    # distribute computation to server
    if (yield computation.setup(server, timeout=3)):
        raise Exception('setup on %s failed' % location)
    hb_coro = asyncoro.Coro(heartbeat, server)
    # create n coroutines at server with this computation; if the
    # computations are CPU intensive, running more than one coroutine
    # on a server at the same time is not advisable
    n = 2
    for i in range(n):
        obj = C(i) # create object of C
        rcoro = yield computation.run(server, obj, coro)
        r = random.uniform(10, 100) # send data to remote coro
        print('%s: %d, %.3f' % (location, i, r))
        rcoro.send(r)
    for i in range(n): # get results from remote coros
        # result is instance of C
        result = yield coro.receive()
        print('%s: %d, result = %s' % (location, i, result))
    yield computation.close(server)
    hb_coro.terminate()
    # disable streaming; otherwise, peer remains connected preventing
    # it from automatically terminating even after all coroutines
    # terminated
    yield scheduler.peer(location.addr, tcp_port=location.port, stream_send=False)
    print('server %s is done' % location)

def peer_status(name, location, status):
    # this function is called when peer is discovered (status=1) or
    # when peer terminates (status=0)
    print('peer "%s" @ %s status: %s' % (name, location, status))
    if status: # peer came online
        asyncoro.Coro(client_proc, computation, location)
    else: # peer terminated
        # if any pending processes, send them to other peers?
        pass

if __name__ == '__main__':
    asyncoro.logger.setLevel(logging.DEBUG)
    scheduler = asyncoro.AsynCoro.instance(name='client')
    # send generator function and class C (as the function uses
    # objects of C); 'depends' can include files, functions, objets
    computation = discoro.Computation(compute, depends=[C])
    scheduler.peer_status(peer_status) # register peer status callback
    while True:
        try:
            cmd = sys.stdin.readline().strip().lower()
            if cmd == 'quit' or cmd == 'exit':
                break
        except KeyboardInterrupt:
            break
