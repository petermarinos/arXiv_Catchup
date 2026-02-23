"""arXiv client class, which controls connections to the API."""

# fmt: off
# Import standard libraries
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import pathlib
import ssl
import os

# Import non-standard libraries
import certifi

# # Import libraries used to test API connections and errors
# from email.message import Message
# from unittest.mock import patch

# Import classes
from .config import Config

# Import functions
from .file_io import write_xml
from .utils   import delete_file
from .ui      import pretty_sleep
# fmt: on


class ArxivClient:
    """Defines all data that is used to connect to the arXiv servers.
    Also performs said connections.
    """

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

    # Define some values for retry attempts. These are magic values and kept from the users.
    # These can be altered as arXiv does not specify values.
    # However, these values are pretty typical so it is best to leave them.
    MAX_RETRIES = 5  # Maximum number of retried connections
    BACKOFF = 2  # Factor to increase the wait_time after a failure
    TIMEOUT = 30  # Seconds to wait before a timeout

    # Define some error codes. If one of these, we will retry
    RETRY_CODES = (
        408,  # Request timeout
        429,  # Too many requests
        500,  # Internal server error. Also caused by malformed urls in the request.
        502,  # Bad gateway
        503,  # Service unavailable (i.e. overloaded or down)
        504,  # Gateway timeout
    )

    # XML namespaces used by arXiv
    NS = {
        "atom": "http://www.w3.org/2005/Atom",
        "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    def __init__(self, config: Config) -> None:
        """Set up some information that is required for the arXiv API calls.

        inputs
        ------
        config : Run configuration
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

        # Initialise wait times. Values will be modified if connection errors occur
        self.wait_time = 3.0
        self.retry_after = 0.0

        # Total number of papers that will be searched for
        # Different to the length of the Corpus (though they should be equal at the end).
        self.total_papers = 0

        # Define the ssl_context and define a flag
        self.ssl_context = ssl.create_default_context()
        self.cert_error_bool = False

    def http_errorcheck(self, error: urllib.error.HTTPError, attempt: int) -> None:
        """Handles the HTTP errors that could arise.

        inputs
        ------
        error   : Error returned from the connection attempt.
        attempt : Attempt number.
        """

        # If the HTTP error is in our list of codes that tell us to retry
        if error.code in self.RETRY_CODES:

            self.logger.warning(
                f"HTTP error code {error.code} on attempt {attempt} of {self.MAX_RETRIES}."
            )

            # Obtain some additional information from the error headers

            # If the error header is empty
            # Probably unnecessary, but good to check
            if not error.headers:

                self.logger.debug("HTTP error header was empty.")

            # Else, if the header isn't empty
            else:

                for key, value in error.headers.items():
                    self.logger.debug(f"HTTP header: {key}: {value}")

                # Obtain the 'Retry-After' header
                retry = error.headers.get("Retry-After")

                # If there is a Retry-After header
                if retry is not None:

                    self.logger.debug("Found Retry-After header.")

                    self.retry_after = float(retry)

                    self.logger.warning(
                        "---> Received a wait command from the server. "
                        f"Increasing wait time to the recommended {self.retry_after} seconds ..."
                    )

                # Catch 429 error codes that do not have a Retry-after header
                elif (retry is None) and (error.code == 429):

                    self.retry_after = 90.0 * attempt
                    self.logger.warning(
                        "Did not find a Retry-After command despite being a 429 error. "
                        f"Increasing wait time to {self.retry_after} seconds ..."
                    )

                # Else, if there are headers but no retry-after header
                else:

                    self.logger.debug("Did not find a Retry-After header.")

        # Otherwise, raise an error
        else:

            self.logger.critical(f"HTTP error code {error.code}: {error.reason}\n")
            for key, value in error.headers.items():
                self.logger.debug(f"HTTP header: {key}: {value}")
            raise RuntimeError("Received non-retry HTTP error code.")

    def url_errorcheck(self, error: urllib.error.URLError) -> None:
        """Handles the URL errors that could arise.

        inputs
        ------
        error : Error returned from the connection attempt.
        """

        # If it is a certificate verification error, and no certification error has occured before:
        if (
            isinstance(error.reason, ssl.SSLCertVerificationError)
            and not self.cert_error_bool
        ):

            # Warn the user that verification failed
            self.logger.warning(
                f"Connection error: {error.reason}. "
                f"Updating certificate and retrying in {self.wait_time} seconds ..."
            )

            # Try updating the ssl_context to use the certifi cafile
            self.ssl_context = ssl.create_default_context(cafile=certifi.where())

            # Set the certification error flag to True
            self.cert_error_bool = True

        # If it is a certificate verification error, and we have tried certifying earlier:
        elif (
            isinstance(error.reason, ssl.SSLCertVerificationError)
            and self.cert_error_bool
        ):

            # Warn the user that we are disabling verification
            self.logger.warning("Verification still failed.")
            self.logger.warning(
                "This could potentially be an issue with your OS and its trust store, or the "
                "certifi package version, or a wifi proxy."
            )
            self.logger.info(
                f"Current certifi version: {certifi.__version__}. Recommended: >2026.01.04."
            )
            self.logger.warning(
                "This issue should be fixed before rerunning the script."
            )

        # # Add a CLI option to skip verification entirely?
        # Do not do it by default, and ensure the users are warned of the risk
        #     (e.g. by forcing to confirm a prompt)
        # self.logger.warning(
        #     f"Disabling verification and retrying in {self.wait_time} seconds ..."
        # )

        # # Disable verification
        # ssl._create_default_https_context = ssl._create_unverified_context

        # Otherwise, if it is any other type of URL error, raise an error
        else:

            self.logger.critical(f"Connection error: {error.reason}\n")
            raise RuntimeError("Unable to connect.")

    def arxiv_query(self, start_num: int, blocksize: int) -> ET.Element:
        """Queries the arXiv servers for the papers.
        Will catch errors and attempt retries (if the error allows retries).

        inputs
        ------
        start_num : Starting paper number for the search query.
        blocksize : Number of papers to download in the search query.
        """

        # Format the last two fields in the url
        formatted_url = self.url.format(start_num=start_num, blocksize=blocksize)

        self.logger.debug(
            f"Searching for papers {start_num} to {start_num+blocksize-1} ..."
        )

        # Query the server
        for attempt in range(
            1, self.MAX_RETRIES + 1
        ):  # 1 -> max_retries+1 so that we start counting attempts at 1 in the logger messages

            self.logger.debug(f"Attempting connection to:\n       {formatted_url}")

            try:

                # Test error handling
                # Add an indent to the "attempt to connect to arXiv"--"return parsed_xml_date" lines
                # -- add proper testing in the future

                # # HTTP ERRORS

                # # http error with a random code and no header
                # err = urllib.error.HTTPError(
                #     url=None, code=47, msg="fake error that should exit", hdrs=None, fp=None
                # )
                # with patch("urllib.request.urlopen", side_effect=err):

                # # http repeating error code with no header
                # err = urllib.error.HTTPError(
                #     url=None, code=408, msg="non-repeating code", hdrs=None, fp=None
                # )
                # with patch("urllib.request.urlopen", side_effect=err):

                # # http non-repeating error code with a useless header
                # headers = Message()
                # headers["blank"] = "nothing"
                # err = urllib.error.HTTPError(
                #     url=None, code=408, msg="non-repeating code", hdrs=headers, fp=None
                # )
                # with patch("urllib.request.urlopen", side_effect=err):

                # # http error with a retry-after header
                # headers = Message()
                # headers["Retry-After"] = 40
                # err = urllib.error.HTTPError(
                #     url=None, code=429, msg="repeating code", hdrs=headers, fp=None
                # )
                # with patch("urllib.request.urlopen", side_effect=err):

                # # URL ERRORS

                # # non-Verification errors
                # with patch(
                #     "urllib.request.urlopen", side_effect=urllib.error.URLError("DNS fail")
                # ):

                # # Verification errors
                # err = urllib.error.URLError(
                #     ssl.SSLCertVerificationError(
                #         "certificate verify failed: unable to get local issuer certificate"
                #     )
                # )
                # with patch("urllib.request.urlopen", side_effect=err):

                # Attempt to connect to arXiv
                with urllib.request.urlopen(
                    formatted_url, timeout=self.TIMEOUT, context=self.ssl_context
                ) as f:

                    self.logger.debug("...Connection successful")

                    # Read the data
                    xml_data = f.read()

                    # Parse the xml
                    # if ET.fromstring(xml_data) is None:
                    #     raise
                    # else:
                    parsed_xml_root = ET.fromstring(xml_data)

                    return parsed_xml_root

            # If there is a HTTP error:
            except urllib.error.HTTPError as error:

                self.http_errorcheck(error, attempt)

            # If there is a URL error:
            except urllib.error.URLError as error:

                self.url_errorcheck(error)

            # If there is a timeout error:
            except TimeoutError:

                self.retry_after = 60.0

                self.logger.warning(
                    f"Timeout Error. Retrying in {self.retry_after} seconds ..."
                )

            # If there is an error parsing the xml, raise an error
            except ET.ParseError as error:

                # May need to add a way to warn and skip.
                # This error shouldn't occur, but potenially could be due to malformed paper entries
                # It is rare error and difficult to know the cause -- it has only ever occured in
                # historical searches when testing.

                # # For now, raise an error
                self.logger.critical(
                    "XML parsing error. Please upload log file to github.\n"
                )
                self.logger.debug(error)
                raise

            # If there was a Retry-After command, replace the wait time
            if self.retry_after != 0.0:

                self.wait_time = self.retry_after

            # Sleep before retrying
            pretty_sleep(self.logger, self.wait_time)

            # If there was no retry after demand, increase the wait time for the next attempt
            if self.retry_after == 0.0:

                self.wait_time *= self.BACKOFF

        # If the loop completes and no data was downloaded, raise an error.
        self.logger.exception(
            "Maximum retries attempted. arXiv query failed.\n          "
            "Review connection error codes before trying again.\n"
        )
        raise RuntimeError("Cancelling arXiv connection. Too many attempts.")

    def get_search_info(self, xml_path: pathlib.Path) -> None:
        """Obtain the information on how we will obtain all papers within the search period.
        Will attempt to load from an .xml file.
        Will fall back to connecting to the arXiv servers if:
        1) can't find the file, or
        2) the file does not match the current search parameters.

        inputs
        ------
        xml_path : Path to searchxml
        """

        # Initialise the xml data
        # This is just to ensure the type checker understands
        xml_data: ET.Element | None = None

        # Search for xml file. If found, load it
        if os.path.exists(xml_path):

            self.logger.info(f"Found a .xml file: {xml_path}")
            self.logger.info("Attempting to continue from the previous failed run.")

            # Load the file
            xml_data = ET.parse(xml_path).getroot()

            # if xml_data is None:
            #     self.logger.exception("Empty .xml.")
            #     raise TypeError(".xml data was returned as None.")

            # Check the url from the loaded xml matches the current search url
            expected_url = self.apiquery.format(start_num=0, blocksize=1)
            returned_urlblock = xml_data.find("atom:link", self.NS)
            if returned_urlblock is None:
                self.logger.exception("No arXiv link (returned None).\n")
                raise TypeError(
                    "arXiv data did not include a link. It is corrupted (returned None)."
                )
            returned_url = returned_urlblock.attrib["href"]

            url_missmatch = expected_url != returned_url
            if url_missmatch:
                self.logger.warning(
                    "The .xml file information does not match the current search."
                    "Discarding the file and re-connecting."
                )
                self.logger.debug(f"Expected: {expected_url}")
                self.logger.debug(f"Found:    {returned_url}")

                # Clear the .xml file
                delete_file(self.logger, xml_path)
            else:
                self.logger.debug(
                    "The .xml file information matches the current search. Continuing"
                )

        # If there is no file, perform the search
        # NOTE: This is not an elif as the above if statement can delete the file.
        #       If the file is deleted, we want to be redownloaded.
        #       If the file never existed, we want to download.
        #       If the file existed and had the correct information, then skip below
        if not os.path.exists(xml_path):

            self.logger.info("Obtaining search information from the servers.")

            # Perform the query
            xml_data = self.arxiv_query(0, 1)

            # Write the extracted xml to a file
            write_xml(self.logger, xml_path, xml_data, self.NS, overwrite=True)

            self.logger.info(
                "Search information successfully obtained from the arXiv servers!"
            )

        # Confirm that the xml data was loaded
        # This *should* never activate, but is needed for safety
        if xml_data is None:
            self.logger.exception("Issue with the xml data. Did not load correctly.\n")
            raise TypeError("XML data was None")

        # Extract the total number of papers that were found
        max_num_temp = xml_data.find("opensearch:totalResults", self.NS)
        if max_num_temp is None:
            self.logger.exception(
                "arXiv data did not include a number of papers. It is corrupted.\n"
            )
            raise RuntimeError("The arXiv results are missing critical data...?")
        max_num_str = max_num_temp.text
        if max_num_str is None:
            self.logger.exception(
                "The number of papers is corrupted (couldn't convert from Element).\n"
            )
            raise AttributeError("Could not extract number of papers from the data...?")

        # Set the number of papers
        self.total_papers = int(max_num_str)

    def arxiv_error_check(self) -> None:
        """Runs some error checks on the results of the initial arXiv API pull.
        (i.e. the one that collects some basic information)."""

        self.logger.debug("Checking for issues with the search information ...")

        # If no papers were found in the search, raise an error
        # This should catch deferred mailings
        if self.total_papers == 0:
            self.logger.exception(
                "There were no papers submitted to the arXiv.\n          "
                "Refine search dates/categories and check for deferred mailings:\n          "
                "https://info.arxiv.org/help/availability.html\n"
            )
            raise RuntimeError("No papers were submitted to the arXiv.")

        # If there are too many papers then there can be issues with the arXiv API.
        # While the API will likely return an error, catch it here as well just in case
        if self.total_papers >= 30000:

            self.logger.exception(
                "Number of papers is too large. Refine search dates and/or categories.\n"
            )
            raise RuntimeError("Too many papers were submitted to the arXiv.")

        self.logger.debug("All search information tests passed!")
