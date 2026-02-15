# Import functions
from scripts.string_handling import normalise_string
from scripts.file_io         import write_xml
from scripts.utils           import progress_bar, delete_file

# Import libraries
import xml.etree.ElementTree as ET
import pandas                as pd
import numpy                 as np
import urllib.request
import certifi
import time
import ssl
import sys
import os
import re

# # Import libraries used to test API connections and errors
# from email.message import Message
# from unittest.mock import patch

def arxiv_errorcheck(self):
    """Runs some error checks on the results of the initial arXiv API pull (i.e. the one that collects some basic information).

    inputs
    ------
    self : Papers object
    """

    # If no papers were found in the search, raise an error
    # This should catch deferred mailings
    if self.total_papers == 0:
        self.logger.critical("There were no papers submitted to the arXiv.\n          Refine search dates and/or categories and check for deferred mailings:\n          https://info.arxiv.org/help/availability.html\n")
        raise

    # If there are too many papers then there can be issues with the arXiv API.
    # While the API will likely return an error, catch it here as well just in case
    if self.total_papers >= 30000:
        
        self.logger.critical("Number of papers is too large. Refine search dates and/or categories.\n")
        raise
    
    # Compute the time it will take to download all papers
    time_to_search_minutes = self.total_papers * self.arxiv_const.sleeptimer_search / ( self.arxiv_const.search_blocksize * 60 )
    
    # Print a warning if it is going to take a long time
    if 1 <= time_to_search_minutes < 5:

        self.logger.warning("There are {:d} papers. The search will take {:.1f} minutes.".format(self.total_papers, time_to_search_minutes))

    # Prompt the user if it is going to take a really long time.
    elif time_to_search_minutes >= 5:

        user_prompt = input("There are {:d} papers. The search will take {:.1f} minutes. Continue? [y/N]: ".format(self.total_papers, time_to_search_minutes)).strip().lower()

        # If they want to continue, do nothing.
        # If they do not want to continue, end the search
        if user_prompt != "y":

            # Delete the .xml file
            delete_file(self.paths["searchxml"], self.logger)

            # Exit
            sys.exit("Cancelling the search. Reduce search window to decrease the number of results.")

    return

def http_errorcheck(logger, error, attempt, max_retries, wait_time):
    """Handles the HTTP errors that could arise.

    inputs
    ------
    logger      : RootLogger
        The logger object
    error       : urllib.error.HTTPError
        Error returned from the connection attempt.
    attempt     : int
        Attempt number.
    max_retries : int
        Maximum number of attempts allowed.
    wait_time   : float
        Time to wait between attempts.

    returns
    -------
    retry_after : None or float
        Holds the time that the query attempts should be paused for, if there is a request to pause. Otherwise, it is None.
    """

    # Define some error codes. If one of these, we will retry
    retry_codes = (
                   408, # Request timeout
                   429, # Too many requests
                   500, # Internal server error. Also caused by malformed urls in the request.
                   502, # Bad gateway
                   503, # Service unavailable (i.e. overloaded or down)
                   504, # Gateway timeout
                  )

    # If the HTTP error is in our list of codes that tell us to retry
    if error.code in retry_codes:

        logger.warning("HTTP error code '{:}' on attempt {:} of {:}. Retrying in {:} seconds ...".format(error.code, attempt, max_retries, wait_time))

        # Obtain some additional information. This will increase the wait time, or is used for debug

        # If there are no headers
        if error.headers is None:

            logger.debug("No header found")
            retry_after = None

        # Else, if there are headers
        else:

            for key, value in error.headers.items():
                logger.debug("HTTP header: {:}: {:}".format(key, value))

            # If there is a Retry-After header
            if error.headers["Retry-After"] is not None:

                logger.debug("Found Retry-After header.")
                retry_after = error.headers["Retry-After"]
                wait_time = retry_after

            # Else, if there are headers but no retry-after header
            else:

                logger.debug("Did not find a Retry-After header.")
                retry_after = None

    # Otherwise, raise an error
    else:

        logger.critical("HTTP error code '{:}': {:}\n".format(error.code, error.reason))
        raise

    return retry_after

