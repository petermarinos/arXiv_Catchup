# Import libraries
from scripts.string_handling import normalise_string
from scripts.output          import write_xml
from scripts.utils           import progress_bar, clear_progress_bar

import xml.etree.ElementTree as ET
import pandas                as pd
import numpy                 as np

import urllib.request
import certifi
import time
import ssl
import sys
import os

# # Import libraries used to test API connections and errors
# from email.message import Message
# from unittest.mock import patch

def arxiv_errorcheck(max_num, sleep_timer, blocksize, logger):
    """Runs some error checks on the results of the arXiv API pull.

    inputs
    ------
    max_num     : int
        Number of papers in the search.
    sleep_timer : float
        Time between searches.
    blocksize   : int
        Number of papers returned in each search.
    logger      : RootLogger
        The logger object
    """

    # If no papers were found in the search, raise an error
    # This should catch deferred mailings
    if max_num == 0:
        logger.critical("There were no papers submitted to the arXiv.\n          Refine search dates and/or categories and check for deferred mailings:\n          https://info.arxiv.org/help/availability.html\n")
        raise

    # If there are too many papers then there can be issues with the arXiv API.
    # While the API will likely return an error, catch it here as well just in case
    if max_num >= 30000:
        
        logger.critical("Number of papers is too large. Refine search dates and/or categories.\n")
        raise
    
    # Compute the time it will take to download all papers
    time_to_search_minutes = max_num*sleep_timer/(blocksize*60)
    
    # Print a warning if it is going to take a long time
    if 1 <= time_to_search_minutes < 5:

        logger.warning("There are {:d} papers. The search will take {:.1f} minutes.".format(max_num, time_to_search_minutes))

    # Prompt the user if it is going to take a really long time.
    elif time_to_search_minutes >= 5:

        user_prompt = input("There are {:d} papers. The search will take {:.1f} minutes. Continue? [y/N]: ".format(max_num,time_to_search_minutes)).strip().lower()

        # If they want to continue, do nothing.
        # If they do not want to continue, end the search
        if user_prompt != "y":

            sys.exit("Cancelling the search. Reduce search window to decrease the number of results.")

    return

def http_errorcheck(error, retry_codes, attempt, max_retries, wait_time, logger):
    """Handles the HTTP errors that could arise.
    NOTE: Only occurs within functions that include a progress bar.

    inputs
    ------
    error       : urllib.error.HTTPError
        Error returned from the connection attempt.
    retry_codes : tuple
        Codes that allow a re-attempt at connection.
    attempt     : int
        Attempt number.
    max_retries : int
        Maximum number of attempts allowed.
    wait_time   : float
        Time to wait between attempts.
    logger      : RootLogger
        The logger object

    returns
    -------
    retry_after : None or float
        Holds the time that the query attempts should be paused for, if there is a request to pause. Otherwise, it is None.
    """

    # If the HTTP error is in our list of codes that tell us to retry
    if error.code in retry_codes:

        # Print a warning
        clear_progress_bar(logger, 30)
        logger.warning("HTTP error code '{:}' on attempt {:} of {:}. Retrying in {:} seconds ...".format(error.code, attempt, max_retries, wait_time))

        # Obtain some additional information. This will increase the wait time, or is used for debug

        # If there are no headers
        if error.headers is None:

            clear_progress_bar(logger, 10)
            logger.debug("No header found")
            retry_after = None

        # Else, if there are headers
        else:

            clear_progress_bar(logger, 10)
            # Print the headers if in debug mode
            for key, value in error.headers.items():
                logger.debug("HTTP header: {:}: {:}".format(key, value))

            # If there is a Retry-After header
            if error.headers["Retry-After"] is not None:

                clear_progress_bar(logger, 10)
                logger.debug("Found Retry-After header.")
                retry_after = error.headers["Retry-After"]
                wait_time = retry_after

            # Else, if there are headers but no retry-after header
            else:

                clear_progress_bar(logger, 10)
                logger.debug("Did not find a Retry-After header.")
                retry_after = None

    # Otherwise, raise an error
    else:

        # print("")
        clear_progress_bar(logger, 50)
        logger.critical("HTTP error code '{:}': {:}\n".format(error.code, error.reason))
        raise

    return retry_after

