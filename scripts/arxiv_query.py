# Import functions
from .utils import pretty_sleep

# Import libraries
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import certifi
import logging
import ssl

# # Import libraries used to test API connections and errors
# from email.message import Message
# from unittest.mock import patch


def http_errorcheck(
    logger: logging.Logger,
    error: urllib.error.HTTPError,
    attempt: int,
    max_retries: int,
) -> float | None:
    """Handles the HTTP errors that could arise.

    inputs
    ------
    logger      : The logger object.
    error       : Error returned from the connection attempt.
    attempt     : Attempt number.
    max_retries : Maximum number of attempts allowed.
    wait_time   : Time to wait between attempts.

    returns
    -------
    retry_after : Holds the time that the query attempts should be paused for, if there is a request to pause. Otherwise, it is None.
    """

    # Define some error codes. If one of these, we will retry
    retry_codes = (
        408,  # Request timeout
        429,  # Too many requests
        500,  # Internal server error. Also caused by malformed urls in the request.
        502,  # Bad gateway
        503,  # Service unavailable (i.e. overloaded or down)
        504,  # Gateway timeout
    )

    # Set retry_after to None. If a Retry-After command is given by the server, it will be updated
    retry_after = None

    # If the HTTP error is in our list of codes that tell us to retry
    if error.code in retry_codes:

        logger.warning(
            "HTTP error code {:} on attempt {:} of {:}.".format(
                error.code, attempt, max_retries
            )
        )

        # Obtain some additional information. This will increase the wait time, or is used for debug

        # If there are no headers
        if error.headers is None:

            logger.debug("No header found.")

        # Else, if there are headers
        else:

            for key, value in error.headers.items():
                logger.debug("HTTP header: {:}: {:}".format(key, value))

            # If there is a Retry-After header
            if error.headers["Retry-After"] is not None:

                logger.debug("Found Retry-After header.")
                retry_after = float(error.headers["Retry-After"])

                logger.warning(
                    "---> Received a wait command from the server. Increasing wait time to the recommended {:} seconds ...".format(
                        retry_after
                    )
                )

            # Catch 429 error codes that do not have a Retry-after header
            elif (error.headers["Retry-After"] is None) and (error.code == 429):

                retry_after = 90 * attempt
                logger.warning(
                    "Did not find a Retry-After command despite being a 429 error. Increasing wait time to {:} seconds ...".format(
                        retry_after
                    )
                )

            # Else, if there are headers but no retry-after header
            else:

                logger.debug("Did not find a Retry-After header.")

    # Otherwise, raise an error
    else:

        logger.critical("HTTP error code {:}: {:}\n".format(error.code, error.reason))
        for key, value in error.headers.items():
            logger.debug("HTTP header: {:}: {:}".format(key, value))
        raise

    return retry_after


def url_errorcheck(
    logger: logging.Logger,
    error: urllib.error.URLError,
    cert_error_bool: bool,
    wait_time: float,
) -> tuple[ssl.SSLContext | None, bool]:
    """Handles the URL errors that could arise.

    inputs
    ------
    logger          : The logger object.
    error           : Error returned from the connection attempt.
    cert_error_bool : True if the error was caused by a certification error, False otherwise.
    wait_time       : Time to wait between attempts.

    returns
    -------
    ssl_context     : New SSLContext to use for the connection if the error is caused by a certification error, otherwise None.
    cert_error_bool : True if the error was a certification error, otherwise False.
    """

    # If it is a certificate verification error, and no certification error has occured before:
    if isinstance(error.reason, ssl.SSLCertVerificationError) and not cert_error_bool:

        # Warn the user that verification failed
        logger.warning(
            "Connection error: {:}. Updating certificate and retrying in {:} seconds ...".format(
                error.reason, wait_time
            )
        )

        # Try verifying
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        # Set the certification error flag to True
        cert_error_bool = True

    # If it is a certificate verification error, and we have tried certifying earlier:
    elif isinstance(error.reason, ssl.SSLCertVerificationError) and cert_error_bool:

        # Warn the user that we are disabling verification
        logger.warning("Verification still failed.")
        logger.info(
            "This could potentially be an issue with your OS and its trust store, or the certifi package version."
        )
        logger.info(
            "Current certifi version: {:}. Recommended: >2026.01.04.".format(
                certifi.__version__
            )
        )
        logger.info("This issue should be fixed before rerunning the script.")
        logger.warning(
            "Disabling verification and retrying in {:} seconds ...".format(wait_time)
        )

        # Disable verification
        ssl._create_default_https_context = ssl._create_unverified_context
        ssl_context = None

    # Otherwise, if it is any other type of URL error, raise an error
    else:

        logger.critical("Connection error: {:}\n".format(error.reason))
        raise

    return ssl_context, cert_error_bool


