# Import packages
from scripts.constants import set_filenames, set_arxiv_constants
from scripts.file_io   import read_catchup
from scripts.utils     import logger_setup, delete_catchup

import argparse
import os

# The goal of this script is to save the link opening for later if the user chooses
# However, it can also be used to automate the searches.

# Set up a cron job to run `/path/tp/arXiv_Catchup/catchup.py -w` daily.
# Then, when ready to open all the saved papers, run this script.

# While functionally equivalent to just running `/path/tp/arXiv_Catchup/catchup.py` whenever you want to open the papers, this method can offload the search times (3s per ten papers) to the cron job where there is no impact to you.
# The only impact to you would be the 0.25s per filtered paper opened in the browser.
# If you rarely want to open all papers, this is the recommended method.

# Find the directory of this file
cdir = os.path.dirname(os.path.realpath(__file__))

# Parse command-line arguments
parser = argparse.ArgumentParser(prog='Catchup file opening',
                                 description='Opens all links in the catchup text file, then clears it.')
parser.add_argument('-v', '--verbosity', type=int, default=3,
                    help='Set the verbosity level.\n0 => critical errors\n1 => ... and non-critical errors\n2 => ... and warnings\n3 => ... and info\n4 => ... and debug messages')
args = parser.parse_args()

# Extract some of the required constants
prevsearch, searchterms, paperlinks = set_filenames(cdir)
url, ns, sleep_opening, sleep_search, search_blocksize = set_arxiv_constants()

# Setup logging
logger = logger_setup(args)

# Read the catchup file
papers = read_catchup(paperlinks, sleep_opening, logger)

# Ask the user if the file should be deleted
delete_catchup(paperlinks, papers, logger)