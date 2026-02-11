# Import libraries
import numpy as np

import argparse
import logging
import pathlib
import yaml
import sys

def cli_args():
    """Defines and parses the CLI arguments passed when running the script.

    outputs
    -------
    args : namespace
        Contains all parsed arguments and their values.
    """

    # Parse command-line arguments
    parser = argparse.ArgumentParser(prog='arXiv Catchup',
                                    description='Search arXiv for papers matching your criteria')

    parser.add_argument('-f', '--force-open', action='store_true',
                        help='Skip the warning about how many papers will be opened.')
    parser.add_argument('-w', '--write-to-file', action='store_true',
                        help='Skip opening links and user prompts, writing all links straight to a file.')
    parser.add_argument('-n', '--new-window', action='store_true',
                        help='Open all papers in a single new browser window as tabs.') # Doesn't work on mac with firefox
    parser.add_argument('-s', '--start-date', type=str,
                        help='Set the start time for the search, YYYY-MM-DD (19:00 UTC)\nIgnores the date in the `prev_search.txt`.')
    parser.add_argument('-e', '--end-date', type=str,
                        help='Set the end time for the search, YYYY-MM-DD (19:00 UTC).')
    parser.add_argument('-v', '--verbosity', type=int, default=3,
                        help='Verbosity level.')

    args = parser.parse_args()

    return args

def logger_setup(args):
    """Set up the logger.
    Note: There are currently no messages with levels set to CRITICAL. Verbosity must be set to 1 or higher to show any messages.

    inputs
    ------
    verbosity : int
        Defines the level for the logger.
        0 => only critical errors
        1 => errors                 and all of the above
        2 => warnings               and all of the above
        3 => info                   and all of the above
        4 => debug                  and all of the above
    """

    # Define logging message
    # logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s') # Show time
    logging.basicConfig(format="%(levelname)s: %(message)s") # Don't show time

    # Initialise the logger
    logger = logging.getLogger()

    # Set the logging level
    if args.verbosity == 0:
        logger.setLevel(logging.CRITICAL)
    elif args.verbosity == 1:
        logger.setLevel(logging.ERROR)
    elif args.verbosity == 2:
        logger.setLevel(logging.WARNING)
    elif args.verbosity == 3:
        logger.setLevel(logging.INFO)
    elif args.verbosity >= 4:
        logger.setLevel(logging.DEBUG)

    return logger

def load_searchterms(filename, logger):
    """Loads the user-defined search terms from the `search_terms.yaml` into a dictionary.

    inputs
    ------
    filename : str
        Path+filename of the `search_terms.yaml` file.

    outputs
    -------
    search_terms  : dict
        Dictionary of all loaded search terms.
    cat_urlstring : str
        String containing the url used in the arXiv API queries
    """

    # Load the .yaml into a dictionary
    with open(filename, 'r') as f:

        search_terms = yaml.safe_load(f)

    # # Check the file

    # At least one category is required
    if search_terms["Categories"] is None:

        raise ValueError("No search terms were found in the 'Categories' entry in the configuration file.\n            Please check the file and add at least one item")
    
    else:

        # Define category string for the urls/API calls
        cat_urlstring = "+OR+".join(f"cat:{c}" for c in search_terms["Categories"])

        # Define category string to make nice print statements
        if len(search_terms["Categories"]) == 2:

            cat_printstring = " and ".join(f"{c}" for c in search_terms["Categories"])

        elif len(search_terms["Categories"]) > 2:

            catstring_temp = ", ".join(f"{c}" for c in search_terms["Categories"][:-1])
            cat_printstring = ", and ".join([catstring_temp, search_terms["Categories"][-1]])

        else:

            cat_printstring = ", ".join(f"{c}" for c in search_terms["Categories"])

        # Print which categories are being searched over
        logger.info("Searching the {:} categories".format(cat_printstring))

    # If a category with a wildcard (e.g. astro-ph*) is entered with other matching sub-categories (e.g. astro-ph.HE), the API will ignore the sub-categories
    # No need to catch it here

    # At least one search term is required in the "Words" key
    if search_terms["Included Words"] is None:

        raise ValueError("No search terms were found in the 'Included Words' entry in the configuration file.\n            Please check the file and add at least one item")

    # No search terms are required for the "Authors" or "Excluded Words" keys
    # Warn the user if no terms are found
    if search_terms["Authors"] is None:

        logger.warning("No search terms were found in the 'Authors' entry in the configuration file.")

    if search_terms["Excluded Words"] is None:

        logger.warning("No search terms were found in the 'Excluded Words' entry in the configuration file.")

    return search_terms, cat_urlstring

def progress_bar(ii, total, time_estimate=None):
    """Prints a progress bar that updates as the loop progresses.

    inputs
    ------
    ii            : int
        Current step in the loop.
    total         : int
        Final step in the loop.
    time_estimate : float
        Estimate of the remaining time of the loop.
    """

    percent_progress = 100 * ii / total

    width = 50 # Width of the progress bar in characters
    bar_string = "■" * int( np.floor( percent_progress * width/100 ) ) + "□" * int( width - np.floor( percent_progress * width/100 ) )

    if time_estimate is not None:
        if time_estimate <= 60:
            progress_message = "|{:s}|  {: >3}%  Remaining: {:.2f} seconds".format( bar_string, int(np.ceil(percent_progress)), time_estimate )
        elif 60 < time_estimate <= 3600:
            progress_message = "|{:s}|  {: >3}%  Remaining: {:.1f} minutes".format( bar_string, int(np.ceil(percent_progress)), time_estimate/60 )
        else:
            progress_message = "|{:s}|  {: >3}%  Remaining: {:.1f} hours".format( bar_string, int(np.ceil(percent_progress)), time_estimate/3600 )
    else:
        progress_message = "|{:s}|  {: >3}%".format( bar_string, int(np.ceil(percent_progress)) )

    # Compute the padding to overwrite all text with whitespace
    # Maximum length of the message is width+33+{extra digits before the decimal on the remaining time}
    pad = " " * ( width + 33 + 3 - len(progress_message))

    sys.stdout.write("\r" + progress_message + pad) # Move cursor to the start of the line and print the progress message
    sys.stdout.flush()

    # If it is the final call, print a blank line
    if ii == total:
        print("")

    return

def clear_catchup(filename, links, logger):
    """Deletes the `catchup.txt` file, which contains all links that have been saved over previous runs.

    inputs
    ------
    filename : str
        Path+filename of the `catchup.txt` file.
    links : list
        List containing all arXiv links in the file.

    TO-DO:
    1) This function will delete any file passed to it. Perform a check that the file is actually what we expect. While it is only called after opening all files, there should be a check here just in case.
    """

    # Ask the user if they would like to open the links in the browser. Default is no
    logger.warning("There are {:} links in {:}.".format(len(links), filename))
    user_prompt = input(
                        "    Delete them all? This action cannot be reversed, only do so if the papers have been reviewed. [y/N]: "
                        ).strip().lower()
    
    # If the user says yes, delete the file (it will be recreated later if writing links)
    if user_prompt == "y":

        logger.info("Deleting the file.")

        # Delete the file
        file = pathlib.Path(filename)
        file.unlink()

    # Else, do nothing
    else:

        logger.info("Doing nothing.")

    return