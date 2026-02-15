# Import libraries
import numpy    as np
import argparse
import logging
import pathlib
import sys

class FlushingStreamHandler(logging.StreamHandler):
    def emit(self, record):
        # Flush the current stream
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        # Print message
        super().emit(record)

def cli_args():
    """Defines and parses the CLI arguments passed when running the script.

    outputs
    -------
    args : namespace
        Contains all parsed arguments and their values.
    """

    # Parse command-line arguments
    parser = argparse.ArgumentParser(prog='arXiv Catchup',
                                     description='Searches arXiv for papers matching your criteria.',
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-f', '--force-open', action='store_true',
                        help='Skip all user prompts and open links in the web browser.')
    parser.add_argument('-w', '--write-to-file', action='store_true',
                        help='Skip all user prompts and write all links to a file.')
    parser.add_argument('-n', '--new-window', action='store_true',
                        help='Open all papers in a new browser window as tabs.') # Doesn't work on mac with firefox
    parser.add_argument('-s', '--start-date', type=str,
                        help='Set the start date for the search.\nInput in ISO format, i.e. "YYYY-mm-dd".\nIgnores the date in the `prev_search.txt`.')
    parser.add_argument('-e', '--end-date', type=str,
                        help='Set the end date for the search.\nInput in ISO format, i.e. "YYYY-mm-dd".')
    parser.add_argument('-v', '--verbosity', type=int, default=3,
                        help='Set the verbosity level.\n0 => critical errors\n1 => ... and non-critical errors\n2 => ... and warnings\n3 => ... and info\n4 => ... and debug messages')

    args = parser.parse_args()

    return args

def logger_setup(args):
    """Set up the logger.

    inputs
    ------
    verbosity : int
        Defines the level for the logger.
        0 => only critical errors
        1 => ... and errors
        2 => ... and warnings
        3 => ... and info
        4 => ... and debug

    outputs
    -------
    logger : RootLogger
        The logger object
    """

    # Initialise the logger
    logger = logging.getLogger()

    # Create a custom handler that will ensure the terminal line is cleared before writing messages
    handler = FlushingStreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)

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
    else:
        logger.critical("Verbosity level must be positive.\n")
        raise

    return logger

def progress_bar(ii, total, time_estimate=None):
    """Prints a progress bar that updates as the loop progresses.

    inputs
    ------
    ii            : int
        Current step in the loop.
    total         : int
        Final step in the loop.
    time_estimate : float or None
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
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    return

def delete_catchup(logger, filename, links):
    """Deletes the `catchup.txt` file, which contains all links that have been saved over previous runs.
    NOTE: This function checks to ensure the file is formatted correctly. This was done so that the `open_catchup.py` script can be run on the `catchup.txt` file safely, even after adding (potentially malformed ) links manually.

    inputs
    ------
    logger   : RootLogger
        The logger object
    filename : str
        Path+filename of the `catchup.txt` file.
    links    : list
        List containing all arXiv links in the file.
    """

    # Ask the user if they would like to open the links in the browser. Default is no
    logger.warning("There are {:} links in {:}.".format(len(links), filename))
    user_prompt = input(
                        "         Delete all links? This action cannot be reversed. Only do so if the papers have been reviewed. [y/N]: "
                        ).strip().lower()
    
    # If the user says yes, delete the file
    if user_prompt == "y":

        # Check that the file is of the correct format to prevent deleting some other file
        # Loop through all lines, ensuring they begin with the correct text
        with open(filename, "r") as f:

            for line in f:

                link = line.strip()

                if link[:21] != "http://arxiv.org/abs/":

                    print("")
                    logger.critical("The catchup file is not formatted correctly. Double check its contents manually.\n")
                    raise

        # If the file is of the correct format, delete it
        delete_file(logger, filename)

    # Else, do nothing
    else:

        logger.info("Doing nothing.")

    return

def delete_file(logger, filename):
    """Deletes a file

    inputs
    ------
    logger   : RootLogger
        The logger object.
    filename : str
        Path+filename of the file being deleted.
    """

    logger.info("Deleting file: {:}".format(filename))
    file = pathlib.Path(filename)
    file.unlink()

    return