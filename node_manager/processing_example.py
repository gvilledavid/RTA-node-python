import multiprocessing
import random, time, threading
import queue
from enum import IntEnum, auto
import sys, os
import curses
import tty, termios
import select

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path

# from leaf_managers.leaf_manager import UARTLeafManager
# from tools.MQTT import Message, get_mac


class LeafProcessorCommands(IntEnum):
    START = auto()
    STOP = auto()
    TERM = auto()
    ECHO = auto()


class LeafProcessorStates(IntEnum):
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    DEAD = auto()


# todo, integrate this interface to the UARTLeafManager instead?
# we need to rework
class LeafProcessor:
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self.context = multiprocessing.get_context("spawn")
        self.node_transmit_queue = self.context.Queue()
        self.leaf_transmit_queue = self.context.Queue()
        self.command_state_pipe_node, self.command_state_pipe_leaf = self.context.Pipe()
        self.last_state = LeafProcessorStates.STOPPED
        self.processor = self.context.Process(
            target=LeafProcessorRunner,
            args=(
                self.name,
                self.parent,
                self.node_transmit_queue,
                self.leaf_transmit_queue,
                self.command_state_pipe_leaf,
            ),
        )
        time.sleep(1)
        self.processor.start()
        time.sleep(1)
        self.pid = self.processor.pid
        print(self.pid)

    def transmit(self, message_tuple):
        if not self.node_transmit_queue.full():
            try:
                self.node_transmit_queue.put_nowait(message_tuple)
            except queue.Full:
                return False
            return True
        else:
            return False

    def recieve(self):
        if not self.leaf_transmit_queue.empty():
            try:
                return self.leaf_transmit_queue.get()
            except queue.Empty:
                pass
        else:
            return None

    def full(self):
        return self.node_transmit_queue.full()

    def empty(self):
        return self.leaf_transmit_queue.empty()

    def recQsize(self):
        return self.leaf_transmit_queue.qsize()

    def transQsize(self):
        return self.node_transmit_queue.qsize()

    def start(self):
        try:
            self.command_state_pipe_node.send(LeafProcessorCommands.START)
        except ValueError:
            pass
            # object not  picklable
        # except full?

    def stop(self):
        self.command_state_pipe_node.send(LeafProcessorCommands.STOP)

    def state(self):
        if self.command_state_pipe_node.poll(0.01):
            while self.command_state_pipe_node.poll(0.01):
                try:
                    state = self.command_state_pipe_node.recv()  # empty pipe
                    self.last_state = state
                except EOFError:
                    pass  # no more data
                return state
        else:
            self.command_state_pipe_node.send(LeafProcessorCommands.ECHO)
            return self.last_state

    def echo(self):
        self.command_state_pipe_node.send(LeafProcessorCommands.ECHO)

    def join(self, timeout=None):
        t = time.monotonic()
        self.command_state_pipe_node.send(LeafProcessorCommands.TERM)
        if timeout:
            st = time.monotonic()
            timeout = st + timeout
        while True:
            if self.state() == LeafProcessorStates.DEAD:
                break
            if timeout and (time.monotonic() > timeout):
                break
            time.sleep(0.1)
        self.processor.join(0.1)
        print(f"{self.name}.join() Executed {time.monotonic()-t} seconds")
        return self.processor.is_alive()


def LeafProcessorRunner(
    name, parent, node_transmit_queue, leaf_transmit_queue, leaf_pipe
):
    leaf = fake_leaf(name, parent)
    running = True
    stopped = False
    node_desired_run_state = True
    state = LeafProcessorStates.RUNNING
    leaf_pipe.send(state)
    last_sent_state = state
    while running:
        try:
            # check leaf messages and relay to node
            if not leaf.txQueue.empty():
                while not leaf.txQueue.empty():
                    m = leaf.txQueue.get()  # todo, catch queue exceptions
                    leaf_transmit_queue.put(m)
            # check node messages and relay to leaf
            if not node_transmit_queue.empty():
                while not node_transmit_queue.empty():
                    leaf.rxQueue.put(node_transmit_queue.get())
            # check for node commands
            if leaf_pipe.poll(0.01):
                comm = leaf_pipe.recv()
                match comm:
                    case LeafProcessorCommands.ECHO:
                        leaf_pipe.send(state)
                        last_sent_state = state
                    case LeafProcessorCommands.START:
                        node_desired_run_state = True
                    case LeafProcessorCommands.STOP:
                        node_desired_run_state = False
                    case LeafProcessorCommands.TERM:
                        running = False
                        node_desired_run_state = False
                        leaf.loop_stop()
                        leaf_transmit_queue.put((1, "Accepted term command"))
            # check if leaf needs to be started or stopped
            if node_desired_run_state and state != LeafProcessorStates.RUNNING:
                leaf.loop_start()
                leaf_transmit_queue.put((1, "Accepted start command"))
            elif not node_desired_run_state and state == LeafProcessorStates.RUNNING:
                leaf.loop_stop()
                leaf_transmit_queue.put((1, "Accepted stop command"))
            # update leaf state
            if leaf.running:
                state = LeafProcessorStates.RUNNING
            elif not leaf.running and not leaf.stopped:
                state = LeafProcessorStates.STOPPING
            elif not leaf.running and leaf.stopped:
                state = LeafProcessorStates.STOPPED
            # send state on changes
            if state != last_sent_state:
                leaf_pipe.send(state)
                last_sent_state = state
                leaf_transmit_queue.put((1, f"updated state to {state}"))

        except Exception as e:
            running = False
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
    leaf_pipe.send(LeafProcessorStates.DEAD)


