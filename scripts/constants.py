def aux_filenames(cdir):

    # Define filenames
    prevsearch  = cdir+"/prev_search.txt" # File that stores the date of the previous run
    searchterms = cdir+"/search_terms.yaml" # File that stores the search terms
    paperlinks  = cdir+"/catchup.txt" # File that stores the links to the papers of interest (if writing to a file)
    
    return prevsearch, searchterms, paperlinks

def arxiv_constants():

    # Define the search url
    url = "https://export.arxiv.org/api/query?search_query=submittedDate:[{start_year:d}{start_month:02d}{start_day:02d}1900%20TO%20{end_year:d}{end_month:02d}{end_day:02d}1900]+AND+{cats:s}&sortBy=submittedDate&start={start_num:d}&max_results={end_num:d}"

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