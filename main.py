import sys
import argparse

# Set Argument Parser
args_parser = argparse.ArgumentParser(prog='mgit', description='A hand-made rough but useable git implement')
args_subparser = args_parser.add_subparsers(title='Command', dest='command')
args_subparser.required = True

init_parser = args_subparser.add_parser('init', help='Initialize a new, empty repository')
init_parser.add_argument('path', default='.', help='Where to create the repository')

def main():
    args = args_parser.parse_args()
    # now we can use args.command to get subcommons 