def url_errorcheck(error, cert_error_bool, wait_time, logger):
    """Handles the URL errors that could arise.
    NOTE: Only occurs within functions that include a progress bar.

    inputs
    ------
    error           : urllib.error.URLError
        Error returned from the connection attempt.
    cert_error_bool : bool
        True if the error was caused by a certification error, False otherwise.
    wait_time       : float
        Time to wait between attempts.
    logger          : RootLogger
        The logger object

    returns
    -------
    ssl_context     : None or SSLContext
        New SSLContext to use for the connection if the error is caused by a certification error, otherwise None.
    cert_error_bool : bool
        True if the error was a certification error, otherwise False.
    """

    # If it is a certificate verification error, and no certification error has occured before:
    if isinstance(error.reason, ssl.SSLCertVerificationError) and not cert_error_bool:

        # Warn the user that verification failed
        clear_progress_bar(logger, 30)
        logger.warning("Connection error: {:}. Updating certificate and retrying in {:} seconds ...".format(error.reason, wait_time))

        # Try verifying
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        # Set the certification error flag to True
        cert_error_bool = True

    # If it is a certificate verification error, and we have tried certifying earlier:
    elif isinstance(error.reason, ssl.SSLCertVerificationError) and cert_error_bool:

        # Warn the user that we are disabling verification
        clear_progress_bar(logger, 30)
        logger.warning("Verification still failed.")
        clear_progress_bar(logger, 20)
        logger.info("This could potentially be an issue with your OS and its trust store, or the certifi package version.")
        logger.info("Current certifi version: {:}. Recommended: >2026.01.04.".format(certifi.__version__))
        logger.info("This issue should be fixed before rerunning the script.")
        logger.warning("Disabling verification and retrying in {:} seconds ...".format(wait_time))

        # Disable verification
        ssl._create_default_https_context = ssl._create_unverified_context
        ssl_context                       = None

    # Otherwise, if it is any other type of URL error, raise an error
    else:

        clear_progress_bar(logger, 50)
        logger.critical("Connection error: {:}\n".format(error.reason))
        raise

    return ssl_context, cert_error_bool

def arxiv_query(url, start_date, end_date, cats, start_num, blocksize, logger):
    """Queries the arXiv API.
    Will catch errors and attempt retries.

    inputs
    ------
    url        : str
        URL for the arXiv API.
    start_date : datetime.date
        Start date for the search.
    end_date   : datetime.date
        End date for the search.
    cats       : str
        Categories that will be searched over (must be formatted for the search).
    start_num  : int
        Starting paper number for the search query.
    blocksize  : int
        Number of papers to download in the search query.
    logger     : RootLogger
        The logger object

    outputs
    -------
    parsed_xml_data : Element
        XML data from the arXiv query.
    """

    # Define some values for retry attempts. These are magic values and kept from the users.
    # Do not alter these
    max_retries = 5  # Maximum number of retried connections
    wait_time   = 6  # Seconds to wait. Double the courtesy value
    backoff     = 2  # Factor to increase the wait_time after a failure
    timeout     = 30 # Seconds to wait before a timeout
    retry_codes = (
                   408, # Request timeout
                   429, # Too many requests
                   500, # Internal server error. Also caused by malformed urls in the request.
                   502, # Bad gateway
                   503, # Service unavailable (i.e. overloaded or down)
                   504, # Gateway timeout
                  )

    # Set default ssl_context and define a flag to check if a certification error was raised previously
    ssl_context     = None
    cert_error_bool = False

    # If an error gives a "Retry-After" demand, we will wait for that time instead of the exponential backoff
    # Initialise to None
    retry_after = None

    # Format the url
    formatted_url = url.format(start_year  = start_date.year,
                               start_month = start_date.month,
                               start_day   = start_date.day,
                               end_year    = end_date.year,
                               end_month   = end_date.month,
                               end_day     = end_date.day,
                               cats        = cats,
                               start_num   = start_num,
                               blocksize   = blocksize)
    
    clear_progress_bar(logger, 10)
    logger.debug("Connecting to:\n       {:}".format(formatted_url))
    
    # Query the server
    for attempt in range(1, max_retries + 1): # 1 -> max_retries+1 so that we start counting attempts at 1 in the logger messages

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
            with urllib.request.urlopen(formatted_url, timeout=timeout, context=ssl_context) as f:

                # Read the data
                xml_data = f.read()

                # Parse the xml
                parsed_xml_data = ET.fromstring(xml_data)

                return parsed_xml_data
                
        # If there is a HTTP error:
        except urllib.error.HTTPError as error:

            retry_after = http_errorcheck(error, retry_codes, attempt, max_retries, wait_time, logger)

        # If there is a URL error:
        except urllib.error.URLError as error:

            ssl_context, cert_error_bool = url_errorcheck(error, cert_error_bool, wait_time, logger)

        # If there is an error parsing the xml, raise an error
        except ET.ParseError as error:

            # # Print a warning and retry
            # clear_progress_bar()
            # logger.warning("XML parsing error on attempt {:} of {:}. Retrying in {:} seconds ...".format(attempt, max_retries, wait_time))
            # # May need to add a way to warn and skip. This error shouldn't occur, but potenially could be due to malformed paper entries?
            # # It is rare error and difficult to know the cause (has only ever occured in historical searches when testing)
            
            # # For now, raise an error
            clear_progress_bar(logger, 50)
            logger.critical("XML parsing error.\n")
            raise

        # If there have been too many retries, raise an error
        if attempt == max_retries:

            clear_progress_bar(logger, 50)
            logger.critical("Maximum retries attempted. arXiv query failed.\n          Review connection error codes before trying again.\n")
            raise

        # Sleep before retrying
        clear_progress_bar(logger, 10)
        logger.debug("Sleeping for {:} seconds ...".format(wait_time))
        time.sleep(wait_time)

        # If there was no retry after demand, increase the wait time for the next attempt
        if retry_after is None:
            
            wait_time *= backoff
    
    # Raise an error if the function reaches here somehow
    clear_progress_bar(logger, 50)
    logger.critical("Something went wrong...?\n")
    raise

