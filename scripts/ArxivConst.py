# Import libraries
# from dataclasses import dataclass

class ArxivConst():

    def __init__(self) -> None:
        """Define the constants that will be used when making API calls to arXiv.
        """

        # Define the urls
        # Double braces, {{}}, used for fields that change on each search
        self.url      = "https://export.arxiv.org/api/query?search_query=submittedDate:[{start_year:d}{start_month:02d}{start_day:02d}1900%20TO%20{end_year:d}{end_month:02d}{end_day:02d}1900]+AND+{cats:s}&sortBy=submittedDate&start={{start_num:d}}&max_results={{blocksize:d}}"
        self.apiquery = "https://arxiv.org/api/query?search_query=submittedDate:%22{start_year:d}{start_month:02d}{start_day:02d}1900+TO+{end_year:d}{end_month:02d}{end_day:02d}1900%22+AND+{cats:s}&start={{start_num:d}}&max_results={{blocksize:d}}&id_list="

        # XML namespaces used by arXiv
        self.ns = {
                   "atom"       : "http://www.w3.org/2005/Atom",
                   "opensearch" : "http://a9.com/-/spec/opensearch/1.1/",
                   "arxiv"      : "http://arxiv.org/schemas/atom",
                  }

        # Define arXiv API courtesy limits
        # These are the values that arXiv asks we obey. Do not alter them.
        self.sleep_opening    = 0.25 # 0.25 seconds between opening links
        self.sleep_search     = 3    # 3 seconds per search
        self.search_blocksize = 10   # Each search downloads only ten papers (max=2000)

        return