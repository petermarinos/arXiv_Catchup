# Import libraries
from scripts.string_handling import normalise_string
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(prog='Test String Normalisation',
                                 description='Test how the LaTeX/Unicode is normalised to plain ASCII text.')
parser.add_argument('-s', type=str,
                    help='String to normalise.')
args = parser.parse_args()

# Print the ASCII representation of the string passed on the command line
print( normalise_string( args.s ) )