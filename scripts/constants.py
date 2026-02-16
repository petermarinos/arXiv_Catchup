# Import libraries
from dataclasses import dataclass

def set_filenames(cdir):
    """Compute the filenames of various auxiliary files that may or may not be used.

    inputs
    ------
    cdir : str
        Top directory of the project, i.e. `/path/to/arXiv_Catchup/`.

    outputs
    -------
    filenames : dict
        Contains the path+filename for the various auxiliary/temporary files the script requires/creates.
    """

    # Place filenames into a dictionary
    filenames = {
                 "prevsearch"  : cdir+"/prev_search.txt",   # File that stores the date of the previous run
                 "searchterms" : cdir+"/search_terms.yaml", # File that stores the search terms
                 "catchup"     : cdir+"/catchup.txt",       # File that stores the links to the papers of interest (if writing to a file)
                 "searchxml"   : cdir+"/search.xml",        # File that stores the .xml data of the initial arXiv query, i.e. the information on the search
                 "papersxml"   : cdir+"/papers.xml",        # File that stores the .xml data for all downloaded papers
                }
    
    return filenames

def set_arxiv_constants() -> tuple[str, str, dict, float, float, int]:
    """Define the constants that will be used when making API calls to arXiv.

    outputs
    -------
    url              : str
        Unformatted url that is used for the API calls to arXiv.
    apiquery         : str
        Unformatted url that is returned by API calls to arXiv.
    ns               : dict
        XML namespaces used by arXiv.
    sleep_opening    :
        Sleep timer (in seconds) between opening links in the browser. arXiv asks this to be limited to 0.25s per link.
    sleep_search     :
        Sleep timer (in seconds) between searches of papers. arXiv asks this to be limited to 3s per search.
    search_blocksize : int
        Size of the block used when searching through the papers. arXiv asks this to be limited to 10.
    """

    # Define the urls
    # Double braces, {{}}, used for fields that change on each search
    url      = "https://export.arxiv.org/api/query?search_query=submittedDate:[{start_year:d}{start_month:02d}{start_day:02d}1900%20TO%20{end_year:d}{end_month:02d}{end_day:02d}1900]+AND+{cats:s}&sortBy=submittedDate&start={{start_num:d}}&max_results={{blocksize:d}}"
    apiquery = "https://arxiv.org/api/query?search_query=submittedDate:%22{start_year:d}{start_month:02d}{start_day:02d}1900+TO+{end_year:d}{end_month:02d}{end_day:02d}1900%22+AND+({cats:s})&start={{start_num:d}}&max_results={{blocksize:d}}&id_list="

    # XML namespaces used by arXiv
    ns = {
        "atom"       : "http://www.w3.org/2005/Atom",
        "opensearch" : "http://a9.com/-/spec/opensearch/1.1/",
        "arxiv"      : "http://arxiv.org/schemas/atom",
        }

    # Define arXiv API courtesy limits
    # These are the values that arXiv asks we obey. Do not alter them.
    sleep_opening    = 0.25 # 0.25 seconds between opening links
    sleep_search     = 3    # 3 seconds per search
    search_blocksize = 10   # Each search downloads only ten papers (max=2000)

    return url, apiquery, ns, sleep_opening, sleep_search, search_blocksize

# Set up a dataclass
@dataclass
class arxivConst:
    url:                str
    apiquery:           str
    ns:                 dict[str, str]
    sleeptimer_opening: float
    sleeptimer_search:  float
    search_blocksize:   int