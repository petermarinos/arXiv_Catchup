# Import classes
from scripts.paper_class import Papers

# Import functions
from scripts.utils import cli_args

"""TO-DO:

Find out if it is working on Windows 11.

Fix incorrect author ordering for the list of papers with found authors.

Add an exception for "TimeoutError: The read operation timed out" in arxiv_query, with a large backoff.
Add a check for the 429 error code -- if it is from arXiv, use the current backoff method. If it is from the infrastructure between the user and arXiv, use a much larger backoff.

Catch TimeoutErrors and deal with them

Add the ability to include given names. Update README.

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