def arxiv_initial_pull(ns, url, start_date, end_date, cats, sleeptimer, blocksize, filename_xml, logger):
    """Performs the initial query to obtain important run information.

    inputs
    ------
    url        : str
        URL for the arXiv API.
    start_date : datetime.date
        Start date for the search.
    end_date   : datetime.date
        End date for the search.
    cats       : str
        Categories that will be searched over (must be formatted for the search).
    sleeptimer : float
        Time in seconds to wait between searches.
    blocksize  : int
        Number of papers to return from the search.
    searchxml   : str
        Path+filename of the `search.xml` file, that contains the xml of the initial search.
    logger      : RootLogger
        The logger object

    outputs
    -------
    max_num : int
        Number of papers that were found in the categories of interest.
    """

    # Search for xml file. If found, load it
    if os.path.exists(filename_xml):
        
        logger.info("Found an xml file: {:}".format(filename_xml))
        logger.info("Continuing from the previous failed run.")

        # Load the file
        xml_data = ET.parse(filename_xml)

    # Otherwise, search the arXiv
    else:

        logger.info("Obtaining arXiv info ...")

        # # Display a progress bar
        # progress_bar(0, 1, 3)

        # Perform the query
        xml_data = arxiv_query(url,
                               start_date,
                               end_date,
                               cats,
                               0,
                               1,
                               logger)
        
        # Write the extracted xml to a file
        write_xml(filename_xml, ns, xml_data, logger, overwrite=True)
        
        # # Close the progress bar
        # progress_bar(1, 1)
    
    # Extract the total number of papers that were found
    max_num = int(xml_data.find("opensearch:totalResults", ns).text)

    arxiv_errorcheck(max_num, sleeptimer, blocksize, logger)

    return max_num

def extract_papers(ns, xml, logger):
    """

    inputs
    ------
    ns  : dict
        XML namespaces that arXiv uses.
    xml : Element
        XML data from the arXiv query.

    outputs
    -------
    papers : list
        All papers in the entry.
    """
    
    papers = []

    # Loop over the entries (papers) within the current search
    for entry in xml.findall("atom:entry", ns):

        # Previously, when parsing the emails, there would be 'revised' versions. I would skip them, and they typically had no abstract.
        # The search that is being used now specifically uses "submitted date" as the criteria for being included, so I think there will never be any revised papers or empty abstracts.
        # However, I have kept the relevant columns and error checks just in case.

        published_date = entry.find("atom:published", ns).text
        updated_date   = entry.find("atom:updated", ns).text

        author_list = [author.find("atom:name", ns).text for author in entry.findall("atom:author", ns)]

        # Place information in a dictionary
        paper = {
            "arXiv Number"    : entry.find("atom:id", ns).text.split("/")[-1],
            "Title"           : entry.find("atom:title", ns).text.strip(),
            "Authors"         : normalise_string( ", ".join(f"{author}" for author in author_list) ),
            "Revised?"        : updated_date > published_date,
            "Abstract"        : entry.find("atom:summary", ns).text.strip(),
            "url"             : entry.find("atom:id", ns).text.strip(),
            "Author Match"    : False,
            "IncWord Match"   : False,
            "ExcWord Match"   : False,
        }

        logger.debug("Found: "+entry.find("atom:id", ns).text.split("/")[-1])

        papers.append(paper)

    logger.debug("Found {:} papers for this search".format(len(papers)))

    return papers

