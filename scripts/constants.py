def aux_filenames(cdir):
    """Compute the filenames of various auxiliary files that may or may not be used.

    inputs
    ------
    cdir : str
        Top directory of the project, i.e. `/path/to/arXiv_Catchup/`.

    outputs
    -------
    prevsearch  : str
        Path+filename of the `prev_search.txt` file, that contains the date of the previous execution.
    searchterms : str
        Path+filename of the `search_terms.yaml` file, that contains all terms that are used in the search.
    paperlinks  : str
        Path+filename of the `catchup.txt` file, that contains all links of found papers.
    searchxml   : str
        Path+filename of the `search.xml` file, that contains the xml of the initial search.
    papersxml   : str
        Path+filename of the `papers.xml` file, that contains the xml of all found papers.
    """

    # Define filenames
    prevsearch  = cdir+"/prev_search.txt" # File that stores the date of the previous run
    searchterms = cdir+"/search_terms.yaml" # File that stores the search terms
    paperlinks  = cdir+"/catchup.txt" # File that stores the links to the papers of interest (if writing to a file)
    searchxml   = cdir+"/search.xml" # File that stores the links to the papers of interest (if writing to a file)
    papersxml   = cdir+"/papers.xml" # File that stores the links to the papers of interest (if writing to a file)
    
    return prevsearch, searchterms, paperlinks, searchxml, papersxml

def arxiv_constants():
    """Define the constants that will be used when making API calls to arXiv.

    outputs
    -------
    url              : str
        Unformatted url that is used for the API calls to arXiv.
    ns               : dict
        XML namespaces used by arXiv.
    sleep_opening    :
        Sleep timer (in seconds) between opening links in the browser. arXiv asks this to be limited to 0.25s per link.
    sleep_search     :
        Sleep timer (in seconds) between searches of papers. arXiv asks this to be limited to 3s per search.
    search_blocksize : int
        Size of the block used when searching through the papers. arXiv asks this to be limited to 10.
    """

    # Define the search url
    url = "https://export.arxiv.org/api/query?search_query=submittedDate:[{start_year:d}{start_month:02d}{start_day:02d}1900%20TO%20{end_year:d}{end_month:02d}{end_day:02d}1900]+AND+{cats:s}&sortBy=submittedDate&start={start_num:d}&max_results={blocksize:d}"

    # XML namespaces used by arXiv
    ns = {
        "atom"       : "http://www.w3.org/2005/Atom",
        "opensearch" : "http://a9.com/-/spec/opensearch/1.1/",
        "arxiv"      : "http://arxiv.org/schemas/atom",
        }

    # Define arXiv API courtesy limits
    sleep_opening    = 0.25 # 0.25 seconds between opening links
    sleep_search     = 3    # 3 seconds per search
    search_blocksize = 10   # Each search downloads only ten papers (max=2000)

    return url, ns, sleep_opening, sleep_search, search_blocksize