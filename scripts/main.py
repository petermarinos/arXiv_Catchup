# Import classes
from .SearchParameters import SearchParameters
from .Corpus           import Corpus
from .API              import API
from .CLI              import CLI

# Import functions
from .file_io import write_aux_files
from .output  import display
from .utils   import logger_setup

"""TO-DO:

AAAAAAAAAHH
"""

# The main script
# Performs the entire pipeline
def main(cdir):

    # # # Parse command-line arguments
    cli = CLI()

    # # Set up the logger
    logger = logger_setup(cli.args, cdir)

    # # Set up the papers class
    search_params = SearchParameters(logger, cdir)

    # # # Load the constants
    # arxiv_const = ArxivConst()

    # # Load search terms from the auxiliary file
    search_params.get_searchterms()

    # # Load the dates
    search_params.get_dates(cli.args)
    # search_parameters.get_dates()

    # # Check for errors with the dates
    search_params.date_error_check()
    # search_parameters.date_error_check()

    # # Setup the API information
    # pipeline.setup_API()
    api = API(logger, search_params.start_date, search_params.end_date, search_params.search_terms, search_params.cat_urlstring)

    # # Obtain basic search information
    # pipeline.get_search_info()
    api.get_search_info(api.arxiv_const, search_params.paths["searchxml"])

    # # Check for errors
    # pipeline.arxiv_error_check()
    api.arxiv_error_check(api.arxiv_const, search_params.paths["searchxml"])

    # # Loop through the searches and obtain all papers
    # pipeline.get_papers()
    corpus = Corpus(logger)
    corpus.get_papers(api.arxiv_const, api, search_params.paths["papersxml"])
    # corpus = get_papers(api, )

    # # Find matches in the papers
    corpus.find_matches(search_params.search_terms)

    # # Score the papers
    # # Score based on author/word matches
    corpus.score_papers_matches()
    # # Score based on the ML model
    # # NOT YET IMPLEMENTED
    # corpus.score_papers_ML()

    # # Filter the papers
    # # Filter based on matches
    # corpus.filter_papers_matches()
    # Filter based on score
    corpus.filter_papers_score()

    # # Display the results
    cli.get_display_method(api.arxiv_const, corpus)
    display(logger, cli.args, corpus.papers_of_note, cli.open_in_brower, api.arxiv_const.sleep_opening, cli.write_to_file, search_params.paths["catchup"])

    # # Write some auxiliary file(s) for the next run
    write_aux_files(logger, search_params.paths["prevsearch"], search_params.end_date, corpus.length)

    print("Not deleting temp. files.")
    # # Delete xmls/other supplemental files if successfull
    # pipeline.clear_temp_files()

    # # Print a summary
    corpus.summary()