class fake_leaf:
    def __init__(self, name, parent):
        self.number = random.random() * 5
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
                try:
                    self.txQueue.put_nowait(
                        (
                            1,
                            f"{self.name}({self.number}) last: {time.monotonic()-lastsend}",
                        )
                    )
                    lastsend = time.monotonic()
                except queue.Full:
                    pass
            while not self.rxQueue.empty():
                try:
                    self.txQueue.put_nowait(
                        (
                            1,
                            f" {self.name} recieved {self.rxQueue.get_nowait()} at {time.monotonic()}",
                        )
                    )
                except queue.Full:
                    pass
                except queue.Empty:
                    pass
            time.sleep(0.1)
        self.stopped = True


def pressed_key():
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin)
    try:
        while True:
            time.sleep(1)
            if select.select(
                [
                    sys.stdin,
                ],
                [],
                [],
                0,
            )[0]:
                b = os.read(sys.stdin.fileno(), 1).decode()
            else:
                return ""
            if len(b) == 3:
                k = ord(b[2])
            else:
                k = ord(b)
            key_mapping = {
                127: "backspace",
                10: "return",
                32: "space",
                9: "tab",
                27: "esc",
                65: "up",
                66: "down",
                67: "right",
                68: "left",
            }
            print(key_mapping.get(k, chr(k)))
            # termios.tcflush(sys.stdin, termios.TCIOFLUSH)
            return key_mapping.get(k, chr(k))
        return ""
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


if __name__ == "__main__":
    # in init
    # the goal is to start multiple fake_leafs in processes,
    # send data randomly to the leafs, and read data that comes back

    leaf = LeafProcessor("ttyAMA1", "123")
    last_state = leaf.state()

    """poll:
        if leaf is dead:
            start it
        if leaf is not running 
            start it
        if leaf.something.txqueue
            send to mqtt  
        if command from mqtt
            leaf.somthign.rxqueue.put()
    """
    # do we need to get the command topic from the leaf or should we assume it?
    try:
        while True:
            while leaf.recQsize():
                m = leaf.recieve()
                if m:
                    print(m)
            if last_state == LeafProcessorStates.DEAD:
                print("Detected dead leaf and no more messages in queues.")
                break
            s = leaf.state()
            if s != last_state:
                last_state = s
                print(f"State changed on {leaf.name} to {s}")
            time.sleep(0.25)

            match pressed_key().lower():
                case "":
                    pass
                case "t":
                    # transmit
                    t = time.monotonic()
                    print(f"Sending {t} to {leaf.name}")
                    leaf.transmit((1, t))
                case "s":
                    print(f"sending start command to {leaf.name}")
                    leaf.start()
                case "p":
                    print(f"sending stop command to {leaf.name}")
                    leaf.stop()
                case "e":
                    print(f"sending echo command to {leaf.name}")
                    leaf.echo()
                case "j":
                    print(f"sending join command to {leaf.name}")
                    leaf.join()
                case _:
                    print("Commands *H*elp, *T*ransmit, *S*tart, sto*P*, *E*cho, *J*oin")

    except Exception as e:
        leaf.stop()
        if leaf.join(10):
            print(f"Succeeded in stopping {leaf.name}")

        # os.system("stty sane")
    # __del__ implementation:
    # for p in self.leafs:
    # leafs.something.command_pipe.send(LeafProcessorCommands.STOP)
