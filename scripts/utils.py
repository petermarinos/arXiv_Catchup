# Import version number
from scripts import __version__

# Import libraries
import importlib.metadata as metadata
import numpy              as np
import argparse
import platform
import logging
import pathlib
import random
import time
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

def logger_setup(args, cdir):
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

    # Set the global logging level
    logger.setLevel(logging.DEBUG)

    # Clear the logger handles. Not required, but is good practice
    logger.handlers.clear()

    # Create a handler that will output *all* messages to a file. Will overwrite the file on each execution.
    handler_file = logging.FileHandler(cdir+"/catchup.log", mode="w")
    handler_file.setLevel(logging.DEBUG)
    handler_file.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"))

    # Create a custom handler that will ensure the terminal line is cleared before writing messages
    handler_cli = FlushingStreamHandler(sys.stdout)
    handler_cli.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    # Set the logging level for the CLI output
    if args.verbosity == 0:
        handler_cli.setLevel(logging.CRITICAL)
    elif args.verbosity == 1:
        handler_cli.setLevel(logging.ERROR)
    elif args.verbosity == 2:
        handler_cli.setLevel(logging.WARNING)
    elif args.verbosity == 3:
        handler_cli.setLevel(logging.INFO)
    elif args.verbosity >= 4:
        handler_cli.setLevel(logging.DEBUG)

    # Add both the CLI and file handlers to the logger
    logger.addHandler(handler_file)
    logger.addHandler(handler_cli)

    # Warn if a negative verbosity was entered on the CLI
    if args.verbosity < 0:
        logger.warning("Input verbosity was negative. Defaulting to show debug.".format(logger.level))

    # State the verbosity level
    logger.debug("CLI verbosity level set to: {:}".format(logging.getLevelName(handler_cli.level)))
    logger.debug("Log file verbosity level set to: {:}".format(logging.getLevelName(logger.level)))

    logger.debug("===============================")

    # Log the environment
    log_environment(logger)

    # Log the passed arguments
    log_args(logger, args)

    return logger

def log_environment(logger):
    """Log some environment and system information.
    NOTE: Only logging packages that are important and/or not part of the standard library.

    inputs
    ------
    logger : RootLogger
        The logger object
    """

    # Print system info
    logger.debug("=== Environment Information ===")
    logger.debug(f"Python: {sys.version}")
    logger.debug(f"Platform: {platform.platform()}")

    # Print project info
    logger.debug(f"arXiv_Catchup=={__version__}")

    # Print package info
    for pkg in ["certifi", "numpy", "pandas", "pylatexenc", "PyYAML"]:
        version = metadata.version(pkg)
        logger.debug(f"{pkg}=={version}")

    logger.debug("===============================")

    return

def log_args(logger, args):

    logger.debug("===== CLI Arg Definitions =====")

    for key,val in vars(args).items():

        logger.debug("Argument '{:}' was set to: {:}".format(key, val))

    logger.debug("===============================")

    return

def progress_bar(ii: int,
                 total: int,
                 time_estimate: float | None = None) -> None:
    """Prints a progress bar that updates as the loop progresses.

    inputs
    ------
    ii            : Current step in the loop.
    total         : Final step in the loop.
    time_estimate : Estimate of the remaining time of the loop.
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

def pretty_sleep(logger, sleep_time):
    """Shows a progress bar if sleeping for a long time.
    NOTE: Also adds jitter.

    inputs
    ------
    time : float
        Time to sleep for
    """

    # Add jitter
    sleep_time = sleep_time + random.uniform(0, 0.3)
    logger.debug("Sleeping for {:.3f} seconds ...".format(sleep_time))

    # If sleeping for a short time (under 5s), do a normal sleep
    if sleep_time <= 5:
        time.sleep(sleep_time)

    # If sleeping for a long time, show a progress bar
    else:
        # Flush any already-existing progress bar
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

        # Update the bar every 0.1s
        # n_msecs = sleep_time * 1000
        n_steps = int( np.ceil( sleep_time * 10 ) )
        for ii in range(0, n_steps):

            progress_bar(ii, n_steps, 0.1 * ( n_steps - ii ))
            time.sleep(0.1)

        progress_bar(n_steps, n_steps)

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