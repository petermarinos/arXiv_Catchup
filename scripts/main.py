# Import classes
from .catchup_classes import CatchupPipeline

# Import functions
from .utils import cli_args

"""TO-DO:

Update all function descriptions

Add comments to classes
Add documentation to class functions
Functions that loop through the Corpus should be moved to the Corpus class

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

    # # Load the dates
    pipeline.getDates()

    # # Check for errors with the dates
    pipeline.dateErrorCheck()

    # # Setup the API information
    pipeline.setupAPI()

    # # Obtain basic search information
    pipeline.getSearchInfo()

    # # Check for errors
    pipeline.arxivErrorCheck()

    # # Loop through the searches and obtain all papers
    pipeline.getPapers()

    # # Find matches in the papers
    pipeline.findMatches()

    # # Score the papers
    pipeline.scorePapersMatches()
    # pipeline.scorePapersML()

    # # Filter the papers
    # # Filter based on matches
    # pipeline.filterPapersMatches()
    # Filter based on score
    pipeline.filterPapersScore()

    # # Display the results
    pipeline.getDisplayMethod()
    pipeline.display()

    # print("Not deleting temp. files.")
    # # Delete xmls/other supplemental files if successfull
    pipeline.clearTempFiles()

    # # Print a summary
    pipeline.summary()