"""HTTP client class. Handles all connections, retry logic, etc."""

# Import standard libraries
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import logging
import ssl

# Import non-standard libraries
import certifi

# Import functions
from .xml_handling import convert_request_to_xml_root
from .ui import pretty_sleep


class TooManyAttempts(Exception):
    """Exception raised if too many connection attempts are made to the arXiv servers.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class HttpClient:
    """Performs the connections to the arXiv servers."""

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

    def __init__(self) -> None:
        """Set up the connection parameters."""

        # Obtain the logger
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initialising %s", self.__class__.__name__)

        # Initialise wait times. Values will be modified if connection errors occur
        self.wait_time = 3.0
        self.retry_after = 0.0

        # Define the ssl_context and define a flag
        self.ssl_context = ssl.create_default_context()
        self.cert_error_bool = False

    def arxiv_query(self, url: str, start_num: int, blocksize: int) -> ET.Element:
        """Queries the arXiv servers for the papers.
        Will catch errors and attempt retries (if the error allows retries).

        inputs
        ------
        url       : The url that will be used for connections.
        start_num : Starting paper number for the search query.
        blocksize : Number of papers to download in the search query.
        """

        # Format the last two fields in the url
        formatted_url = url.format(start_num=start_num, blocksize=blocksize)

        self.logger.debug(
            "Searching for papers %s to %s ...", start_num, start_num + blocksize - 1
        )

        self.logger.debug("Attempting connection to:\n       %s", formatted_url)

        # Query the server
        for attempt in range(
            1, self.MAX_RETRIES + 1
        ):  # 1 -> max_retries+1 so that we start counting attempts at 1 in the logger messages

            self.logger.debug("Attempt: %s", attempt)

            # Sleep before retrying
            if attempt > 1:
                pretty_sleep(self.logger, self.wait_time)

            try:

                # Attempt to connect to arXiv
                with urllib.request.urlopen(
                    formatted_url, timeout=self.TIMEOUT, context=self.ssl_context
                ) as f:

                    self.logger.debug("...Connection successful")

                    # Read the data
                    data = f.read()

                    xml_root = convert_request_to_xml_root(self.logger, data)

                    return xml_root

            # If there is a HTTP error:
            except urllib.error.HTTPError as error:

                self.http_errorcheck(error, attempt)

            # If there is a URL error:
            except urllib.error.URLError as error:

                self.url_errorcheck(error, attempt)

            # If there is a timeout error:
            except TimeoutError:

                self.retry_after = 60.0

                self.logger.warning(
                    "Timeout error on attempt %s of %s. Retrying in %s seconds ...",
                    attempt,
                    self.MAX_RETRIES,
                    self.retry_after
                )

            # If there was a Retry-After command, replace the wait time
            if self.retry_after != 0.0:

                self.wait_time = self.retry_after

            # If there was no retry after demand, increase the wait time for the next attempt
            if self.retry_after == 0.0:

                self.wait_time *= self.BACKOFF

        # If the loop completes and no data was downloaded, raise an error.
        self.logger.critical(
            "Maximum retries attempted. arXiv query failed.\n          "
            "Review connection error codes before trying again.\n"
        )
        raise TooManyAttempts("Cancelling arXiv connection. Too many attempts.")

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
                "HTTP error code %s on attempt %s of %s.",
                error.code,
                attempt,
                self.MAX_RETRIES,
            )

            # Obtain some additional information from the error headers

            # If the error header is empty
            # Probably unnecessary, but good to check
            if not error.headers:

                # Something probably went very wrong if this block is activated.
                self.logger.debug("HTTP error header was empty.")

            # Else, if the header isn't empty
            else:

                for key, value in error.headers.items():
                    self.logger.debug("HTTP header: %s: %s", key, value)

                # Obtain the 'Retry-After' header
                retry = error.headers.get("Retry-After")

                # If there is a Retry-After header
                if retry is not None:

                    self.logger.debug("Found Retry-After header.")

                    self.retry_after = float(retry)

                    self.logger.warning(
                        "---> Received a wait command from the server. "
                        "Increasing wait time to the recommended %s seconds ...",
                        self.retry_after,
                    )

                # Catch 429 error codes that do not have a Retry-after header
                elif (retry is None) and (error.code == 429):

                    self.retry_after = 90.0 * attempt
                    self.logger.warning(
                        "Did not find a Retry-After command despite being a 429 error. "
                        "Increasing wait time to %s seconds ...",
                        self.retry_after,
                    )

                # Else, if there are headers but no retry-after header
                else:

                    self.logger.debug("Did not find a Retry-After header.")

        # Otherwise, raise an error
        else:

            self.logger.critical("HTTP error code %s: %s\n", error.code, error.reason)

            if error.headers:
                for key, value in error.headers.items():
                    self.logger.debug("HTTP header: %s: %s", key, value)
            raise RuntimeError("Received non-retry HTTP error code.")

    def url_errorcheck(self, error: urllib.error.URLError, attempt: int) -> None:
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
                "Connection error code %s on attempt %s of %s.\n"
                "         Updating certificate and retrying in %s seconds ...",
                error.reason,
                attempt,
                self.MAX_RETRIES,
                self.wait_time,
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
                "Current certifi version: %s | Recommended: >2026.01.04.",
                certifi.__version__,
            )
            self.logger.warning(
                "This issue should be fixed before rerunning the script."
            )

        # # Add a CLI option to skip verification entirely?
        # Do not do it by default, and ensure the users are warned of the risk
        #     (e.g. by forcing to confirm a prompt)
        # Leaving here in case it is added later.
        # self.logger.warning(
        #     f"Disabling verification and retrying in {self.wait_time} seconds ..."
        # )

        # # Disable verification
        # ssl._create_default_https_context = ssl._create_unverified_context

        # Otherwise, if it is any other type of URL error, raise an error
        else:

            self.logger.critical("Connection error: %s\n", error.reason)
            raise RuntimeError("Unable to connect.")
