# Import functions
from scripts.arxiv_query import arxiv_initial_pull, arxiv_search, arxiv_errorcheck
from scripts.filtering   import score_papers_matches, score_papers_ML, filter_papers_matches, filter_papers_score
from scripts.constants   import set_filenames, set_arxiv_constants, arxivConst
from scripts.file_io     import load_searchterms, display_results
from scripts.dates       import date_setup, date_errorcheck
from scripts.utils       import logger_setup, open_links, summarise_search

# Import libraries
import datetime

# Define the class
class Papers(object):

    # Initialise the class
    def __init__(self, cdir, args):

        self.args   = args
        self.logger = logger_setup(args)
        self.paths  = set_filenames(cdir)

        url, apiquery, ns, sleep_opening, sleep_search, search_blocksize = set_arxiv_constants()
        self.arxivConst = arxivConst(url=url,
                                     apiquery=apiquery,
                                     ns=ns,
                                     sleeptimer_opening=sleep_opening,
                                     sleeptimer_search=sleep_search,
                                     search_blocksize=search_blocksize)
        
       # Define the posting time of the daily list
        self.post_time    = datetime.time(6, 0, tzinfo=datetime.timezone.utc)  # 06:00 UTC
        # Define the posting time of the daily list
        self.search_time  = datetime.time(19, 0, tzinfo=datetime.timezone.utc) # 19:00 UTC
        # Obtain the current time, converted to the UTC timezone
        self.current_time = datetime.datetime.now(datetime.timezone.utc)
        
    # # Load search terms from the auxiliary file
    def getSearchterms(self):
        self.search_terms, self.cat_urlstring = load_searchterms(self)

    # # Load and check dates
    def getDates(self):
        self.start_date, self.end_date = date_setup(self)
        date_errorcheck(self)
        # Format the url and apiquery
        self.arxivConst.url = self.arxivConst.url.format(
                                  start_year  = self.start_date.year,
                                  start_month = self.start_date.month,
                                  start_day   = self.start_date.day,
                                  end_year    = self.end_date.year,
                                  end_month   = self.end_date.month,
                                  end_day     = self.end_date.day,
                                  cats        = self.cat_urlstring,
                                  )
        self.arxivConst.apiquery = self.arxivConst.apiquery.format(
                                  start_year  = self.start_date.year,
                                  start_month = self.start_date.month,
                                  start_day   = self.start_date.day,
                                  end_year    = self.end_date.year,
                                  end_month   = self.end_date.month,
                                  end_day     = self.end_date.day,
                                  cats        = self.cat_urlstring,
                                  )

    # # Obtain basic search information
    def getSearchInfo(self):
        self.total_papers = arxiv_initial_pull(self)
        arxiv_errorcheck(self)

    # # Loop through the searches and obtain all papers
    def getPapers(self):
        self.df_papers = arxiv_search(self)

    # Score the papers
    def scorePapers(self):
        # Score based on matches
        self.author_str = score_papers_matches(self)
        # # Score based on an ML algorithm (NOT YET IMPLEMENTED)
        # score_papers_ML(self)

    # # Filter the papers based on matches
    def filterPapersMatches(self):
        self.papers_of_note = filter_papers_matches(self)

    # Filter the papers based on their scores
    def filterPapersScore(self):
        self.papers_of_note = filter_papers_score(self)

    # # Display the results
    def display(self):
        self.open_in_brower = display_results(self)
        if self.open_in_brower:
            open_links(self)        

    def summary(self):
        summarise_search(self)