def url_errorcheck(logger, error, cert_error_bool, wait_time):
    """Handles the URL errors that could arise.

    inputs
    ------
    logger          : RootLogger
        The logger object
    error           : urllib.error.URLError
        Error returned from the connection attempt.
    cert_error_bool : bool
        True if the error was caused by a certification error, False otherwise.
    wait_time       : float
        Time to wait between attempts.

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
        logger.warning("Connection error: {:}. Updating certificate and retrying in {:} seconds ...".format(error.reason, wait_time))

        # Try verifying
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        # Set the certification error flag to True
        cert_error_bool = True

    # If it is a certificate verification error, and we have tried certifying earlier:
    elif isinstance(error.reason, ssl.SSLCertVerificationError) and cert_error_bool:

        # Warn the user that we are disabling verification
        logger.warning("Verification still failed.")
        logger.info("This could potentially be an issue with your OS and its trust store, or the certifi package version.")
        logger.info("Current certifi version: {:}. Recommended: >2026.01.04.".format(certifi.__version__))
        logger.info("This issue should be fixed before rerunning the script.")
        logger.warning("Disabling verification and retrying in {:} seconds ...".format(wait_time))

        # Disable verification
        ssl._create_default_https_context = ssl._create_unverified_context
        ssl_context                       = None

    # Otherwise, if it is any other type of URL error, raise an error
    else:

        logger.critical("Connection error: {:}\n".format(error.reason))
        raise

    return ssl_context, cert_error_bool

def arxiv_query(logger, url, start_num, blocksize):
    """Queries the arXiv servers for the papers.
    Will catch errors and attempt retries (if the error allows retries).

    inputs
    ------
    logger    : RootLogger
        The logger object
    url       : str
        URL for the arXiv API. Should be formatted to include dates/etc, except for the start_num and blocksize
    start_num : int
        Starting paper number for the search query.
    blocksize : int
        Number of papers to download in the search query.

    outputs
    -------
    parsed_xml_data : Element
        XML data from the arXiv query.
    """

    # Define some values for retry attempts. These are magic values and kept from the users.
    # These can be altered as arXiv does not specify values. However, these values are pretty typical so it is best to leave them.
    max_retries = 5  # Maximum number of retried connections
    wait_time   = 6  # Seconds to wait. Double the courtesy value
    backoff     = 2  # Factor to increase the wait_time after a failure
    timeout     = 30 # Seconds to wait before a timeout

    # Set default ssl_context and define a flag to check if a certification error was raised previously
    ssl_context     = None
    cert_error_bool = False

    # If an error gives a "Retry-After" demand, we will wait for that time instead of the exponential backoff
    # Initialise to None
    retry_after = None

    # Format the last two fields in the url
    formatted_url = url.format(start_num = start_num,
                               blocksize = blocksize)
    
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

            retry_after = http_errorcheck(logger, error, attempt, max_retries, wait_time)

        # If there is a URL error:
        except urllib.error.URLError as error:

            ssl_context, cert_error_bool = url_errorcheck(logger, error, cert_error_bool, wait_time)

        # If there is an error parsing the xml, raise an error
        except ET.ParseError as error:

            # # Print a warning and retry
            # logger.warning("XML parsing error on attempt {:} of {:}. Retrying in {:} seconds ...".format(attempt, max_retries, wait_time))
            # # May need to add a way to warn and skip. This error shouldn't occur, but potenially could be due to malformed paper entries?
            # # It is rare error and difficult to know the cause (has only ever occured in historical searches when testing)
            
            # # For now, raise an error
            logger.critical("XML parsing error.\n")
            raise

        # If there have been too many retries, raise an error
        if attempt == max_retries:

            logger.critical("Maximum retries attempted. arXiv query failed.\n          Review connection error codes before trying again.\n")
            raise

        # Sleep before retrying
        logger.debug("Sleeping for {:} seconds ...".format(wait_time))
        time.sleep(wait_time)

        # If there was no retry after demand, increase the wait time for the next attempt
        if retry_after is None:
            
            wait_time *= backoff
    
    # Raise an error if the function reaches here somehow
    logger.critical("Something went wrong...?\n")
    raise

def arxiv_initial_pull(self):
    """Performs the initial query to obtain important run information.

    inputs
    ------
    self : Papers object

    outputs
    -------
    max_num : int
        Number of papers that were found in the categories of interest.
    """

    # Search for xml file. If found, load it
    if os.path.exists(self.paths["searchxml"]):
        
        self.logger.info("Found a .xml file: {:}".format(self.paths["searchxml"]))
        self.logger.info("Attempting to continue from the previous failed run.")

        # Load the file
        xml_data = ET.parse(self.paths["searchxml"])

        # Check the url from the loaded xml matches the current search url
        expected_url = self.arxiv_const.apiquery.format(start_num=0, blocksize=1)
        returned_url = xml_data.find("atom:link", self.arxiv_const.ns).attrib["href"]

        url_missmatch = ( expected_url != returned_url )
        if url_missmatch:
            self.logger.warning("The .xml file information does not match the current search. Discarding the file and re-connecting.")
            self.logger.debug("Expected: {:}".format(expected_url))
            self.logger.debug("Found:    {:}".format(returned_url))
            # Clear the .xml file
            delete_file(self.logger, self.paths["searchxml"])
        else:
            self.logger.debug("The .xml file information matches the current search. Continuing")

    # If there is no file, perform the search
    # NOTE: This is not an elif as the above if statement can delete the file. If the file is deleted, we want to be redownloaded. If the file never existed, we want to download. If the file existed and had the correct information, then this statement will not be activated anyway.
    if not os.path.exists(self.paths["searchxml"]):

        self.logger.info("Obtaining search information from the servers.")

        # Perform the query
        xml_data = arxiv_query(self.logger, self.arxiv_const.url, 0, 1)
        
        # Write the extracted xml to a file
        write_xml(self.logger, self.paths["searchxml"], xml_data, self.arxiv_const.ns, overwrite=True)
        
        self.logger.info("Search information successfully obtained from the arXiv servers!")
    
    # Extract the total number of papers that were found
    max_num = int(xml_data.find("opensearch:totalResults", self.arxiv_const.ns).text)

    return max_num

def extract_papers(logger, ns, xml_data):
    """Extracts the papers (and their information) from the results of the API query.

    inputs
    ------
    logger : RootLogger
        The logger object
    ns     : dict
        XML namespaces that arXiv uses.
    xml    : Element
        XML data from the arXiv query.

    outputs
    -------
    papers : list
        All papers in the entry.
    """
    
    papers = []

    # Loop over the entries (papers) within the current search
    for entry in xml_data.findall("atom:entry", ns):

        # Find the published and updated dates
        published_date = entry.find("atom:published", ns).text
        updated_date   = entry.find("atom:updated", ns).text

        # Find the arXiv numbers
        ID_number      = entry.find("atom:id", ns).text.split("/")[-1][:10]
        version_number = int( entry.find("atom:id", ns).text.split("/")[-1][11:] )

        # Extract the author list
        author_list = [author.find("atom:name", ns).text for author in entry.findall("atom:author", ns)]

        # Extract the title
        title          = entry.find("atom:title", ns).text.strip()
        title_numwords = len( re.findall(r'\w+', title) )

        # Extract the abstract
        abstract          = entry.find("atom:summary", ns).text.strip()
        abstract_numwords = len( re.findall(r'\w+', abstract) )

        # Place information in a dictionary
        paper = {
            # Extract information
            "arXiv Number"      : ID_number,
            "Title"             : title,
            "Authors"           : normalise_string( ", ".join(f"{author}" for author in author_list) ),
            "Revised?"          : (updated_date > published_date) or (version_number > 1),
            "Abstract"          : abstract,
            "url"               : entry.find("atom:id", ns).text.strip(),
            "Number of Authors" : len(author_list),
            "Number of Words"   : {"Title"    : title_numwords,
                                   "Abstract" : abstract_numwords},
            # Setup fields used for output
            # Authors
            "Found Authors"   : [],
            "Authors Matches" : 0,
            "Authors Score"   : 0.,
            # Number of words
            # Included words
            "Included Words Matches" : {"Title"    : 0,
                                        "Abstract" : 0,
                                        "Total"    : 0},
            "Included Words Score"   : {"Title"    : 0.,
                                        "Abstract" : 0.,
                                        "Total"    : 0.},
            # Excluded words
            "Excluded Words Matches" : {"Title"    : 0,
                                        "Abstract" : 0,
                                        "Total"    : 0},
            "Excluded Words Score"   : {"Title"    : 0.,
                                        "Abstract" : 0.,
                                        "Total"    : 0.},
            # Final score
            "Final Score"            : 0.,
        }

        logger.debug("Found: {:}, version {:}.".format(ID_number, version_number))
        logger.debug("       published on {:}, updated on {:}.".format(published_date, updated_date))
        logger.debug("       Revised? {:}".format((updated_date > published_date) or (version_number > 1)))

        papers.append(paper)

    logger.debug("Found {:} papers in this search block.".format(len(papers)))

    return papers

def arxiv_search(self):
    """Searches the arXiv for all papers that satisfy our criteria.

    inputs
    ------
    self : Papers object

    outputs
    -------
    df : pandas.DataFrame
        Contains all papers and their information.
    """

    # Initialise the list of entries
    entries = []

    # Search for xml file. If found, load it
    if os.path.exists(self.paths["papersxml"]):
        
        self.logger.info("Found an .xml file: {:}".format(self.paths["papersxml"]))
        self.logger.info("Continuing from the previous failed run.")

        # Load the file
        xml_data = ET.parse(self.paths["papersxml"])

        # Extract the papers from the xml
        entries.extend(extract_papers(self.logger, self.arxiv_const.ns, xml_data))

        # Print how many were found
        self.logger.info("Found {:} of {:} papers in the .xml file.".format(len(entries), self.total_papers))

        # Check the url from the loaded xml matches the current search url
        expected_url = self.arxiv_const.apiquery.format(start_num=0, blocksize=self.arxiv_const.search_blocksize)
        returned_url = xml_data.find("atom:link", self.arxiv_const.ns).attrib["href"]

        url_missmatch = ( expected_url != returned_url )

        # If the urls do not match, discard and restart the search
        if url_missmatch:

            self.logger.warning("The .xml file information does not match the current search. Discarding the file and re-connecting.")
            self.logger.debug("Expected: {:}".format(expected_url))
            self.logger.debug("Found:    {:}".format(returned_url))

            # Clear the entries from the list.
            entries = []

            # Clear the .xml file
            delete_file(self.logger, self.paths["papersxml"])

        # If the urls match AND the number of papers was less than the total:
        elif ( not url_missmatch ) and ( len(entries) < self.total_papers ):
            self.logger.debug("The .xml file information matches the current search. Continuing.")

        # If less than the total, provide info that we are continuing the search
        elif len(entries) >= self.total_papers:

            self.logger.info("All information found in the .xml file. Skipping the search.")

    # If the number of papers is less that the total, connect to arXiv
    if len(entries) < self.total_papers:

        # Set the starting number
        start_num = len(entries)

        self.logger.debug("The number of papers found so far is: {:}".format(start_num))

        # Compute the estimated time
        est_time = -self.arxiv_const.sleeptimer_search * ( ( self.total_papers - start_num ) // -self.arxiv_const.search_blocksize )

        # Compute the number of steps it will take
        # The time to complete depends almost entirely on the number of connections to arXiv and the number of sleeps -- the amount of data that is downloaded is minimal.
        num_steps = int( np.ceil(self.total_papers/self.arxiv_const.search_blocksize) * self.arxiv_const.search_blocksize )

        # Search the arXiv
        self.logger.info("Searching for papers. Estimated time: {:d} seconds".format(est_time))
        for ii in range(start_num, self.total_papers, self.arxiv_const.search_blocksize):

            # Compute the progress of the loop
            if ii+self.arxiv_const.search_blocksize > self.total_papers:
                remaining_steps = 1
                search_interval = self.total_papers - ii
                search_endnum   = self.total_papers
            else:
                remaining_steps = -((self.total_papers-ii)//-self.arxiv_const.search_blocksize)
                search_interval = self.arxiv_const.search_blocksize
                search_endnum   = ii + self.arxiv_const.search_blocksize

            # Print the progress bar
            progress_bar(ii, num_steps, remaining_steps * self.arxiv_const.sleeptimer_search)

            # Debug messages
            self.logger.debug("Remaining steps: {:}".format(remaining_steps))
            self.logger.debug("Starting number: {:}".format(ii))
            self.logger.debug("Ending number:   {:}".format(search_endnum))

            # Sleep before the query so that there is no dead time on the last query. Also need to sleep here as we do not wait after the initial API call
            self.logger.debug("Sleeping for {:} seconds ...".format(self.arxiv_const.sleeptimer_search))
            progress_bar(ii, num_steps, remaining_steps * self.arxiv_const.sleeptimer_search)
            time.sleep(self.arxiv_const.sleeptimer_search)

            # Query the API
            parsed_xml = arxiv_query(self.logger, self.arxiv_const.url, ii, search_interval)
            
            # Write the xml to a file
            #logger, filename, xml_data, ns, overwrite=False
            write_xml(self.logger, self.paths["papersxml"], parsed_xml, self.arxiv_const.ns)
            
            # Extract the paper from the xml
            entries.extend(extract_papers(self.logger, self.arxiv_const.ns, parsed_xml))

        # Close the progress bar
        progress_bar(self.total_papers, self.total_papers)

        self.logger.info("All paper information successfully downloaded from the arXiv servers!")

    # Double check that we found the correct number of papers
    if len(entries) != self.total_papers:

        self.logger.error("Found {:} papers (expected {:}).".format(len(entries), self.total_papers))

    else:

        self.logger.debug("Found the expected number of papers.")

    # Place all entries into a dataframe
    df = pd.DataFrame( entries )

    self.logger.debug("Removing duplicates and revised papers.")

    # Drop duplicate papers, if they exist
    df.drop_duplicates(subset="arXiv Number", inplace=True, ignore_index=True)
    num_dup = self.total_papers - len(df)
    self.logger.debug("Dropped {:} duplicate entries.".format(num_dup))

    # Remove revised papers
    df.drop(df[df["Revised?"]==True].index, inplace=True)
    df.reset_index(drop=True, inplace=True)
    num_rev = ( self.total_papers - num_dup ) - len(df)
    self.logger.debug("Dropped {:} revised papers.".format(num_rev))

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