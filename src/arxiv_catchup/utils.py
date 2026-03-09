"""Utily functions."""

# Import libraries
from importlib.metadata import version
import argparse
import platform
import logging
import pathlib
import sys


__version__ = version("arxiv-catchup")


class FlushingStreamHandler(logging.StreamHandler):  # type: ignore
    """Sets up a logging handler that flushes the line before displaying the log message.

    inputs
    ------
    : The stream handler object
    """

    # Want the default behaviour, except for flushing the line first.
    # Hence, no other methods required.
    # pylint: disable=R0903

    def emit(self, record: logging.LogRecord) -> None:
        """Do whatever it takes to actually log the specified logging record."""
        # Flush the current stream
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        # Print message
        super().emit(record)


def cli_args() -> argparse.Namespace:
    """Defines and parses the CLI arguments passed when running the script.

    outputs
    -------
    args : Contains all parsed arguments and their values.
    """

    # # Parse command-line arguments
    parser = argparse.ArgumentParser(
        prog="arXiv Catchup",
        description="Searches arXiv for papers matching your criteria.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # # Extract the arguments
    # Skip dialogues and open links in browser
    parser.add_argument(
        "-f",
        "--force-open",
        action="store_true",
        help="Skip all user prompts and open links in the web browser.",
    )

    # Open links in a new browswer window
    parser.add_argument(
        "-n",
        "--new-window",
        action="store_true",
        help="Open all papers in a new browser window as tabs.",
    )  # Doesn't work on mac with firefox

    # Skip confirmations and write links to files
    parser.add_argument(
        "-w",
        "--write-to-file",
        action="store_true",
        help="Skip all user prompts and write all links to a file.",
    )

    # If writing links to files, only include the arXiv ID number
    parser.add_argument(
        "--only-ids",
        action="store_true",
        help="Will only write the arXiv ID numbers to the file (if writing).",
    )

    # Keep temp files
    parser.add_argument(
        "-k",
        "--keep-temp",
        action="store_true",
        help="Keep all temporary files.",
    )

    # Manually set the start date of the search
    parser.add_argument(
        "-s",
        "--start-date",
        type=str,
        help=(
            "Set the start date for the search.\n"
            "Input in ISO format, i.e. 'YYYY-mm-dd'.\n"
            "Ignores the date in the `prev_search.txt`."
        ),
    )

    # Manually set the end date of the search
    parser.add_argument(
        "-e",
        "--end-date",
        type=str,
        help='Set the end date for the search.\n"'
        "Input in ISO format, i.e. 'YYYY-mm-dd'.",
    )

    # Chose the scoring algorithm
    # Help message is suppressed as the ML algorithm has not been implemented yet
    # Once implemented, change default to False
    parser.add_argument(
        "--score-on-matches",
        action="store_true",
        # Current default while ML is not implemented
        default=True,  # DEFAULT: True => don't use the ML algorithm and score based on matches
        help=argparse.SUPPRESS,
        # Default once ML is implemented
        # default=False,  # DEFAULT: False => use the ML algorithm to score the papers
        # help="Use the author/word matches to score papers (default: use ML algorithm).",
    )

    # Chose the filtering algorithm
    parser.add_argument(
        "--filter-on-matches",
        action="store_true",
        default=False,  # DEFAULT: False => don't filter on matches and use the score instead
        help="Filter papers based on matches (default: use interest scores).",
    )

    # Choose the verbosity
    parser.add_argument(
        "-v",
        "--verbosity",
        type=int,
        default=3,  # DEFAULT: Info messages
        help="Set the verbosity level.\n"
        "    0 => critical errors\n"
        "    1 => ... and non-critical errors\n"
        "    2 => ... and warnings\n"
        "    3 => ... and info\n"
        "    4 => ... and debug messages",
    )

    args = parser.parse_args()

    return args


def logger_setup(args: argparse.Namespace, filename: pathlib.Path):
    """Set up the logger.
    Writes all messages to a log file, and takes the CLI argument for the terminal logs.

    inputs
    ------
    args     : Command-line arguments
    filename : Path+filename of the log file

    outputs
    -------
    logger : Logger object
    """

    # Initialise the logger
    logger = logging.getLogger()

    # Set the global logging level
    logger.setLevel(logging.DEBUG)

    # Clear the logger handles. Not required, but is good practice
    logger.handlers.clear()

    # Create a handler that will output *all* messages to a file.
    # Will overwrite the file on each execution.
    handler_file = logging.FileHandler(filename, mode="w")
    handler_file.setLevel(logging.DEBUG)
    handler_file.setFormatter(
        logging.Formatter(
            "%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"
        )
    )

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
        logger.warning("Input verbosity was negative. Defaulting to show debug.")

    # Log the location of the log file
    logger.debug("Log file created at: %s", filename)

    # State the verbosity level
    logger.debug(
        "Log file verbosity level set to: %s", logging.getLevelName(logger.level)
    )
    logger.debug(
        "CLI verbosity level set to:      %s", logging.getLevelName(handler_cli.level)
    )

    logger.debug("===============================")

    # Log the environment
    log_environment(logger)

    # Log the passed arguments
    log_args(logger, args)


def log_environment(logger: logging.Logger) -> None:
    """Log some environment and system information.
    NOTE: Only logging package versions that are important and/or not part of the standard library.

    inputs
    ------
    logger : The logger object
    """

    # Print system info
    logger.debug("=== Environment Information ===")
    logger.debug(f"Python: {sys.version}")
    logger.debug(f"Platform: {platform.platform()}")

    # Print project info
    logger.debug(f"arXiv_Catchup=={__version__}")

    # Print package info
    for pkg in ["certifi", "pylatexenc", "PyYAML"]:
        pkg_version = version(pkg)
        logger.debug(f"{pkg}=={pkg_version}")

    logger.debug("===============================")


def log_args(logger: logging.Logger, args: argparse.Namespace) -> None:
    """Log the CLI arguments.

    inputs
    ------
    logger : The logger object
    args   : Command-line arguments
    """

    logger.debug("===== CLI Arg Definitions =====")

    for key, val in vars(args).items():

        logger.debug(f"Argument '{key}' was set to: {val}")

    logger.debug("===============================")


def create_dir(path: pathlib.Path) -> None:
    """Small helper to create a directory and check that it was successful.

    inputs
    ------
    path: Path where the directory should be created.
    """

    # Create the directory
    path.mkdir(parents=True, exist_ok=True)

    # Check the directory was created
    if not path.exists() or not path.is_dir():
        raise RuntimeError(f"Failed to create directory: {path}")
