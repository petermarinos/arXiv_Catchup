# Import packages
from scripts.constants import aux_filenames, arxiv_constants
from scripts.output    import read_catchup
from scripts.utils     import logger_setup, clear_catchup

import argparse
import os

# Find the directory of this file
cdir = os.path.dirname(os.path.realpath(__file__))

# Parse command-line arguments
parser = argparse.ArgumentParser(prog='Catchup file opening',
                                 description='Opens all links in the catchup text file, then clears it.')
parser.add_argument('-v', '--verbosity', type=int, default=3,
                    help='Set the verbosity level.\n0 => critical errors\n1 => ... and non-critical errors\n2 => ... and warnings\n3 => ... and info\n4 => ... and debug messages')
args = parser.parse_args()

# Extract some of the required constants
prevsearch, searchterms, paperlinks = aux_filenames(cdir)
url, ns, sleep_opening, sleep_search, search_blocksize = arxiv_constants()

# Setup logging
logger = logger_setup(args)

# Read the catchup file
papers = read_catchup(paperlinks, sleep_opening, logger)

# Ask the user if the file should be cleared
clear_catchup(paperlinks, papers, logger)