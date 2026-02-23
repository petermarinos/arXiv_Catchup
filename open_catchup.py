"""Script that will run through the auxiliary file and open all links contained within.

CLI Arguments
-------------
-v: int -> verbosity level
"""

# fmt: off
# Import standard libraries
import argparse
import pathlib

# Import classes
from scripts.config import Paths

# Import packages
from scripts.file_io import read_catchup
from scripts.utils   import logger_setup, delete_catchup
# fmt: on

# The goal of this script is to save the link opening for later if the user chooses
# However, it can also be used to automate the searches.

# Set up a cron job to run `/path/tp/arXiv_Catchup/catchup.py -w` daily.
# Then, when ready to open all the saved papers, run this script.

# This script is functionally equivalent to running `/path/tp/arXiv_Catchup/catchup.py -f` whenever
# However, this script can be used to offload the search times (3s per ten papers) to a cron job.
# The only impact to you would be the 0.25s per filtered paper opened in the browser.
# If you rarely want to open all papers, this is the recommended method.

# Find the directory of this file
root_dir = pathlib.Path(__file__).resolve().parent.parent

# Parse command-line arguments
parser = argparse.ArgumentParser(
    prog="Catchup file opening",
    description="Opens all links in the catchup text file, then clears it.",
)
parser.add_argument(
    "-v",
    "--verbosity",
    type=int,
    default=3,
    help="Set the verbosity level.\n0 => critical errors\n...\n4 => ... and debug messages",
)
args = parser.parse_args()

# Extract some of the required constants
filenames = Paths(
    prevsearch=root_dir / "prev_search.txt",
    searchterms=root_dir / "search_terms.yaml",
    catchup=root_dir / "catchup.txt",
    searchxml=root_dir / "search.xml",
    papersxml=root_dir / "papers.xml",
)

# XML namespaces used by arXiv
ns = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}
# Define arXiv API courtesy limits
# These are the values that arXiv asks we obey. Do not alter them.
SLEEP_OPENING = 0.25  # 0.25 seconds between opening links

# Setup logging
logger = logger_setup(args, root_dir)

# Read the catchup file
papers = read_catchup(logger, filenames.catchup, SLEEP_OPENING)

# Ask the user if the file should be deleted
delete_catchup(logger, filenames.catchup, papers)