def arxiv_search(ns, url, start_date, end_date, cats, max_num, sleeptimer, blocksize, filename_xml, logger):
    """Performs the initial query to obtain important run information.

    inputs
    ------
    ns         : dict
        XML namespaces that arXiv uses.
    url        : str
        URL for the arXiv API.
    start_date : datetime.date
        Start date for the search.
    end_date   : datetime.date
        End date for the search.
    cats       : str
        Categories that will be searched over (must be formatted for the search).
    max_num    : int
        Total number of papers found in the categories of interest.
    sleeptimer : float
        Time in seconds to wait between searches.
    blocksize  : int
        Number of papers to return from the search.
    logger     : RootLogger
        The logger object

    outputs
    -------
    df : pandas.DataFrame
        Contains all papers and their information.
    """

    # Initialise the list of entries
    entries = []

    # Search for xml file. If found, load it
    if os.path.exists(filename_xml):
        
        logger.info("Found an .xml file: {:}".format(filename_xml))
        logger.info("Continuing from the previous failed run.")

        # Load the file
        xml_data = ET.parse(filename_xml)

        # Extract the papers from the xml
        entries.extend(extract_papers(ns, xml_data, logger))

        # Print how many were found
        logger.info("Found {:} of {:} papers in the .xml file.".format(len(entries), max_num))

        # If less than the total, provide info that we are continuing the search
        if len(entries) < max_num:

            logger.info("Continuing the search.")

    # If the number of papers is less that the total, connect to arXiv
    if len(entries) < max_num:

        # Set the starting number
        start_num = len(entries)

        logger.debug("The number of papers found so far is: {:}".format(start_num))

        # Compute the estimated time
        est_time = -sleeptimer * ( ( max_num - start_num ) // -blocksize )

        # Compute the number of steps it will take
        # The time to complete depends almost entirely on the number of connections to arXiv and the number of sleeps -- the amount of data that is downloaded is minimal.
        num_steps = int( np.ceil(max_num/blocksize) * blocksize )

        # Search the arXiv
        logger.info("Searching for papers. Estimated time: {:d} seconds".format(est_time))
        for ii in range(start_num, max_num, blocksize):

            # Compute the progress of the loop
            if ii+blocksize > max_num:
                remaining_steps = 1
                search_interval = max_num - ii
                search_endnum   = max_num
            else:
                remaining_steps = -((max_num-ii)//-blocksize)
                search_interval = blocksize
                search_endnum   = ii + blocksize

            logger.debug("Remaining steps: {:}".format(remaining_steps))
            logger.debug("Starting number: {:}".format(ii))
            logger.debug("Ending number:   {:}".format(search_endnum))

            # Print the progress bar
            progress_bar(ii, num_steps, remaining_steps * sleeptimer)
            # Sleep before the query so that there is no dead time on the last query. Also need to sleep here as we do not wait after the initial API call
            clear_progress_bar(logger, 10)
            logger.debug("Sleeping for {:} seconds ...".format(sleeptimer))
            time.sleep(sleeptimer)

            # Query the API
            parsed_xml = arxiv_query(url,
                                    start_date,
                                    end_date,
                                    cats,
                                    ii,
                                    search_interval,
                                    logger)
            
            # Write the xml to a file
            write_xml(filename_xml, ns, parsed_xml, logger)
            
            # Extract the paper from the xml
            entries.extend(extract_papers(ns, parsed_xml, logger))

        # Close the progress bar
        progress_bar(max_num, max_num)

    # Double check that we found the correct number of papers
    if len(entries) != max_num:

        logger.error("Found {:} papers (expected {:}).".format(len(entries), max_num))

    else:

        logger.debug("Found the expected number of papers.")

    # Place all entries into a dataframe
    df = pd.DataFrame( entries )

    logger.debug("Removing duplicates and revised papers.")

    # Drop duplicate papers, if they exist
    df.drop_duplicates(subset="arXiv Number", inplace=True, ignore_index=True)
    num_dup = max_num - len(df)
    logger.debug("Dropped {:} duplicate entries.".format(num_dup))

    # Remove revised papers
    df.drop(df[df["Revised?"]==True].index, inplace=True)
    df.reset_index(drop=True, inplace=True)
    num_rev = ( max_num - num_dup ) - len(df)
    logger.debug("Dropped {:} revised papers.".format(num_rev))

    return df

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