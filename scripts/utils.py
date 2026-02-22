"""Utily functions."""

# fmt: off
# Import libraries
from importlib import metadata
import argparse
import platform
import logging
import pathlib
import sys

# Import version number
from scripts import __version__
# fmt: on


class FlushingStreamHandler(logging.StreamHandler):
    """Sets up a logging handler that flushes the line before displaying the log message.

    inputs
    ------
    : The stream handler object
    """

    def emit(self, record):
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

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        prog="arXiv Catchup",
        description="Searches arXiv for papers matching your criteria.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-f",
        "--force-open",
        action="store_true",
        help="Skip all user prompts and open links in the web browser.",
    )
    parser.add_argument(
        "-w",
        "--write-to-file",
        action="store_true",
        help="Skip all user prompts and write all links to a file.",
    )
    parser.add_argument(
        "--only-ids",
        action="store_true",
        help="Will only write the arXiv ID numbers to the file (if writing).",
    )
    parser.add_argument(
        "-n",
        "--new-window",
        action="store_true",
        help="Open all papers in a new browser window as tabs.",
    )  # Doesn't work on mac with firefox
    parser.add_argument(
        "-s",
        "--start-date",
        type=str,
        help=(
            "Set the start date for the search.\n"
            + "Input in ISO format, i.e. 'YYYY-mm-dd'.\n"
            + "Ignores the date in the `prev_search.txt`."
        ),
    )
    parser.add_argument(
        "-e",
        "--end-date",
        type=str,
        help='Set the end date for the search.\n"'
        + "Input in ISO format, i.e. 'YYYY-mm-dd'.",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        type=int,
        default=3,
        help="Set the verbosity level.\n"
        + "0 => critical errors\n"
        + "1 => ... and non-critical errors\n"
        + "2 => ... and warnings\n"
        + "3 => ... and info\n"
        + "4 => ... and debug messages",
    )

    args = parser.parse_args()

    return args


def logger_setup(args: argparse.Namespace, root_dir: pathlib.Path) -> logging.Logger:
    """Set up the logger.
    Writes all messages to a log file, and takes the CLI argument for the terminal logs.

    inputs
    ------
    args     : Command-line arguments
    root_dir : Path to the project

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
    handler_file = logging.FileHandler(root_dir / "catchup.log", mode="w")
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

    return logger


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
    for pkg in ["certifi", "numpy", "pylatexenc", "PyYAML"]:
        version = metadata.version(pkg)
        logger.debug(f"{pkg}=={version}")

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


def set_filenames(root_dir: pathlib.Path) -> dict[str, pathlib.Path]:
    """Compute the filenames of various auxiliary files that may or may not be used.

    inputs
    ------
    root_dir : Top directory of the project, i.e. `/path/to/arXiv_Catchup/`.

    outputs
    -------
    filenames : Contains the path+filename for the various aux./temp. files.
    """

    # Place filenames into a dictionary
    filenames = {
        # File that stores the date of the previous run
        "prevsearch": root_dir / "prev_search.txt",
        # File that stores the search terms
        "searchterms": root_dir / "search_terms.yaml",
        # File that stores the links to the papers of interest (if writing to a file)
        "catchup": root_dir / "catchup.txt",
        # File that stores the .xml data of the initial arXiv query, i.e. critical search info
        "searchxml": root_dir / "search.xml",
        # File that stores the .xml data for all downloaded papers
        "papersxml": root_dir / "papers.xml",
    }

    return filenames


def delete_catchup(
    logger: logging.Logger, filename: pathlib.Path, links: list[str]
) -> None:
    """Deletes the `catchup.txt` file (contains all links that have been saved over previous runs)
    NOTE: This function checks to ensure the file is formatted correctly to prevent deletions when
          users manually alter the file, or if the CLI option to only output the ID numbers is used.

    inputs
    ------
    logger   : The logger object
    filename : Path+filename of the `catchup.txt` file.
    links    : List containing all arXiv links in the file.
    """

    # Ask the user if they would like to open the links in the browser. Default is no
    logger.warning(f"There are {len(links)} links in {filename}.")
    user_prompt = (
        input(
            "         Delete all links? This action cannot be reversed. "
            + "Only do so if the papers have been reviewed. [y/N]: "
        )
        .strip()
        .lower()
    )

    # If the user says yes, delete the file
    if user_prompt == "y":

        # Check that the file is of the correct format to prevent deleting some other file
        # Loop through all lines, ensuring they begin with the correct text
        with open(filename, "r", encoding="utf8") as f:

            for line in f:

                link = line.strip()

                if link[:21] != "http://arxiv.org/abs/":

                    print("")
                    logger.exception(
                        "The catchup file is not formatted correctly. "
                        + "Double check its contents manually.\n"
                    )
                    raise ValueError("Malformed catchup file.")

        # If the file is of the correct format, delete it
        delete_file(logger, filename)

    # Else, do nothing
    else:

        logger.info("Doing nothing.")


def delete_file(logger: logging.Logger, filename: pathlib.Path) -> None:
    """Deletes a file.

    inputs
    ------
    logger   : The logger object.
    filename : Path+filename of the file being deleted.
    """

    logger.info(f"Deleting file: {filename}")
    file = pathlib.Path(filename)
    file.unlink()
