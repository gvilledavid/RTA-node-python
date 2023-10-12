import os, sys

sys_parser = "parsers.parser.V60"
directory = os.path.dirname(os.path.realpath(__file__))
sys.path.append(directory)
# append other package folders that need to be inserted:
# sys.path.append(os.path.join(directory, "IntellivueProtocol"))
