from parsers.parser1.parser1 import parser1 as P1
from parsers.parser2.parser2 import parser2 as P2
import importlib
import sys
import hashlib


class update_parser:
    # usage:
    # x=update_parser()
    # reqs=x.make_update_packets("path/parser.py",dest_uid,src_uid)
    # request reqs count ids from source with req_id command with parameter reqs
    # that command should return some start_req_id
    # x.write_req_id(start_req_id)
    # now x.packets is x.len count packets you can send
    # or as a reader
    # x=update_parser()
    # x.read_update_packets(packets)

    def __init__(self):
        pass

    def __del__(self):
        pass

    def write_req_id(self, start):
        if self.len == 0:
            return
        for p in self.packets:
            p["req_id"] = int(p["req_id"]) + start - 1

    def make_update_packets(file_location, dest_uid, source_uid):
        sample_packet = {
            "UID": dest_uid,
            "timestamp": 0,
            "requester": source_uid,
            "command": "update_parser",
            "parameters": [],
            "req_id": 0,
        }
        # parameters(new_file_part, sha256, partx, ofn, filename, classname)
        return_packets = []
        partx = 1
        ofn = 1
        part = ""
        length = 0
        MAX_LENGTH = 128000  # AWS Iot core allows 128kb max payload
        with open(file_location, "r") as f:
            lineb = bytes(line, "utf-8")
            newlength = length + len(lineb)
            if line == b"":
                # end of file
                pass
            elif newlength > MAX_LENGTH:
                pass

            else:
                part += lineb
                length = newlength

    def read_update_packets(packets):
        return


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
    p1hasher = hashlib.sha256()
    p1hasher.update(bytes("".join(p1data), "utf-8"))
    p1hash = p1hasher.hexdigest()
    p2hasher = hashlib.sha256()
    p2hasher.update(bytes("".join(p2data), "utf-8"))
    p2hash = p2hasher.hexdigest()
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

    # verify hash:
    with open(p3.file) as f:
        p3hasher = hashlib.sha256()
        p3hasher.update(bytes(f.read(), "utf-8"))
        p3hash = p3hasher.hexdigest()
    with open(p4.file) as f:
        p4hasher = hashlib.sha256()
        p4hasher.update(bytes(f.read(), "utf-8"))
        p4hash = p4hasher.hexdigest()
    print(f"{p1hash=}")
    print(f"{p2hash=}")
    print(f"{p3hash=}")
    print(f"{p4hash=}")
    if p3hash == p1hash:
        print("p3 matches")
    if p4hash == p2hash:
        print("p4 matches")
