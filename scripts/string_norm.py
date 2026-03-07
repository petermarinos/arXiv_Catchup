"""Small script to test how the function `normalise_string()` alters the string.

CLI Arguments
-------------
-s: str -> string to test
"""

# Import standard libraries
import argparse

# Import functions
from arxiv_catchup.string_handling import normalise_string

# Parse command-line arguments
parser = argparse.ArgumentParser(
    prog="Test String Normalisation",
    description="Test how the LaTeX/Unicode is normalised to plain ASCII text.",
)
parser.add_argument("-s", type=str, help="String to normalise.")
args = parser.parse_args()

# Print the ASCII representation of the string passed on the command line
print(normalise_string(args.s))
