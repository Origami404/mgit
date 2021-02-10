import sys
import argparse

# Set Argument Parser
args_parser = argparse.ArgumentParser(description="My Git")
args_subparser = args_parser.add_subparsers(title="Command", dest="command")
args_subparser.required = True

def main(argv=sys.argv[1:]):
    args = args_parser.parse_args()
    
    # now we can use args.command to get subcommons 

