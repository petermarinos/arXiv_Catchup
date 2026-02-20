# Import functions
from .string_handling import normalise_string
from .file_io         import write_date
from .dates           import parse_date, calc_search_endtime, calc_next_posttime
from .utils           import set_filenames, delete_file

# Import libraries
import numpy as np
import argparse
import datetime
import logging
import pathlib
import yaml
import os

class Config:
    """Defines important parameters required for the search
    """

    # # Initialise the class
    def __init__(self, logger: logging.Logger, root_dir: pathlib.Path) -> None:
        """Create the CatchupPipeline object, which will store important values used throughout the search, scoring, and filtering sections.
        - May want to break apart to separate pipelines in the future

        inputs
        ------
        cdir : Absolute path, '/path/to/catchup.py'.
        args : CLI arguments.
        """

        # Define important variables
        self.logger = logger
        self.paths  = set_filenames(root_dir)
        
       # Define some datetime objects
        self.post_time    = datetime.time(6, 0, tzinfo=datetime.timezone.utc) # Define the posting time of the daily list
        self.search_time  = datetime.time(19, 0, tzinfo=datetime.timezone.utc) # Define the times that the daily list covers
        self.current_time = datetime.datetime.now(datetime.timezone.utc) # Obtain the current time, converted to the UTC timezone
        
    # # Load search terms from the auxiliary file
    def get_searchterms(self) -> None:
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
            self.cat_urlstring = "+OR+".join("cat:{:}".format(c) for c in self.search_terms["Categories"])

            # Define category string to make nice print statements
            if len(self.search_terms["Categories"]) == 2:

                self.cat_printstring = " and ".join("{:}".format(c) for c in self.search_terms["Categories"])

            elif len(self.search_terms["Categories"]) > 2:

                catstring_temp  = ", ".join("{:}".format(c) for c in self.search_terms["Categories"][:-1])
                self.cat_printstring = ", and ".join([catstring_temp, self.search_terms["Categories"][-1]])

            else:

                self.cat_printstring = ", ".join("{:}".format(c) for c in self.search_terms["Categories"])

            # Print which categories are being searched over
            self.logger.info("Searching the {:} categories".format(self.cat_printstring))

        # If a category with a wildcard (e.g. astro-ph*) is entered with other matching sub-categories (e.g. astro-ph.HE), the API will ignore the sub-categories
        # No need to catch it here

        # # Warn the user if no terms are found
        # If no authors are found, warn the user
        if self.search_terms["Authors"] is None:

            self.logger.warning("No search terms were found in the 'Authors' entry in the configuration file.")

        # Otherwise, log all authors that were extracted
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
    def get_dates(self, cli_args: argparse.Namespace) -> None:
        """Set up the dates that the script uses for the arXiv API calls.
        """

        # If the end_date was passed on the command line, use it
        if cli_args.end_date:

            self.logger.debug("Attempting to use the end_date: {:}".format(cli_args.end_date))

            self.end_time, self.end_date = parse_date(self.logger, cli_args.end_date,   "end-date",   self.search_time, self.post_time)

        # If the end_date was not passed in the command line, compute it
        else:

            self.logger.debug("No end date was input. Computing based on the current time.")

            self.end_time = calc_search_endtime(self.current_time, self.search_time, self.post_time)
            self.end_date = self.end_time.date()

        # If the start_date was passed on the command line, use it
        if cli_args.start_date:

            self.logger.debug("Attempting to use the start_date: {:}".format(cli_args.start_date))

            self.start_time, self.start_date = parse_date(self.logger, cli_args.start_date, "start-date", self.search_time, self.post_time)

        # If the start_date was not passed on the command line, attempt to load it from the previous run file
        if not cli_args.start_date:

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
    def date_error_check(self) -> None:
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

    # # Delete the temporarly files
    def clear_temp_files(self) -> None:
        """Clear the temporary files created by the script.
        """

        delete_file(self.logger, self.paths["searchxml"])
        delete_file(self.logger, self.paths["papersxml"])