def arxiv_query(
    logger: logging.Logger, ssl_dict: dict, url: str, start_num: int, blocksize: int
) -> tuple[ET.Element, dict]:
    """Queries the arXiv servers for the papers.
    Will catch errors and attempt retries (if the error allows retries).

    inputs
    ------
    logger    : The logger object.
    ssl_dict  : Contains None, False if there have been no certification errors. Contains ssl_context, True if ther has been a cert. error.
    url       : URL for the arXiv API. Should be formatted to include dates/etc, except for the start_num and blocksize.
    start_num : Starting paper number for the search query.
    blocksize : Number of papers to download in the search query.

    outputs
    -------
    parsed_xml_data : XML data from the arXiv query.
    ssl_context     : Contains the SSLContext and a bool to say if a certificate error has been encountered.
    """

    # Define some values for retry attempts. These are magic values and kept from the users.
    # These can be altered as arXiv does not specify values. However, these values are pretty typical so it is best to leave them.
    max_retries = 5  # Maximum number of retried connections
    wait_time = 6  # Seconds to wait. Double the courtesy value
    backoff = 2  # Factor to increase the wait_time after a failure
    timeout = 30  # Seconds to wait before a timeout

    # Extract info on certification errors
    ssl_context = ssl_dict["ssl_context"]
    cert_error_bool = ssl_dict["ssl_preverr"]

    # If an error gives a "Retry-After" demand, we will wait for that time instead of the exponential backoff
    # Initialise to None
    retry_after = None

    # Format the last two fields in the url
    formatted_url = url.format(start_num=start_num, blocksize=blocksize)

    # Query the server
    for attempt in range(
        1, max_retries + 1
    ):  # 1 -> max_retries+1 so that we start counting attempts at 1 in the logger messages

        logger.debug("Attempting connection to:\n       {:}".format(formatted_url))

        try:

            # # Test error handling
            # # Indent the "attempt to connect to arXiv" to "return parsed_xml_date" lines by one additional indentation

            # # HTTP ERRORS

            # # http error with a random code and no header
            # err = urllib.error.HTTPError(url=None, code=47, msg="fake error that should exit", hdrs=None, fp=None)
            # with patch("urllib.request.urlopen", side_effect=err):

            # # http repeating error code with no header
            # time.sleep(4)
            # err = urllib.error.HTTPError(url=None, code=408, msg="non-repeating code", hdrs=None, fp=None)
            # with patch("urllib.request.urlopen", side_effect=err):

            # # http non-repeating error code with a useless header
            # headers = Message()
            # headers["blank"] = 'nothing'
            # err = urllib.error.HTTPError(url=None, code=408, msg="non-repeating code", hdrs=headers, fp=None)
            # with patch("urllib.request.urlopen", side_effect=err):

            # # http error with a retry-after header
            # headers = Message()
            # headers["Retry-After"] = 40
            # err = urllib.error.HTTPError(url=None, code=429, msg="repeating code", hdrs=headers, fp=None)
            # with patch("urllib.request.urlopen", side_effect=err):

            # # URL ERRORS

            # # non-Verification errors
            # with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("DNS fail")):

            # # Verification errors
            # err = urllib.error.URLError(ssl.SSLCertVerificationError("certificate verify failed: unable to get local issuer certificate"))
            # with patch("urllib.request.urlopen", side_effect=err):

            # Attempt to connect to arXiv
            with urllib.request.urlopen(
                formatted_url, timeout=timeout, context=ssl_context
            ) as f:

                logger.debug("...Connection successful")

                # Read the data
                xml_data = f.read()

                # Parse the xml
                # if ET.fromstring(xml_data) is None:
                #     raise
                # else:
                parsed_xml_root = ET.fromstring(xml_data)

                return parsed_xml_root, ssl_dict

        # If there is a HTTP error:
        except urllib.error.HTTPError as error:

            retry_after = http_errorcheck(logger, error, attempt, max_retries)

        # If there is a URL error:
        except urllib.error.URLError as error:

            ssl_context, cert_error_bool = url_errorcheck(
                logger, error, cert_error_bool, wait_time
            )
            ssl_dict["ssl_context"] = ssl_context
            ssl_dict["ssl_preverr"] = cert_error_bool

        # If there is a timeout error:
        except TimeoutError:

            retry_after = 60

            logger.warning(
                "Timeout Error. Retrying in {:} seconds ...".format(retry_after)
            )

        # If there is an error parsing the xml, raise an error
        except ET.ParseError as error:

            # # Print a warning and retry
            # logger.warning("XML parsing error on attempt {:} of {:}. Retrying in {:} seconds ...".format(attempt, max_retries, wait_time))
            # # May need to add a way to warn and skip. This error shouldn't occur, but potenially could be due to malformed paper entries?
            # # It is rare error and difficult to know the cause (has only ever occured in historical searches when testing)

            # # For now, raise an error
            logger.critical("XML parsing error. Please upload log file to github.\n")
            logger.debug(error)
            raise

        # If there have been too many retries, raise an error
        if attempt == max_retries:

            logger.critical(
                "Maximum retries attempted. arXiv query failed.\n          Review connection error codes before trying again.\n"
            )
            raise

        # If there was a Retry-After command, replace the wait time
        if retry_after is not None:

            wait_time = retry_after

        # Sleep before retrying
        pretty_sleep(logger, wait_time)

        # If there was no retry after demand, increase the wait time for the next attempt
        if retry_after is None:

            wait_time *= backoff

    # Raise an error if the function reaches here somehow
    logger.critical("Something went wrong...?\n")
    raise


