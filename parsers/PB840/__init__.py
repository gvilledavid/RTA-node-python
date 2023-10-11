import os, sys

sys_parser = "parsers.parser.PB840"
directory = os.path.dirname(os.path.realpath(__file__))
sys.path.append(directory)
# append other package folders that need to be inserted:
# sys.path.append(os.path.join(directory, "IntellivueProtocol"))
