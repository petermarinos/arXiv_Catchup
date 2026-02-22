"""The main script."""

# fmt: off
# Import standard libraries
import pathlib

# Import classes
from .arxiv_client import ArxivClient
from .config       import Config
from .corpus       import Corpus
from .cli          import CLI

# Import functions
from .file_io import write_aux_files
from .output  import display
from .utils   import logger_setup
# fmt: on

# # TO-DO:
#
# # Current branch will fix issues #32, #33, #34, and #35


# The main script
# Performs the entire pipeline
def main():
    """Pipeline that runs from start to finish."""

    root_path = pathlib.Path(__file__).resolve().parent.parent

    # # # Parse command-line arguments
    cli = CLI()

    # # Set up the logger
    logger = logger_setup(cli.args, root_path)

    # # Set up the papers class
    search_params = Config(logger, root_path)

    # # Load search terms from the auxiliary file
    search_params.get_searchterms()

    # # Load the dates
    search_params.get_dates(cli.args)

    # # Check for errors with the dates
    search_params.date_error_check()

    # # Setup the API information
    api = ArxivClient(search_params)

    # # Obtain basic search information
    api.get_search_info(search_params.paths["searchxml"])

    # # Check for errors
    api.arxiv_error_check()
    cli.check_continue_status(logger, api, search_params.paths["searchxml"])

    # # Loop through the searches and obtain all papers
    corpus = Corpus(logger)
    corpus.get_papers(api, search_params.paths["papersxml"])

    # # Find matches in the papers
    corpus.find_matches(search_params.search_terms)

    # # Score the papers
    # # Score based on author/word matches
    corpus.score_papers_matches()
    # # Score based on the ML model
    # # NOT YET IMPLEMENTED
    # corpus.score_papers_ml()

    # # Filter the papers
    # # Filter based on matches
    # corpus.filter_papers_matches()
    # Filter based on score
    corpus.filter_papers_score()

    # # Display the results
    cli.get_display_method(api, corpus)
    display(
        logger,
        cli.args,
        corpus.papers_of_note,
        cli.open_in_brower,
        api.SLEEP_OPENING,
        cli.write_to_file,
        search_params.paths["catchup"],
    )

    # # Write some auxiliary file(s) for the next run
    write_aux_files(
        logger, search_params.paths["prevsearch"], search_params.end_date, corpus.length
    )

    print("Not deleting temp. files.")
    # # Delete xmls/other supplemental files if successfull
    # pipeline.clear_temp_files()

    # # Print a summary
    corpus.summary()
