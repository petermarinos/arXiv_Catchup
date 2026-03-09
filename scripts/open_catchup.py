"""Script that will run through the auxiliary file and open all links contained within.

CLI Arguments
-------------
-v: int -> verbosity level
"""

# # Import standard libraries
# import argparse

# Import classes
from arxiv_catchup.storage_manager import Storage
from arxiv_catchup.utils import logger_setup
from arxiv_catchup.cli import CLI
from arxiv_catchup.ui import open_links

# The goal of this script is to save the link opening for later if the user chooses
# However, it can also be used to automate the searches.

# Set up a cron job to run `/path/tp/arXiv_Catchup/catchup.py -w` daily.
# Then, when ready to open all the saved papers, run this script.

# This script is functionally equivalent to running `/path/tp/arXiv_Catchup/catchup.py -f` whenever
# However, this script can be used to offload the search times (3s per ten papers) to a cron job.
# The only impact to you would be the 0.25s per filtered paper opened in the browser.
# If you rarely want to open all papers, this is the recommended method.


# # Parse command-line arguments
cli = CLI()

# Extract some of the required constants
storage = Storage()

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
logger_setup(cli.args, storage.paths.log)
cli.add_logger()
storage.add_logger()

# Read the catchup file
papers = storage.read_catchup_file()

# Open the links
open_links(papers, SLEEP_OPENING)

# Ask the user if the file should be deleted
cli.get_delete_catchup_bool(storage, papers)
storage.delete_catchup_file(cli.delete_catchup)
