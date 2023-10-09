import os,sys

sys_parser = "parsers.parser.intellie"
directory = os.path.dirname(os.path.realpath(__file__))
sys.path.append(directory)
sys.path.append(os.path.join(directory,"IntellivueProtocol"))