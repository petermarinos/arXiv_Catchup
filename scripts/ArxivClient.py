# Import functions
from .arxiv_query import arxiv_query
from .file_io     import write_xml
from .utils       import delete_file

# Import libraries
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import datetime
import logging
import pathlib
import sys
import os

@dataclass
class ArxivConst():

    ns               : dict[str, str]
    sleep_opening    : float
    sleep_search     : float
    search_blocksize : int

class ArxivClient():

    # # Setup some of the API information
    def __init__(self, logger: logging.Logger, start_date: datetime.date, end_date: datetime.date, search_terms: dict[str, list[str]], cat_urlstring: str) -> None:
        """Set up some information that is required for the arXiv API calls.
        """

        self.logger = logger

        # Define the urls
        # Double braces, {{}}, used for fields that change on each search
        url = "https://export.arxiv.org/api/query?search_query=submittedDate:[{start_year:d}{start_month:02d}{start_day:02d}1900%20TO%20{end_year:d}{end_month:02d}{end_day:02d}1900]+AND+{cats:s}&sortBy=submittedDate&start={{start_num:d}}&max_results={{blocksize:d}}"

        apiquery = "https://arxiv.org/api/query?search_query=submittedDate:%22{start_year:d}{start_month:02d}{start_day:02d}1900+TO+{end_year:d}{end_month:02d}{end_day:02d}1900%22+AND+{cats:s}&start={{start_num:d}}&max_results={{blocksize:d}}&id_list="

        # Format the url
        self.url = url.format(
                              start_year  = start_date.year,
                              start_month = start_date.month,
                              start_day   = start_date.day,
                              end_year    = end_date.year,
                              end_month   = end_date.month,
                              end_day     = end_date.day,
                              cats        = cat_urlstring,
                             )
        
        # Format the API url
        if len(search_terms["Categories"]) == 1:
            api_catstring = cat_urlstring
        else:
            api_catstring = "(" + cat_urlstring + ")"
        
        self.apiquery = apiquery.format(
                                        start_year  = start_date.year,
                                        start_month = start_date.month,
                                        start_day   = start_date.day,
                                        end_year    = end_date.year,
                                        end_month   = end_date.month,
                                        end_day     = end_date.day,
                                        cats        = api_catstring,
                                       )
        
        # XML namespaces used by arXiv
        ns = {
              "atom"       : "http://www.w3.org/2005/Atom",
              "opensearch" : "http://a9.com/-/spec/opensearch/1.1/",
              "arxiv"      : "http://arxiv.org/schemas/atom",
             }
        # Define arXiv API courtesy limits
        # These are the values that arXiv asks we obey. Do not alter them.
        sleep_opening    = 0.25 # 0.25 seconds between opening links
        sleep_search     = 3    # 3 seconds per search
        search_blocksize = 10   # Each search downloads only ten papers (max=2000)

        self.arxiv_const = ArxivConst(ns=ns,
                                      sleep_opening=sleep_opening,
                                      sleep_search=sleep_search,
                                      search_blocksize=search_blocksize)

        # Define the ssl_context and define a flag
        self.ssl_dict = {"ssl_context" : None,
                         "ssl_preverr" : False}
        
    # # Obtain basic search information
    def get_search_info(self, arxiv_const: ArxivConst, xml_path: pathlib.Path) -> None:
        """Obtain the information on how we will obtain all papers within the search period. Will attempt to load from an .xml file, and will fall back to perform an initial query to the arXiv servers in case no file was found, or the file does not match the current search parameters.

        xml_path : Path to searchxml
        """

        # Search for xml file. If found, load it
        if os.path.exists(xml_path):
            
            self.logger.info("Found a .xml file: {:}".format(xml_path))
            self.logger.info("Attempting to continue from the previous failed run.")

            # Load the file
            xml_data = ET.parse(xml_path)

            # Check the url from the loaded xml matches the current search url
            expected_url = self.apiquery.format(start_num=0, blocksize=1)
            returned_urlblock = xml_data.find("atom:link", arxiv_const.ns)
            if returned_urlblock is None:
                self.logger.critical("arXiv data did not include a link. It is corrupted (returned None).\n")
                raise
            returned_url = returned_urlblock.attrib["href"]

            url_missmatch = ( expected_url != returned_url )
            if url_missmatch:
                self.logger.warning("The .xml file information does not match the current search. Discarding the file and re-connecting.")
                self.logger.debug("Expected: {:}".format(expected_url))
                self.logger.debug("Found:    {:}".format(returned_url))
                # Clear the .xml file
                delete_file(self.logger, xml_path)
            else:
                self.logger.debug("The .xml file information matches the current search. Continuing")

        # If there is no file, perform the search
        # NOTE: This is not an elif as the above if statement can delete the file. If the file is deleted, we want to be redownloaded. If the file never existed, we want to download. If the file existed and had the correct information, then this statement will not be activated anyway.
        if not os.path.exists(xml_path):

            self.logger.info("Obtaining search information from the servers.")

            # Perform the query
            xml_data, self.ssl_dict = arxiv_query(self.logger, self.ssl_dict, self.url, 0, 1)
            
            # Write the extracted xml to a file
            write_xml(self.logger, xml_path, xml_data, arxiv_const.ns, overwrite=True)
            
            self.logger.info("Search information successfully obtained from the arXiv servers!")
        
        # Extract the total number of papers that were found
        max_num_temp = xml_data.find("opensearch:totalResults", arxiv_const.ns)
        if max_num_temp is None:
            self.logger.critical("arXiv data did not include a number of papers. It is corrupted (returned None).\n")
            raise
        max_num_str = max_num_temp.text
        if max_num_str is None:
            self.logger.critical("arXiv data for the number of papers is corrupted (returned None).\n")
            raise

        # Set the number of papers
        self.total_papers = int(max_num_str)

    # # Check the search info query results for errors
    def arxiv_error_check(self, arxiv_const: ArxivConst, xml_path: pathlib.Path) -> None:
        """Runs some error checks on the results of the initial arXiv API pull (i.e. the one that collects some basic information).
        """

        self.logger.debug("Checking for issues with the search information ...")

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
        time_to_search_minutes = self.total_papers * arxiv_const.sleep_search / ( arxiv_const.search_blocksize * 60 )
        
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
                delete_file(self.logger, xml_path)

                # Exit
                sys.exit("Cancelling the search. Reduce search window to decrease the number of results.")

        self.logger.debug("All search information tests passed!")
