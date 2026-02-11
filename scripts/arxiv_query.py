# Import libraries
from scripts.string_handling import normalise_string
from scripts.utils           import progress_bar, clear_progress_bar

import xml.etree.ElementTree as ET
import pandas                as pd
import numpy                 as np

import urllib.request
import certifi
import time
import ssl
import sys

# # # Import libraries used to test API connections and errors
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

def arxiv_query(url, start_date, end_date, cats, start_num, end_num, logger):
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
    end_num    : int
        Ending paper number for the search query.

    outputs
    -------
    parsed_xml_data : Element
        XML data from the arXiv query.

    TO-DO:
    1) If the xml was successfully downloaded and parsed, save it to a file. Also clear this file if the script finishes successfully.
    2) If all of the retries fail, write a file that can be used to restart the search as if nothing occured by rerunning the script.
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
                   500, # Internal server error
                   502, # Bad gateway
                   503, # Service unavailable (i.e. overloaded or down)
                   504, # Gateway timeout
                  )

    # Set default ssl_context and define a flag to check if a certification error was raiseed previously
    ssl_context     = None
    cert_error_bool = False

    # Format the url
    formatted_url = url.format(start_year  = start_date.year,
                               start_month = start_date.month,
                               start_day   = start_date.day,
                               end_year    = end_date.year,
                               end_month   = end_date.month,
                               end_day     = end_date.day,
                               cats        = cats,
                               start_num   = start_num,
                               end_num     = end_num)
    
    # Query the server
    for attempt in range(1, max_retries + 1): # 1 -> max_retries+1 so that we start counting attempts at 1 in the logger messages

        try:

            # # Test error handling
            # # Indent the "attempt to connect to arXiv" to "return parsed_xml_date" lines by one additional indentation
            # # HTTP ERRORS
            # err = urllib.error.HTTPError(url=None, code=504, msg="fake error that I made up", hdrs=None, fp=None)
            # with patch("urllib.request.urlopen", side_effect=err):
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

            # If the HTTP error is in our list of codes that tell us to retry
            if error.code in retry_codes:

                # Print a warning and retry
                clear_progress_bar()
                logger.warning("HTTP error code '{:}' on attempt {:} of {:}. Retrying in {:} seconds ...".format(error.code, attempt, max_retries, wait_time))

            # Otherwise, raise an error
            else:

                print("")
                logger.critical("HTTP error code '{:}': {:}\n".format(error.code, error.reason))
                raise

        # If there is a URL error:
        except urllib.error.URLError as error:

            # If it is a certificate verification error, and no certification error has occured before:
            if isinstance(error.reason, ssl.SSLCertVerificationError) and not cert_error_bool:

                # Warn the user that verification failed
                clear_progress_bar()
                logger.warning("Connection error: {:}. Updating certificate and retrying in {:} seconds ...".format(error.reason, wait_time))

                # Try verifying
                ssl_context = ssl.create_default_context(cafile=certifi.where())

                # Set the certification error flag to True
                cert_error_bool = True

            # If it is a certificate verification error, and we have tried certifying earlier:
            elif isinstance(error.reason, ssl.SSLCertVerificationError) and cert_error_bool:

                # Warn the user that we are disabling verification
                clear_progress_bar()
                logger.warning("Verification still failed.")
                logger.info("This could potentially be an issue with your OS and its trust store, or the certifi package version.")
                logger.info("Current certifi version: {:}. Recommended: >2026.01.04.".format(certifi.__version__))
                logger.info("This issue should be fixed before rerunning the script.")
                logger.warning("Disabling verification and retrying in {:} seconds ...".format(wait_time))

                # Disable verification
                ssl._create_default_https_context = ssl._create_unverified_context

            # Otherwise, if it is any other type of URL error, raise an error
            else:

                print("")
                logger.critical("Connection error: {:}\n".format(error.reason))
                raise

        # If there is an error parsing the xml, raise an error
        except ET.ParseError as error:

            # # Print a warning and retry
            # clear_progress_bar()
            # logger.warning("XML parsing error on attempt {:} of {:}. Retrying in {:} seconds ...".format(attempt, max_retries, wait_time))
            # # May need to add a way to warn and skip. This error shouldn't occur, but potenially could be due to malformed paper entries?
            # # It is rare error and difficult to know the cause (has only ever occured in historical searches when testing)
            
            # # For now, raise an error
            print("")
            logger.critical("XML parsing error.\n")
            raise

        # If there have been too many retries, raise an error
        if attempt == max_retries:

            print("")
            logger.critical("Maximum retries attempted. arXiv query failed.\n")
            raise

        # Sleep before retrying
        logger.debug("Sleeping for {:} seconds".format(wait_time))
        time.sleep(wait_time)

        # Increase the wait time for thee next atteept
        wait_time *= backoff
    
    # Raise an error if the function reaches here somehow
    print("")
    logger.critical("Something went wrong...?\n")
    raise

def arxiv_initial_pull(ns, url, start_date, end_date, cats, sleeptimer, blocksize, logger):
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

    outputs
    -------
    max_num : int
        Number of papers that were found in the categories of interest.
    """

    logger.info("Obtaining arXiv info. Estimated time: {:d} seconds".format(sleeptimer)) # Always a single sleep

    # Display a progress bar
    progress_bar(0, 1, 3)

    # Perform the query
    xml_data = arxiv_query(url,
                           start_date,
                           end_date,
                           cats,
                           0,
                           1,
                           logger)
    
    max_num = int(xml_data.find("opensearch:totalResults", ns).text)
    
    progress_bar(1, 1)

    arxiv_errorcheck(max_num, sleeptimer, blocksize, logger)

    return max_num

def extract_paper(ns, xml):
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

        papers.append(paper)

    return papers

def arxiv_search(ns, url, start_date, end_date, cats, max_num, sleeptimer, blocksize, logger):
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

    outputs
    -------
    df : pandas.DataFrame
        Contains all papers and their information.
    """

    entries = []
    logger.info("Searching for papers. Estimated time: {:d} seconds".format(-sleeptimer*(max_num//-blocksize)))
    for ii in range(0, max_num, blocksize):

        # Compute the progress of the loop
        if ii+blocksize > max_num:
            remaining_steps = 1
            search_endnum   = max_num
        else:
            remaining_steps = -((max_num-ii)//-blocksize)
            search_endnum   = ii + blocksize

        # Print the progress bar
        progress_bar(ii, max_num, remaining_steps * sleeptimer)
        # Sleep before the query so that there is no dead time on the last query. Also need to sleep here as we do not wait after the initial API call
        time.sleep(sleeptimer)

        # Query the API
        parsed_xml = arxiv_query(url,
                                 start_date,
                                 end_date,
                                 cats,
                                 ii,
                                 search_endnum,
                                 logger)
        
        entries.extend(extract_paper(ns, parsed_xml))

    progress_bar(max_num, max_num)

    # Place into a dataframe
    df = pd.DataFrame( entries )

    # Drop duplicate papers, if they exist
    df.drop_duplicates(subset="arXiv Number", inplace=True, ignore_index=True)

    # Remove revised papers
    df.drop(df[df["Revised?"]==True].index, inplace=True)
    df.reset_index(drop=True, inplace=True)

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