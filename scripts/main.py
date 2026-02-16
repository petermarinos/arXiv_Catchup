# Import classes
from scripts.paper_class import Papers

# Import functions
from scripts.utils import cli_args

"""TO-DO:

Find out if it is working on Windows 11.

Normalise author strings when loading from the .yaml. Update advice in the README, as any accents or LaTeX commands could be added.

Add the ability to include given names.
    Escape text on regex searches.
    Update README.

Add a flag to write only the arXiv IDs to a file. Update README.
"""

# The main script
# Performs the entire pipeline
def main(cdir):

    # # Parse command-line arguments
    args = cli_args()

    # # Set up the papers class
    papers = Papers(cdir, args)

    # # Load search terms from the auxiliary file
    papers.getSearchterms()

    # # Load and check dates
    papers.getDates()

    # # Setup the API information
    papers.setupAPI()

    # # Obtain basic search information
    papers.getSearchInfo()

    # # Loop through the searches and obtain all papers
    papers.getPapers()

    # Score the paper
    papers.scorePapers()

    # # Filter the papers
    # # Filter based on matches
    # papers.filterPapersMatches()
    # Filter based on score
    papers.filterPapersScore()

    # # Display the results
    papers.display()

    # Delete xmls/other supplemental files if successfull
    papers.clearTempFiles()

    # # Print a summary
    papers.summary()