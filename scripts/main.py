# Import libraries
from scripts.arxiv_query import arxiv_initial_pull, arxiv_search
from scripts.constants   import aux_filenames, arxiv_constants
from scripts.filtering   import filter_papers
from scripts.output      import display_results
from scripts.utils       import load_searchterms, cli_args, logger_setup, delete_file
from scripts.dates       import date_setup

# The main script
# Performs the entire pipeline
def main(cdir):

    # # Parse command-line arguments
    args = cli_args()

    # Setup logging
    logger = logger_setup(args)

    # Define filenames of the auxiliary files
    filename_prevsearch, filename_searchterms, filename_paperlinks, filename_searchxml, filename_papersxml = aux_filenames(cdir)

    # Return arXiv constants
    url, ns, sleep_opening, sleep_search, search_blocksize = arxiv_constants()
    
    # Load search terms from the auxiliary file
    search_terms, cat_urlstring = load_searchterms(filename_searchterms, logger)

    # Load and check dates
    start_date, end_date = date_setup(args, filename_prevsearch, logger)

    # Obtain basic search information
    max_num = arxiv_initial_pull(ns,
                                 url,
                                 start_date,
                                 end_date,
                                 cat_urlstring,
                                 sleep_search,
                                 search_blocksize,
                                 filename_searchxml,
                                 logger
                                 )

    # Loop through the searches and obtain all papers
    df_papers = arxiv_search(ns,
                             url,
                             start_date,
                             end_date,
                             cat_urlstring,
                             max_num,
                             sleep_search,
                             search_blocksize,
                             filename_papersxml,
                             logger
                             )

    # Filter the papers
    papers_of_note = filter_papers(df_papers, search_terms, logger)

    # Display the results
    display_results(args, df_papers, papers_of_note, sleep_opening, filename_paperlinks, filename_prevsearch, end_date, max_num, logger)

    # Delete xmls/other supplemental files if successfull
    delete_file(filename_searchxml, logger)
    delete_file(filename_papersxml, logger)