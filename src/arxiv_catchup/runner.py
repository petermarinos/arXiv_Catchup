"""The main script."""

# Import classes
from .storage_manager import Storage
from .arxiv_client import ArxivClient
from .http_client import HttpClient
from .config import Config
from .corpus import Corpus
from .cli import CLI

# Import functions
from .utils import logger_setup


# The main script
# Performs the entire pipeline
def main() -> None:
    """Pipeline that runs from start to finish."""

    # # Parse command-line arguments
    cli = CLI()

    # # Set up the storage manager
    storage = Storage()

    # # Set up the logger
    logger_setup(cli.args, storage.paths.log)

    # # Add the logger to the CLI and storage objects
    cli.add_logger()
    storage.add_logger()

    # # Set up the papers class
    search_params = Config()

    # # Load search terms from the auxiliary file
    search_params.get_searchterms(storage)

    # # Load the dates
    search_params.get_dates(storage, cli.args)

    # # Check for errors with the dates
    search_params.date_error_check()

    # # Set up the client that will connect to the servers
    http_client = HttpClient()

    # # Setup the API information
    api = ArxivClient(search_params, http_client)

    # # Obtain basic search information
    api.get_search_info(storage)

    # # Check for errors
    api.arxiv_search_error_check()
    cli.check_continue_status(api, storage, storage.paths.search_xml)

    # # Loop through the searches and obtain all papers
    corpus = Corpus()
    api.get_papers(corpus, storage)

    # # Find matches in the papers
    corpus.find_matches(search_params.search_terms)

    # # Score the papers
    cli.score_papers(corpus)

    # # Filter the papers
    cli.filter_papers(corpus)

    # # Display the results
    cli.get_display_method(api, corpus)
    cli.display(
        storage,
        corpus.papers_of_note,
        api.SLEEP_OPENING,
    )

    # # Write some auxiliary file(s) for the next run
    storage.write_aux_files(search_params.end_date, corpus.length)

    # # Delete xmls/other supplemental files if successfull
    storage.delete_temp_files(cli.args.keep_temp)

    # # Print a summary
    corpus.summary()
