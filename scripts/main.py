# Import classes
from .CatchupPipeline import CatchupPipeline

# Import functions
from .utils import cli_args

"""TO-DO:

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
    pipeline.get_searchterms()

    # # Load the dates
    pipeline.get_dates()

    # # Check for errors with the dates
    pipeline.date_error_check()

    # # Setup the API information
    pipeline.setup_API()

    # # Obtain basic search information
    pipeline.get_search_info()

    # # Check for errors
    pipeline.arxiv_error_check()

    # # Loop through the searches and obtain all papers
    pipeline.get_papers()

    # # Find matches in the papers
    pipeline.find_matches()

    # # Score the papers
    # # Score based on author/word matches
    pipeline.score_papers_matches()
    # # Score based on the ML model
    # # NOT YET IMPLEMENTED
    # pipeline.scorePapersML()

    # # Filter the papers
    # # Filter based on matches
    # pipeline.filter_papers_matches()
    # Filter based on score
    pipeline.filter_papers_score()

    # # Display the results
    pipeline.get_display_method()
    pipeline.display()

    # print("Not deleting temp. files.")
    # # Delete xmls/other supplemental files if successfull
    pipeline.clear_temp_files()

    # # Print a summary
    pipeline.summary()