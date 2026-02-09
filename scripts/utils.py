# Import libraries
import numpy as np

import argparse
import pathlib
import yaml
import sys

def cli_args():

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

    args = parser.parse_args()

    return args

def load_searchterms(filename):

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
        print("Searching the {:} categories".format(cat_printstring))

    # If a category with a wildcard (e.g. astro-ph*) is entered with other matching sub-categories (e.g. astro-ph.HE), the API will ignore the sub-categories
    # No need to catch it here

    # At least one search term is required in the "Words" key
    if search_terms["Included Words"] is None:

        raise ValueError("No search terms were found in the 'Included Words' entry in the configuration file.\n            Please check the file and add at least one item")

    # No search terms are required for the "Authors" or "Excluded Words" keys
    # Warn the user if no terms are found
    if search_terms["Authors"] is None:

        print("WARNING: No search terms were found in the 'Authors' entry in the configuration file.")

    if search_terms["Excluded Words"] is None:

        print("WARNING: No search terms were found in the 'Excluded Words' entry in the configuration file.")

    return search_terms, cat_urlstring

def progress_bar(ii, total, time_estimate=None):
    """Print a progress bar that updates
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

    return

def clear_catchup(filename, links):

    # Ask the user if they would like to open the links in the browser. Default is no
    user_prompt = input(
                        "WARNING: There are {:} links in {:}.\n         Delete them all? This action cannot be reversed, only do so if the papers have been reviewed. [y/N]: ".format(len(links), filename)
                        ).strip().lower()
    
    # If the user says yes, delete the file (it will be recreated later if writing links)
    if user_prompt == "y":

        print("Deleting the file.")

        # Delete the file
        file = pathlib.Path(filename)
        file.unlink()

    # Else, do nothing
    else:

        print("Doing nothing.")

    return