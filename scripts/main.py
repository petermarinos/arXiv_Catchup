# Import classes
from scripts.paper_class import Papers

# Import functions
from scripts.utils import cli_args

"""TO-DO:

Add the ability to include given names. Update README

Add a flag to write only the arXiv IDs to a file. Update README.

Currently, author_search() and word_search() actually compute the scores for the authors/words.
    Change so that these functions place the information of the number of matches, the locations, etc. in an output? or the Papers object?
    Then, score_papers_matches() should actually compute the scores
    Note that this would lead to papers in the print string that may be excluded from their scores. Maybe compute the print string later?
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