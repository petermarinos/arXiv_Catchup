"""arXiv client class, which sets up the connections to the API."""

# Import standard libraries
import xml.etree.ElementTree as ET
import math
import os

# Import classes
from .storage_manager import Storage
from .http_client import HttpClient
from .config import Config
from .corpus import Corpus

# Import functions
from .ui import pretty_sleep, progress_bar


class ArxivClient:
    """Set up the API so that connections can be made."""

    # All 8 attributes are required to ensure connections can be made to the arXiv servers,
    #     and for error checking.
    # Disable pylint warning for >7 attributes
    # pylint: disable=R0902

    # # Constants relating to connecting to the arXiv servers.
    # DO NOT CHANGE

    # Define arXiv API courtesy limits
    # These are the values that arXiv asks we obey.
    SLEEP_OPENING = 0.25  # 0.25 seconds between opening links
    SLEEP_SEARCH = 3  # 3 seconds per search
    SEARCH_BLOCKSIZE = 10  # Each search downloads only ten papers (max=2000)

    # Define the 'sleep_fudge'.
    # Used to overestimate remaining times to account for jitter and server response times.
    # Superficial number and not important
    SLEEP_FUDGE = 0.70 + 0.15

    # XML namespaces used by arXiv
    NS = {
        "atom": "http://www.w3.org/2005/Atom",
        "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    def __init__(self, config: Config, http_client: HttpClient) -> None:
        """Set up some information that is required for the arXiv API calls.

        inputs
        ------
        config      : Run configuration.
        http_client : The client that performs the connections to the arXiv servers.
        """

        self.logger = config.logger

        # Define the urls
        # Double braces, {{}}, used for fields that change on each search
        url = (
            "https://export.arxiv.org/api/query?search_query="
            "submittedDate:[{start_year:d}{start_month:02d}{start_day:02d}1900%20"
            "TO%20{end_year:d}{end_month:02d}{end_day:02d}1900]+"
            "AND+{cats:s}&"
            "sortBy=submittedDate&"
            "start={{start_num:d}}&"
            "max_results={{blocksize:d}}"
        )

        apiquery = (
            "https://arxiv.org/api/query?search_query="
            "submittedDate:%22{start_year:d}{start_month:02d}{start_day:02d}1900+"
            "TO+{end_year:d}{end_month:02d}{end_day:02d}1900%22+"
            "AND+{cats:s}&"
            "start={{start_num:d}}&"
            "max_results={{blocksize:d}}&"
            "id_list="
        )

        # Format the url
        self.url = url.format(
            start_year=config.start_date.year,
            start_month=config.start_date.month,
            start_day=config.start_date.day,
            end_year=config.end_date.year,
            end_month=config.end_date.month,
            end_day=config.end_date.day,
            cats=config.cat_urlstring,
        )

        # Format the API url
        cats = config.search_terms.get("Categories")
        # Ensure there is at least one category to search
        # Should be handled while loading the .yaml, but double-check here
        if cats is None or len(cats) == 0:
            raise ValueError("Empty set of categories to search.")
        # If only one category, change nothing
        if len(cats) == 1:
            api_catstring = config.cat_urlstring
        # If multiple categories, surround with parentheses
        else:
            api_catstring = f"({config.cat_urlstring})"

        self.apiquery = apiquery.format(
            start_year=config.start_date.year,
            start_month=config.start_date.month,
            start_day=config.start_date.day,
            end_year=config.end_date.year,
            end_month=config.end_date.month,
            end_day=config.end_date.day,
            cats=api_catstring,
        )

        # Total number of papers that will be searched for
        # Different to the length of the Corpus (though they should be equal at the end).
        self.total_papers = 0

        # Insert the http client
        self.http_client = http_client

    def arxiv_search_error_check(self) -> None:
        """Runs some error checks on the results of the initial arXiv API pull.
        (i.e. the one that collects some basic information)."""

        self.logger.debug("Checking for issues with the search information ...")

        # If no papers were found in the search, raise an error
        # This should catch deferred mailings
        if self.total_papers == 0:
            self.logger.critical(
                "There were no papers submitted to the arXiv.\n          "
                "Refine search dates/categories and check for deferred mailings:\n          "
                "https://info.arxiv.org/help/availability.html\n"
            )
            raise RuntimeError("No papers were submitted to the arXiv.")

        # If there are too many papers then there can be issues with the arXiv API.
        # While the API will likely return an error, catch it here as well just in case
        if self.total_papers >= 30000:

            self.logger.critical(
                "Number of papers is too large. Refine search dates and/or categories.\n"
            )
            raise RuntimeError("Too many papers were submitted to the arXiv.")

        self.logger.debug("All search information tests passed!")

    def get_search_info(self, storage: Storage) -> None:
        """Obtain the information on how we will obtain all papers within the search period.
        Will attempt to load from an .xml file.
        Will fall back to connecting to the arXiv servers if:
        1) can't find the file, or
        2) the file does not match the current search parameters.

        inputs
        ------
        storage : The storage manager.
        """

        # Initialise the xml data
        # This is just to ensure the type checker understands
        xml_root: ET.Element | None = None

        # Search for xml file. If found, load it
        if os.path.exists(storage.paths.search_xml):

            self.logger.info(f"Found a .xml file: {storage.paths.search_xml}")
            self.logger.info("Attempting to continue from the previous failed run.")

            # Define the url we expect from the file
            expected_url = self.apiquery.format(start_num=0, blocksize=1)

            # Load the file
            xml_tree = storage.read_xml_file(self.NS, expected_url, True)
            xml_root = xml_tree.getroot()

        # If there is no file, perform the search
        # NOTE: This is not an elif as the above if statement can delete the file.
        #       If the file is deleted, we want to be redownloaded.
        #       If the file never existed, we want to download.
        #       If the file existed and had the correct information, then skip below
        if not os.path.exists(storage.paths.search_xml):

            self.logger.info("Obtaining search information from the servers.")

            # Perform the query
            xml_root = self.http_client.arxiv_query(self.url, 0, 1)

            # Write the extracted xml to a file
            storage.write_xml_file(xml_root, self.NS, True)

            self.logger.info(
                "Search information successfully obtained from the arXiv servers!"
            )

        # Confirm that the xml data was loaded
        # This *should* never activate, but is needed for safety
        if xml_root is None:
            self.logger.critical("Issue with the xml data. Did not load correctly.\n")
            raise TypeError("XML data was None")

        # Extract the total number of papers that were found
        max_num_temp = xml_root.find("opensearch:totalResults", self.NS)
        if max_num_temp is None:
            self.logger.critical(
                "arXiv data did not include a number of papers. It is corrupted.\n"
            )
            raise RuntimeError("The arXiv results are missing critical data...?")
        max_num_str = max_num_temp.text
        if max_num_str is None:
            self.logger.critical(
                "The number of papers is corrupted (couldn't convert from Element).\n"
            )
            raise AttributeError("Could not extract number of papers from the data...?")

        # Set the number of papers
        self.total_papers = int(max_num_str)

    def get_papers(self, corpus: Corpus, storage: Storage) -> None:
        """Obtains all Papers and places them in the Corpus.
        Will attempt to load the Corpus from an .xml file.
        Will fall back to connecting to the arXiv servers if:
        1) can't find the file, or
        2) the file does not match the current search parameters.

        inputs
        ------
        corpus  : The corpus of all papers.
        storage : The storage object.
        """

        # Search for xml file. If found, load it
        if os.path.exists(storage.paths.papers_xml):

            self.logger.info(f"Found an .xml file: {storage.paths.papers_xml}")
            self.logger.info("Attempting to continue a previous failed run.")

            # Define the url we expect from the file
            expected_url = self.apiquery.format(
                start_num=0, blocksize=self.SEARCH_BLOCKSIZE
            )

            # Load the file
            xml_tree = storage.read_xml_file(self.NS, expected_url, False)

            # Extract the papers from the xml
            corpus.extract_papers(self.NS, xml_tree)

        # If all papers were found, log a message and continue
        if corpus.length == self.total_papers:

            self.logger.info("All papers found in the .xml file!")

        # If the xml file had more papers than expected, discard and redownload
        # Only possible if the temp xml file is altered manually
        elif corpus.length > self.total_papers:

            self.logger.info("Too many papers found in the .xml file. Redownloading")

            # Clear the entries from the list.
            corpus.clear_corpus()

        # If there were fewer papers in the xml than we expected, connect to arXiv
        # NOTE: Not an elif in the case that the above statement clears the corpus
        if corpus.length < self.total_papers:

            self.logger.debug(f"The number of papers found so far is: {corpus.length}")

            # # Compute the estimated time for the search
            est_time = -(self.SLEEP_SEARCH + self.SLEEP_FUDGE) * (
                (self.total_papers - corpus.length) // -self.SEARCH_BLOCKSIZE
            )

            # Compute the number of steps it will take
            num_steps = math.ceil(
                (self.total_papers / self.SEARCH_BLOCKSIZE) * self.SEARCH_BLOCKSIZE
            )

            # Search the arXiv
            self.logger.info(
                f"Searching for papers. Estimated time: {est_time:.0f} seconds"
            )
            start_index = (
                corpus.length
            )  # self.length updates when adding papers. Need a constant
            for ii in range(start_index, self.total_papers, self.SEARCH_BLOCKSIZE):

                # Compute the progress of the loop
                if ii + self.SEARCH_BLOCKSIZE > self.total_papers:
                    remaining_steps = 1
                    search_interval = self.total_papers - ii
                    search_endnum = self.total_papers
                else:
                    remaining_steps = -(
                        (self.total_papers - ii) // -self.SEARCH_BLOCKSIZE
                    )
                    search_interval = self.SEARCH_BLOCKSIZE
                    search_endnum = ii + self.SEARCH_BLOCKSIZE

                # Print the progress bar
                progress_bar(
                    ii,
                    num_steps,
                    remaining_steps * (self.SLEEP_SEARCH + self.SLEEP_FUDGE),
                )

                # Debug messages
                self.logger.debug(f"Remaining steps: {remaining_steps}")
                self.logger.debug(f"Starting number: {ii}")
                self.logger.debug(f"Ending number:   {search_endnum}")

                # Sleep before the query so that there is no dead time on the last query.
                # Also need to sleep here as we do not wait after the initial API call
                progress_bar(ii, num_steps, remaining_steps * self.SLEEP_SEARCH)
                pretty_sleep(self.logger, self.SLEEP_SEARCH)

                # Query the API
                xml_root = self.http_client.arxiv_query(
                    self.url,
                    ii,
                    search_interval,
                )

                # Write the xml to a file
                storage.write_xml_file(xml_root, self.NS, False)

                # Extract the paper from the xml
                corpus.extract_papers(self.NS, xml_root)

            # Close the progress bar
            progress_bar(self.total_papers, self.total_papers)

            self.logger.info(
                "All paper information successfully downloaded from the arXiv servers!"
            )

        # Double check that we found the correct number of papers
        if corpus.length != self.total_papers:

            self.logger.error(
                f"Found {corpus.length} papers (expected {self.total_papers})."
            )

        else:

            self.logger.debug(
                f"Found the expected number of papers ({self.total_papers})."
            )

        # Remove revised papers
        corpus.drop_revisions()
