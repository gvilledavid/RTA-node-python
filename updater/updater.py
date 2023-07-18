from parsers.parser1.parser1 import parser1 as P1
from parsers.parser2.parser2 import parser2 as P2
import importlib
import sys

if __name__ == "__main__":
    p1 = P1()
    p2 = P2()
    p1data = []
    p2data = []
    try:
        with open(p1.file, "r") as f:
            for line in f:
                if "VER" in line[0:4]:
                    ver = int(line.replace("\n", "").split("=")[1]) + 1
                    line = f"VER = {ver}\n"
                p1data.append(line)
    except:
        pass
    try:
        with open(p2.file, "r") as f:
            for line in f:
                if "VER" in line[0:4]:
                    ver = int(line.replace("\n", "").split("=")[1]) + 1
                    line = f"VER = {ver}\n"
                p2data.append(line)
    except:
        pass

    with open(p1.file, "w") as f:
        for line in p1data:
            f.write(line)
    with open(p2.file, "w") as f:
        for line in p2data:
            f.write(line)
    importlib.reload(sys.modules["parsers.parser1.parser1"])
    importlib.reload(sys.modules["parsers.parser2.parser2"])

    p3 = P1()
    p4 = P2()