## Format of the xml outputs from the arXiv API:
"""Example arXiv API pull:
<ns0:feed xmlns:ns0="http://www.w3.org/2005/Atom" xmlns:ns1="http://a9.com/-/spec/opensearch/1.1/" xmlns:ns2="http://arxiv.org/schemas/atom">
  <ns0:id>https://arxiv.org/api/RdGiJmCzUo9LqFSmMy0zaOoHqng</ns0:id>
  <ns0:title>arXiv Query: search_query=submittedDate:"{start_date}1900 TO {end_date}1900" AND cat:{cat_urlstring}&amp;id_list=&amp;start={ii}&amp;max_results={interval}</ns0:title>
  <ns0:updated>YYYY-mm-ddTHH:MM:SSZ</ns0:updated>
  <ns0:link href="{formatted_url}" type="application/atom+xml" />
  <ns1:itemsPerPage>{interval}</ns1:itemsPerPage>
  <ns1:totalResults>{max_num}}</ns1:totalResults>
  <ns1:startIndex>{ii}}</ns1:startIndex>
  <ns0:entry>
    [paper entry 0]
  </ns0:entry>
  <ns0:entry>
    [paper entry 1]
  </ns0:entry>
  ...
</ns0:feed>
"""

"""Example paper entry:
  <ns0:entry>
    <ns0:id>http://arxiv.org/abs/{arXiv:ID}</ns0:id>
    <ns0:title>Title text</ns0:title>
    <ns0:updated>YYYY-mm-ddTHH:MM:SSZ</ns0:updated>
    <ns0:link href="https://arxiv.org/abs/{arXiv:ID}" rel="alternate" type="text/html" />
    <ns0:link href="https://arxiv.org/pdf/{arXiv:ID}" rel="related" type="application/pdf" title="pdf" />
    <ns0:summary>Abstract text</ns0:summary>
    <ns0:category term="cat0" scheme="http://arxiv.org/schemas/atom" />
    <ns0:category term="cat1" scheme="http://arxiv.org/schemas/atom" />
    ...
    <ns0:published>2026-02-06T18:51:45Z</ns0:published>
    <ns2:comment>Comment text</ns2:comment>
    <ns2:primary_category term="cat0" />
    <ns0:author>
      <ns0:name>example name 0</ns0:name>
    </ns0:author>
    <ns0:author>
      <ns0:name>example name 1</ns0:name>
    </ns0:author>
    ...
  </ns0:entry>
"""
