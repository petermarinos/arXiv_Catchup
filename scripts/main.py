# The main script
# Takes in arguments and runs the entire pipeline

# Import libraries
from scripts.arxiv_query import arxiv_initial_pull, arxiv_loop_pull
from scripts.constants   import aux_filenames, arxiv_constants
from scripts.filtering   import filter_papers
from scripts.output      import display_results
from scripts.utils       import load_searchterms, cli_args
from scripts.dates       import date_setup

def main(cdir):

    # # Parse command-line arguments
    args = cli_args()

    # Define filenames of the auxiliary files
    filename_prevsearch, filename_searchterms, filename_paperlinks = aux_filenames(cdir)

    # Return arXiv constants
    url, ns, sleep_opening, sleep_search, search_blocksize = arxiv_constants()
    
    # Load search terms from the auxiliary file
    search_terms, cat_urlstring = load_searchterms(filename_searchterms)

    # Load and check dates
    start_date, end_date = date_setup(args, filename_prevsearch)

    # Obtain basic search information
    max_num = arxiv_initial_pull(ns,
                                 url,
                                 start_date,
                                 end_date,
                                 cat_urlstring,
                                 sleep_search,
                                 search_blocksize)

    # Loop through the searches and obtain all papers
    df_papers = arxiv_loop_pull(ns,
                                url,
                                start_date,
                                end_date,
                                cat_urlstring,
                                max_num,
                                sleep_search,
                                search_blocksize)

    # Filter the papers
    papers_of_note = filter_papers(df_papers, search_terms)

    # Display the results
    display_results(args, df_papers, papers_of_note, sleep_opening, filename_paperlinks, filename_prevsearch, end_date, max_num)