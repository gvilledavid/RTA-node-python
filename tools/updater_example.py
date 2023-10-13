import os, sys, time, multiprocessing, subprocess

os.chdir(os.path.dirname(os.path.realpath(__file__)))
print(os.getcwd())
# the goal of this is to demonstrate how the node can shutdown,
# then call an update process,
# which updates and restarts it

print(f"parent pid: {os.getppid()}")
print(f"self pid: {os.getpid()}")

# in process commands, we first shutdown all leafs
# shutdown mqtt
# then set your own state to stop running on the next runner loop
# then call the /usr/src/RTA/node/node_updater.sh script
# That script tries to kill the running nodemanager if it is up,
# then downloads the update from git, does a setup, then restarts the node manager


with open("pid.file", "w") as p:
    p.write(str(os.getpid()))
os.system("rm updater_example.txt")  # delete the log from updater_example.sh

# run the updater in the background and do not block
p = subprocess.Popen(
    "./updater_example.sh"
)  # or set a flag in /dev/piCOMM/node_updater

# in the real program, wait like 10 seconds for the updater to run,
# otherwise it didnt run and you need to restart
os.system(f'echo "{p.pid}">>upid.file')

while True:
    print("Still running...")
    time.sleep(1)
    pass

# this process will be killed after 5 iterations or so, and the updater_example.txt file should have something in it
