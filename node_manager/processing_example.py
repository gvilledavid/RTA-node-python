import multiprocessing
import random, time, threading
import queue
from enum import IntEnum


def LeafProcessorCommands(IntEnum):
    START = IntEnum.auto()
    STOP = IntEnum.auto()
    ECHO = IntEnum.auto()


def LeafProcessorStates(IntEnum):
    RUNNING = IntEnum.auto()
    STOPPING = IntEnum.auto()
    STOPPED = IntEnum.auto()
    DEAD = IntEnum.auto()


def LeafProcessor(
    name, parent, node_transmit_queue, leaf_transmit_queue, command_pipe, state_pipe
):
    """
    give multiproccessing queues for the two queues
    give two connection objects from pipe to the pipes.

    send a LeafProcessorCommands enum to indicate a start or stop request.
        (echo will have the LeafProcessor immediately return the stopped state)


    """
    leaf = fake_leaf(name, parent)
    running = True
    stopped = False
    node_desired_run_state = True
    state = LeafProcessorStates.RUNNING
    state_pipe.send(state)
    last_sent_state=state

    while running:
        try:
            if leaf.txQueue.not_empty:
                while leaf.txQueue.not_empty:
                    m = leaf.txQueue.get()
                    leaf_transmit_queue.put(m)
            if not node_transmit_queue.empty():
                while not node_transmit_queue.empty():
                    leaf.rxQueue.put(node_transmit_queue.get())
            if command_pipe.poll():
                comm = command_pipe.recv()
                match comm:
                    case LeafProcessorCommands.ECHO:
                        state_pipe.send(state)
                        last_sent_state=state
                    case LeafProcessorCommands.START:
                        node_desired_run_state = True
                    case LeafProcessorCommands.STOP:
                        node_desired_run_state = False
            if node_desired_run_state and state!=LeafProcessorStates.RUNNING:
                #start
                pass
            elif not node_desired_run_state and state=LeafProcessorStates.RUNNING:
                leaf.loop_stop()
            if state!=last_sent_state:
                state_pipe.send(state)
                last_sent_state=state
                
        except:
            running=False
            try:
                ct = 0
                tMAX = 50
                while not leaf.stopped:
                    ct += 1
                    time.sleep(0.1)
                    if ct > tMAX:
                        break
                    leaf.loop_stop()
            except:
                pass
    state_pipe.send(LeafProcessorStates.DEAD)


class fake_leaf:
    def __init__(self, name, parent):
        self.number = random.random() * 10
        self.name = name
        self.rxQueue = queue.PriorityQueue(maxsize=1000)
        self.txQueue = queue.PriorityQueue(maxsize=1000)
        self.running = False
        self.stopped = True
        self.runner = None
        self.loop_start()

    def loop_start(self):
        if not self.running and self.stopped:
            self.running = True
            self.stopped = False
            self.runner = threading.Thread(target=self.loop_runner, args=())
            self.runner.start()

    def loop_stop(self):
        self.running = False
        ct = 0
        tMAX = 10
        while not self.stopped:
            ct += 1
            time.sleep(0.1)
            if ct > tMAX:
                break

    def loop_runner(self):
        # add flags, exception handling
        lastsend = 0
        while self.running:
            if time.monotonic() > (lastsend + self.number):
                self.txQueue.put(
                    (1, f"{self.name}({self.number}) last: {time.monotonic()-lastsend}")
                )
                lastsend = time.monotonic()
            while self.rxQueue.not_empty():
                self.txQueue.put(
                    (
                        1,
                        f" {self.name} recieved {self.rxQueue.get()} at {time.monotonic()}",
                    )
                )
            time.sleep(0.1)
        self.stopped = True


class fake_node:
    def __init__(self):
        # the goal is to start multiple fake_leafs in processes,
        # send data randomly to the leafs, and read datat that comes back
        with multiprocessing(4) as leafs:
            leafs.map(fake_leaf.__init__, ["bob", "tom", "amy"])
