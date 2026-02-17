# Import classes
from .catchup_classes import CatchupPipeline

# Import functions
from .utils import cli_args

"""TO-DO:

Add type hints to functions

Refactor.
    Rename Papers class to CatchupPipeline -- DONE
    Create Paper class
    Remove pandas DataFrames

Add a flag to write only the arXiv IDs to a file. Update README.
"""

# The main script
# Performs the entire pipeline
def main(cdir):

    # # Parse command-line arguments
    args = cli_args()

    # # Set up the papers class
    pipeline = CatchupPipeline(cdir, args)

    # # Load search terms from the auxiliary file
    pipeline.getSearchterms()

    # # Load and check dates
    pipeline.getDates()

    # # Setup the API information
    pipeline.setupAPI()

    # # Obtain basic search information
    pipeline.getSearchInfo()

    # # Loop through the searches and obtain all papers
    pipeline.getPapers()

    # Score the paper
    pipeline.scorePapers()

    # # Filter the papers
    # # Filter based on matches
    # pipeline.filterPapersMatches()
    # Filter based on score
    pipeline.filterPapersScore()

    # # Display the results
    pipeline.display()

    print("Not deleting temp. files.")
    # # Delete xmls/other supplemental files if successfull
    # pipeline.clearTempFiles()

    # # Print a summary
    pipeline.summary()