# Import classes
from .paper_classes import Corpus

# Import functions
from .string_handling import normalise_string
from .arxiv_query     import arxiv_query, extract_papers
from .constants       import set_filenames, set_arxiv_constants, arxivConst
from .file_io         import write_date, write_links, write_xml
from .dates           import parse_date, calc_search_endtime, calc_next_posttime
from .utils           import progress_bar, pretty_sleep, logger_setup, delete_file

# Import libraries
import xml.etree.ElementTree as ET
import numpy                 as np
import webbrowser
import argparse
import datetime
import typing
import time
import yaml
import sys
import os

# Define the pipeline class
class CatchupPipeline:

    # # Initialise the class
    def __init__(self, cdir: str, args: argparse.Namespace) -> None:

        self.args   = args
        self.logger = logger_setup(args, cdir)
        self.paths  = set_filenames(cdir)

        url, apiquery, ns, sleep_opening, sleep_search, search_blocksize = set_arxiv_constants()
        self.arxiv_const = arxivConst(url=url,
                                      apiquery=apiquery,
                                      ns=ns,
                                      sleeptimer_opening=sleep_opening,
                                      sleeptimer_search=sleep_search,
                                      search_blocksize=search_blocksize)
        
       # Define the posting time of the daily list
        self.post_time    = datetime.time(6, 0, tzinfo=datetime.timezone.utc)  # 06:00 UTC
        # Define the posting time of the daily list
        self.search_time  = datetime.time(19, 0, tzinfo=datetime.timezone.utc) # 19:00 UTC
        # Obtain the current time, converted to the UTC timezone
        self.current_time = datetime.datetime.now(datetime.timezone.utc)

        # Define the ssl_context and define a flag
        self.ssl_dict = {"ssl_context" : None,
                         "ssl_preverr" : False}
        
        # Initialise the corpus
        self.corpus = Corpus()
        
    # # Load search terms from the auxiliary file
    def getSearchterms(self) -> None:
        """Loads the user-defined search terms from the `search_terms.yaml` into a dictionary.
        """

        self.logger.info("Loading search terms from {:}.".format(self.paths["searchterms"]))

        # Load the .yaml into a dictionary
        with open(self.paths["searchterms"], 'r') as f:

            self.search_terms = yaml.safe_load(f)

        # Normalise author strings and remove duplicates
        if self.search_terms["Authors"] is not None:
            self.search_terms["Authors"] = np.unique([normalise_string(_) for _ in self.search_terms["Authors"]])

        # # Check the file

        # At least one category is required
        if self.search_terms["Categories"] is None:

            self.logger.critical("No search terms were found in the 'Categories' entry in the configuration file.\n          Please check the file and add at least one item.\n")
            raise
        
        else:

            self.search_terms["Categories"] = np.unique(self.search_terms["Categories"])

            # Define category string for the urls/API calls
            self.cat_urlstring = "+OR+".join(f"cat:{c}" for c in self.search_terms["Categories"])

            # Define category string to make nice print statements
            if len(self.search_terms["Categories"]) == 2:

                self.cat_printstring = " and ".join(f"{c}" for c in self.search_terms["Categories"])

            elif len(self.search_terms["Categories"]) > 2:

                catstring_temp  = ", ".join(f"{c}" for c in self.search_terms["Categories"][:-1])
                self.cat_printstring = ", and ".join([catstring_temp, self.search_terms["Categories"][-1]])

            else:

                self.cat_printstring = ", ".join(f"{c}" for c in self.search_terms["Categories"])

            # Print which categories are being searched over
            self.logger.info("Searching the {:} categories".format(self.cat_printstring))

        # If a category with a wildcard (e.g. astro-ph*) is entered with other matching sub-categories (e.g. astro-ph.HE), the API will ignore the sub-categories
        # No need to catch it here

        # # Warn the user if no terms are found
        # If no authors are found, warn the user
        if self.search_terms["Authors"] is None:

            self.logger.warning("No search terms were found in the 'Authors' entry in the configuration file.")

        # Otherwise, log all found authors
        else:

            for author in self.search_terms["Authors"]:

                self.logger.debug("Found author: {:}".format(author))

        # If no included words are found, warn the user
        if self.search_terms["Included Words"] is None:

            self.logger.warning("No search terms were found in the 'Included Words' entry in the configuration file.")

        # Otherwise, remove duplicates and log all found included words
        else:

            self.search_terms["Included Words"] = np.unique(self.search_terms["Included Words"])
            
            for included_word in self.search_terms["Included Words"]:

                self.logger.debug("Found included word: {:}".format(included_word))

        # If no excluded words are found, warn the user
        if self.search_terms["Excluded Words"] is None:

            self.logger.warning("No search terms were found in the 'Excluded Words' entry in the configuration file.")

        # Otherwise, remove duplicates and log all found excluded words
        else:

            self.search_terms["Excluded Words"] = np.unique(self.search_terms["Excluded Words"])
            
            for excluded_word in self.search_terms["Excluded Words"]:

                self.logger.debug("Found excluded word: {:}".format(excluded_word))

        # Check to see if any word is in both the 'included' and 'excluded fields
        for inc_word in self.search_terms["Included Words"]:

            if inc_word in self.search_terms["Excluded Words"]:

                self.logger.warning("The term '{:}' appears in both the Included and Excluded word fields.".format(inc_word))

    # # Load and check dates
    def getDates(self) -> None:
        """Set up the date that the script uses for the arXiv API calls.
        """

        # If the end_date was passed on the command line, use it
        if self.args.end_date:

            self.logger.debug("Attempting to use the end_date: {:}".format(self.args.end_date))

            self.end_time, self.end_date = parse_date(self.logger, self.args.end_date,   "end-date",   self.search_time, self.post_time)

        # If the end_date was not passed in the command line, compute it
        else:

            self.logger.debug("No end date was input. Computing based on the current time.")

            self.end_time = calc_search_endtime(self.current_time, self.search_time, self.post_time)
            self.end_date = self.end_time.date()

        # If the start_date was passed on the command line, use it
        if self.args.start_date:

            self.logger.debug("Attempting to use the start_date: {:}".format(self.args.start_date))

            self.start_time, self.start_date = parse_date(self.logger, self.args.start_date, "start-date", self.search_time, self.post_time)

        # If the start_date was not passed on the command line, attempt to load it from the previous run file
        if not self.args.start_date:

            self.logger.debug("No start date was input.")

            # If the file doesn't exist:
            if not os.path.exists(self.paths["prevsearch"]):

                self.logger.debug("No previous search file found. Setting to the day prior to the end_date.")

                # Compute the list time before the previous
                # This can be done by passing the end_time found above into the calc_search_endtime() function
                prev_end_time  = calc_search_endtime(self.end_time, self.search_time, self.post_time)
                
                write_date(self.logger, self.paths["prevsearch"], prev_end_time.date())

            # If the file does exist, load it and extract the previous runtime
            with open(self.paths["prevsearch"], "r", encoding="utf-8") as f:

                self.start_time, self.start_date = parse_date(self.logger, next(f), "start-date", self.search_time, self.post_time)

        # Print some information. Useful to do it before error checks so that all information is visible
        self.logger.info("Searching from {:}/{:}/{:} 19:00 UTC to {:}/{:}/{:} 19:00 UTC".format(self.start_date.year, self.start_date.month, self.start_date.day, self.end_date.year, self.end_date.month, self.end_date.day))

    # # Error check the dates
    def dateErrorCheck(self) -> None:
        """Check for errors with the dates.
        """

        # Compute how long the search is covering
        prev_run = self.end_date - self.start_date

        # Compute the time that the next list will be posted
        nextlist_time   = calc_next_posttime(self.current_time, self.post_time)
        time_until_next = nextlist_time - self.current_time

        t_days    = time_until_next.days
        t_hours   = time_until_next.seconds//3600
        t_minutes = (time_until_next.seconds//60) - t_hours * 60

        next_post_string = ( "\n          "
                        + "If looking for the next list, it will be posted at {:%Y-%m-%d %H:%M (%Z)},".format(nextlist_time)
                        + "\n          "
                        + "which is {:} days, {:} hours, and {:} minutes from now.".format(t_days, t_hours, t_minutes) )

        # Compute number of days between now and the start of the search
        deltadays_now_to_search = ( self.current_time.date() - self.start_date ).days

        # Count the number of valid search days between start_date and end_date
        valid_search_days = 0
        temp_date         = self.end_date
        while temp_date > self.start_date:
            valid_search_days += 1
            temp_date -= datetime.timedelta(days=1)

        # Raise some errors
        # If the search start date is in the future:
        if deltadays_now_to_search < 0:
            self.logger.critical("Search start date is in the future.\n")
            raise

        # If the search end date is in the future:
        elif ( self.current_time.date() - self.end_date ).days < 0:
            self.logger.critical("Search end date is in the future.\n")
            raise

        # If the end date is equal to the start date, tell the user to wait
        elif prev_run.days == 0:
            self.logger.critical("Search start/end dates are equal.{:}\n".format(next_post_string))
            raise

        # If the end date is before the start date
        elif prev_run.days < 0:
            self.logger.critical("Search start date is after the end date. Check for timezone issues.\n")
            raise

        # If the search period doesn't cover any searching days, tell the user to wait
        # Typically one of the previous errors will occur before this one if the entire search period is invalid
        elif deltadays_now_to_search < 7 and valid_search_days == 0:
            self.logger.critical("No valid search dates are included.{:}\n".format(next_post_string))
            raise

        # If there are no issues, let the user know how many days we are searching over
        else:
            self.logger.info("Days since the previous search: {:}".format(prev_run.days))

    # # Setup some of the API information
    def setupAPI(self) -> None:
        # Format the url
        self.arxiv_const.url = self.arxiv_const.url.format(
                                  start_year  = self.start_date.year,
                                  start_month = self.start_date.month,
                                  start_day   = self.start_date.day,
                                  end_year    = self.end_date.year,
                                  end_month   = self.end_date.month,
                                  end_day     = self.end_date.day,
                                  cats        = self.cat_urlstring,
                                  )
        
        # Format the API url
        if len(self.search_terms["Categories"]) == 1:
            api_catstring = self.cat_urlstring
        else:
            api_catstring = "(" + self.cat_urlstring + ")"
        self.arxiv_const.apiquery = self.arxiv_const.apiquery.format(
                                  start_year  = self.start_date.year,
                                  start_month = self.start_date.month,
                                  start_day   = self.start_date.day,
                                  end_year    = self.end_date.year,
                                  end_month   = self.end_date.month,
                                  end_day     = self.end_date.day,
                                  cats        = api_catstring,
                                  )

    # # Obtain basic search information
    def getSearchInfo(self) -> None:
        """Performs the initial query to obtain important run information.
        """

        # Search for xml file. If found, load it
        if os.path.exists(self.paths["searchxml"]):
            
            self.logger.info("Found a .xml file: {:}".format(self.paths["searchxml"]))
            self.logger.info("Attempting to continue from the previous failed run.")

            # Load the file
            xml_data = ET.parse(self.paths["searchxml"])

            # Check the url from the loaded xml matches the current search url
            expected_url = self.arxiv_const.apiquery.format(start_num=0, blocksize=1)
            returned_urlblock = xml_data.find("atom:link", self.arxiv_const.ns)
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
                delete_file(self.logger, self.paths["searchxml"])
            else:
                self.logger.debug("The .xml file information matches the current search. Continuing")

        # If there is no file, perform the search
        # NOTE: This is not an elif as the above if statement can delete the file. If the file is deleted, we want to be redownloaded. If the file never existed, we want to download. If the file existed and had the correct information, then this statement will not be activated anyway.
        if not os.path.exists(self.paths["searchxml"]):

            self.logger.info("Obtaining search information from the servers.")

            # Perform the query
            xml_data, self.ssl_dict = arxiv_query(self.logger, self.ssl_dict, self.arxiv_const.url, 0, 1)
            
            # Write the extracted xml to a file
            write_xml(self.logger, self.paths["searchxml"], xml_data, self.arxiv_const.ns, overwrite=True)
            
            self.logger.info("Search information successfully obtained from the arXiv servers!")
        
        # Extract the total number of papers that were found
        max_num_temp = xml_data.find("opensearch:totalResults", self.arxiv_const.ns)
        if max_num_temp is None:
            self.logger.critical("arXiv data did not include a number of papers. It is corrupted (returned None).\n")
            raise
        max_num_str = max_num_temp.text
        if max_num_str is None:
            self.logger.critical("arXiv data for the number of papers is corrupted (returned None).\n")
            raise

        # Set the number of papers
        self.total_papers = int(max_num_str)

    def arxivErrorCheck(self) -> None:
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
                delete_file(self.logger, self.paths["searchxml"])

                # Exit
                sys.exit("Cancelling the search. Reduce search window to decrease the number of results.")

        self.logger.debug("All search information tests passed!")

    # # Loop through the searches and obtain all papers
    def getPapers(self) -> None:
        """Searches the arXiv for all papers that satisfy our criteria.
        """

        # Search for xml file. If found, load it
        if os.path.exists(self.paths["papersxml"]):
            
            self.logger.info("Found an .xml file: {:}".format(self.paths["papersxml"]))
            self.logger.info("Continuing from the previous failed run.")

            # Load the file
            try:
                xml_tree = typing.cast( ET.ElementTree, ET.parse(self.paths["papersxml"]) )
            except ET.ParseError as e:
                self.logger.critical("Could not parse XML: %s", e)
                raise

            # Extract the papers from the xml
            extract_papers(self.logger, self.corpus, self.arxiv_const.ns, xml_tree)

            # Print how many were found
            # Compute the length of the corpus
            self.corpus.getCorpusLength()
            n_papers = self.corpus.length
            self.logger.info("Found {:} of {:} papers in the .xml file.".format(self.corpus.length, self.total_papers))

            # Check the url from the loaded xml matches the current search url
            expected_url = self.arxiv_const.apiquery.format(start_num=0, blocksize=self.arxiv_const.search_blocksize)
            returned_urlblock = xml_tree.find("atom:link", self.arxiv_const.ns)
            if returned_urlblock is None:
                self.logger.critical("arXiv data did not include a link. It is corrupted (returned None).\n")
                raise
            returned_url = returned_urlblock.attrib["href"]

            url_missmatch = ( expected_url != returned_url )

            # If the urls do not match, discard and restart the search
            if url_missmatch:

                self.logger.warning("The .xml file information does not match the current search. Discarding the file and re-connecting.")
                self.logger.debug("Expected: {:}".format(expected_url))
                self.logger.debug("Found:    {:}".format(returned_url))

                # # Clear the entries from the list.
                # entries = []
                self.corpus.clearCorpus(self.logger)

                # Clear the .xml file
                delete_file(self.logger, self.paths["papersxml"])

            # If the urls match AND the number of papers was less than the total:
            elif ( not url_missmatch ) and ( n_papers < self.total_papers ):
                self.logger.debug("The .xml file information matches the current search. Continuing.")

            # If less than the total, provide info that we are continuing the search
            elif n_papers >= self.total_papers:

                self.logger.info("All information found in the .xml file. Skipping the search.")

        # Compute the length of the corpus
        self.corpus.getCorpusLength()
        n_papers = self.corpus.length
        # If the number of papers is less that the total, connect to arXiv
        if n_papers < self.total_papers:

            # Set the starting number
            start_num = n_papers

            self.logger.debug("The number of papers found so far is: {:}".format(start_num))

            # # Compute the estimated time for the search
            # The time to complete depends almost entirely on the number of connections to arXiv and the number of sleeps, though there is some slowdown due to connecting to the arXiv servers and waiting for a response
            # It is typically 0.7s per connection, though it varies *wildly*
            # We also add jitter to the timers with random.uniform(0, 0.3) (average slowdown of 0.15 seconds)
            # Because of how wildly it varies, computing the remaining search time accurately during the loop is pointless. Just use the fudge_timer
            fudge_timer = 0.7 + 0.15
            est_time    = - ( self.arxiv_const.sleeptimer_search + fudge_timer ) * ( ( self.total_papers - start_num ) // -self.arxiv_const.search_blocksize )

            # Compute the number of steps it will take
            num_steps = int( np.ceil(self.total_papers/self.arxiv_const.search_blocksize) * self.arxiv_const.search_blocksize )

            # Search the arXiv
            self.logger.info("Searching for papers. Estimated time: {:.0f} seconds".format(est_time))
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
                progress_bar(ii, num_steps, remaining_steps * ( self.arxiv_const.sleeptimer_search + fudge_timer ))

                # Debug messages
                self.logger.debug("Remaining steps: {:}".format(remaining_steps))
                self.logger.debug("Starting number: {:}".format(ii))
                self.logger.debug("Ending number:   {:}".format(search_endnum))

                # Sleep before the query so that there is no dead time on the last query. Also need to sleep here as we do not wait after the initial API call
                # Add jitter to the sleep timer
                current_sleep_time = self.arxiv_const.sleeptimer_search
                progress_bar(ii, num_steps, remaining_steps * current_sleep_time)
                pretty_sleep(self.logger, current_sleep_time)

                # Query the API
                parsed_xml, self.ssl_dict = arxiv_query(self.logger, self.ssl_dict, self.arxiv_const.url, ii, search_interval)
                
                # Write the xml to a file
                #logger, filename, xml_data, ns, overwrite=False
                write_xml(self.logger, self.paths["papersxml"], parsed_xml, self.arxiv_const.ns)
                
                # Extract the paper from the xml
                extract_papers(self.logger, self.corpus, self.arxiv_const.ns, parsed_xml)

            # Close the progress bar
            progress_bar(self.total_papers, self.total_papers)

            self.logger.info("All paper information successfully downloaded from the arXiv servers!")

        # Double check that we found the correct number of papers
        self.corpus.getCorpusLength()
        n_papers = self.corpus.length
        if n_papers != self.total_papers:

            self.logger.error("Found {:} papers (expected {:}).".format(n_papers, self.total_papers))

        else:

            self.logger.debug("Found the expected number of papers ({:}).".format(self.total_papers))

        # # Drop duplicate papers, if they exist
        # # No longer needed as two keys cannot be equal.
        # self.corpus.dropDuplicates(self.logger)

        # Remove revised papers
        self.corpus.dropRevisions(self.logger)

    # # Find matches
    def findMatches(self) -> None:

        self.logger.info("Finding keyword matches")

        # Loop over all entries
        count = 0
        for arxiv_ID, paper in self.corpus.corpus.items():

            progress_bar(count, self.corpus.length) # No time estimate as it should always be fast.

            self.logger.debug("Seaching for matches in arXiv:{:}.".format(arxiv_ID))
            
            # Seach for Authors
            paper.matchAuthors(self.logger, self.search_terms["Authors"])

            # # Search for included words
            paper.matchWords(self.logger, self.search_terms, "Included Words")

            # # Search for excluded words
            paper.matchWords(self.logger, self.search_terms, "Excluded Words")

            count += 1

        progress_bar(self.corpus.length, self.corpus.length)

    # # Score the papers
    def scorePapersMatches(self) -> None:
        """Scores the papers based on the number of matches found.
        NOTE: This function also counts the number of matches.
        """

        self.logger.info("Scoring papers based on matches")

        # Loop over all entries
        count = 0
        for arxiv_ID, paper in self.corpus.corpus.items():

            progress_bar(count, self.corpus.length) # No time estimate as it should always be fast

            self.logger.debug("Computing a score for arXiv:{:}.".format(arxiv_ID))

            # Score the authors
            paper.scoreAuthors(self.logger)

            # Score for included words
            paper.scoreWords(self.logger, "Included Words")

            # Score for excluded words
            paper.scoreWords(self.logger, "Excluded Words")

            # Finalise the score
            paper.finalWordScore(self.logger)

            count += 1

        progress_bar(self.corpus.length, self.corpus.length)
    
    def scorePapersML(self) -> None:
        """Scores the papers based on a machine-learning algorithm.
        NOTE: This method is not implemented. Current plan is to create a model that can be traied by the user on a directory containing many .pdf files. This function would then use said model to score each paper in the arXiv search.

        outputs
        -------
        entries_of_note : Contains the indices of all papers that pass the filter.
        """

        self.logger.error("Attempting to use ML model to score papers. This has not been implemented yet. Returning no results.\n")
        raise

    # # Filter the papers based on matches
    def filterPapersMatches(self) -> None:
        self.corpus.filterCorpusMatches(self.logger)

    # Filter the papers based on their scores
    def filterPapersScore(self) -> None:
        self.corpus.filterCorpusScore(self.logger)

    # # Display the results
    def getDisplayMethod(self) -> None:

        # If there is at least one paper, open/prompt
        if len(self.corpus.papers_of_note) > 0:

            # If both -f and -w are passed, both open and write the links
            if self.args.force_open and self.args.write_to_file:

                self.open_in_brower = True
                self.write_to_file  = True

            # If -f is passed and -w is not, only open the links
            elif self.args.force_open and not self.args.write_to_file:

                self.open_in_brower = True
                self.write_to_file  = False

            # If -f is not passed and -w is, only write the links
            elif not self.args.force_open and self.args.write_to_file:

                self.open_in_brower = False
                self.write_to_file  = True

            # If neither -f nor -w were passed, prompt the user to ask for the behaviour they prefer
            else:

                # Ask the user if they would like to open the links in the browser. Default is no
                print("")
                user_prompt_browser = input(
                                            "There are {:} link(s). Open in the browser? It will take {:} seconds. [y/N]: ".format(len(self.corpus.papers_of_note), len(self.corpus.papers_of_note) * self.arxiv_const.sleeptimer_opening)
                                        ).strip().lower()

                # If they say yes to opening in the browser
                if user_prompt_browser == "y":

                    self.open_in_brower = True
                    self.write_to_file  = False

                # If they say no to opening in the browser
                else:

                    self.open_in_brower = False

                    # Ask if they would like to save the links to a file or print to the terminal. Default is no
                    user_prompt_file = input(
                                            "Save all links to a file? Otherwise they will be written to the terminal. [y/N]: "
                                            ).strip().lower()

                    # If they want to save the output
                    if user_prompt_file == "y":

                        self.write_to_file  = True
                    
                    # If they want the output in the terminal
                    else:

                        self.write_to_file  = False

                        print("")
                        self.logger.info("Printing all links to the terminal:\n")
                        for arxiv_id in self.corpus.papers_of_note:

                            print(self.corpus.corpus[arxiv_id].link_abs)
                        print("")

        else:

            self.logger.warning("No papers of interest were found.")
            self.write_to_file  = False
            self.open_in_brower = False

        # Check if any papers were found
        if self.corpus.length == 0:

            self.logger.warning("As no papers were found, the date file was not updated")

        # If papers were found, update the date file
        else:

            # Write the end date of the search to a file for the next run
            write_date(self.logger, self.paths["prevsearch"], self.end_date)
            
    def display(self) -> None:

        if self.write_to_file:

            write_links(self.logger, self.paths["catchup"], self.corpus, self.corpus.papers_of_note)

        if self.open_in_brower:
            
            # Calculate the number of links
            total = len(self.corpus.papers_of_note)

            # Loop through the list and open all in the web browser
            request_count = 0
            # time_start = time.time()
            self.logger.info("Opening the papers. Estimated time: {:.2f} seconds".format(total * self.arxiv_const.sleeptimer_opening))
            for arxiv_id in self.corpus.papers_of_note:

                progress_bar(request_count, total, ( total - request_count ) * self.arxiv_const.sleeptimer_opening)

                # # arXiv asks that you limit opening pages to four requests per second
                # Sleep before the request to prevent an unnecessary sleep at the end
                # # Sleep for 1s every four pages (recommended)
                # if request_count % 4 == 0:
                #     time.sleep(1)
                # Sleep for 0.25s per request (my preferred method when having to watch it open a large number)
                if request_count > 0:
                    time.sleep(self.arxiv_const.sleeptimer_opening)

                link = self.corpus.corpus[arxiv_id].link_abs

                # Open in new window if flag is set
                if self.args.new_window:

                    if request_count == 0:

                        webbrowser.open(link, new=1)  # new=1: open in a new browser window

                    else:

                        webbrowser.open(link, new=2)  # new=2: open in a new tab

                # Otherwise, open in the current window
                else:

                    webbrowser.open(link)  # Default behavior, just opens everything in the current window

                request_count += 1

            progress_bar(total, total)

    # # Summarise the search results
    def summary(self) -> None:

        # Compute the number of digits in the number of papers found
        max_digits = len(str(self.total_papers))
        
        # Print a summary
        print("")
        self.logger.info("There was a total of {: >{fill}} papers submitted to the categories of interest within the search window.".format(self.total_papers, fill=max_digits))
        self.logger.info("           of these, {: >{fill}} papers were opened/linked.".format(len(self.corpus.papers_of_note), fill=max_digits))
        print("")

    # # Delete the temporarly files
    def clearTempFiles(self) -> None:

        delete_file(self.logger, self.paths["searchxml"])
        delete_file(self.logger, self.paths["papersxml"])
