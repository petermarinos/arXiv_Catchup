# Import packages
from scripts.constants import aux_filenames, arxiv_constants
from scripts.output    import read_catchup
from scripts.utils     import clear_catchup

import os

# Find the directory of this file
cdir = os.path.dirname(os.path.realpath(__file__))

# Extract some of the required constants
prevsearch, searchterms, paperlinks = aux_filenames(cdir)
url, ns, sleep_opening, sleep_search, search_blocksize = arxiv_constants()

# Read the catchup file
papers = read_catchup(paperlinks, sleep_opening)

# Ask the user if the file should be cleared
clear_catchup(paperlinks, papers)