"""The main GUI script, which allows the user to run the search step-by-step."""

# Import standard libraries

# Import non-standard libraries

# Import project classes
from arxiv_catchup.storage_manager import Storage
from arxiv_catchup.arxiv_client import ArxivClient
from arxiv_catchup.http_client import HttpClient
from arxiv_catchup.config import Config
from arxiv_catchup.corpus import Corpus
from arxiv_catchup.cli import CLI

from arxiv_catchup.gui.gui import GUI

# Import project functions
from arxiv_catchup.utils import logger_setup


def main() -> None:
    """Pipeline that creates the GUI and runs the analysis."""

    # # Create the GUI
    gui = GUI()

    # # # Parse command-line arguments
    # # These will all be set to their default values
    # cli = CLI()

    # # # Set up the storage manager
    # storage = Storage()

    # # # Set up the logger
    # logger_setup(cli.args, storage.paths.log)

    # # # Add the logger to the CLI and storage objects
    # cli.add_logger()
    # storage.add_logger()

    # # # Set up the papers class
    # search_params = Config()

    # # # Load search terms from the auxiliary file
    # search_params.get_searchterms(storage)

    # # # Load the dates
    # search_params.get_dates(storage, cli.args)

    # # # Check for errors with the dates
    # search_params.date_error_check()

    # # # Set up the client that will connect to the servers
    # http_client = HttpClient()

    # # # Setup the API information
    # api = ArxivClient(search_params, http_client)

    # # # Obtain basic search information
    # api.get_search_info(storage)

    # # # Check for errors
    # api.arxiv_search_error_check()
    # cli.check_continue_status(api, storage, storage.paths.search_xml)

    # # # Loop through the searches and obtain all papers
    # corpus = Corpus()
    # api.get_papers(corpus, storage)

    # # # Find matches in the papers
    # corpus.find_matches(search_params.search_terms)

    # # # Score the papers
    # cli.score_papers(corpus)

    # # # Filter the papers
    # cli.filter_papers(corpus)

    # # # Display the results
    # cli.get_display_method(api, corpus)
    # cli.display(
    #     storage,
    #     corpus.papers_of_note,
    #     api.SLEEP_OPENING,
    # )

    # # # Write some auxiliary file(s) for the next run
    # storage.write_aux_files(search_params.end_date, corpus.length)

    # # # Delete xmls/other supplemental files if successfull
    # storage.delete_temp_files(cli.args.keep_temp)

    # # # Print a summary
    # corpus.summary()
