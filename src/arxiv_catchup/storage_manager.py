"""Storage manager."""

# Import standard libraries
from dataclasses import dataclass
from enum import Enum
import xml.etree.ElementTree as ET
import argparse
import datetime
import logging
import pathlib
import typing
import sys

# Import non-standard libraries
import yaml

# Import functions
from .string_handling import normalise_string
from .xml_handling import XmlReadError
from .dates import calc_search_endtime, parse_date
from .utils import create_dir


class SearchTermReadError(Exception):
    """Exception raised if information cannot be extracted from the search_term.yaml file.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


# Define some small classes. Bounds the expected values and prevents errors within strings.
class YamlFields(Enum):
    """Define the fields that we extract from the configuration .yaml."""

    CATEGORIES = "categories"
    AUTHORS = "authors"
    INCLUDED = "included_words"
    EXCLUDED = "excluded_words"


@dataclass
class SearchTerms:
    """Create a typed dictionary for the search terms. Ensures type checkers know that the category
    field *must* be included.
    """

    categories: list[str]
    authors: list[str]
    included_words: list[str]
    excluded_words: list[str]


@dataclass
class Paths:
    """Holds all paths."""

    log: pathlib.Path
    previous_date: pathlib.Path
    search_terms: pathlib.Path
    catchup: pathlib.Path
    search_xml: pathlib.Path
    papers_xml: pathlib.Path


class Storage:
    """Storage manager to perform all file I/O."""

    def __init__(self) -> None:
        """Create the object that holds all paths."""

        # Find the root path
        # .resolve().parent gives the location of this file.
        # Go up an additional two directories to get to /path/to/arXiv_Catchup/
        root_dir = pathlib.Path(__file__).resolve().parent.parent.parent

        if not root_dir.is_dir():
            raise ValueError(f"{root_dir} is not a valid directory.")

        self.logger: logging.Logger

        config_dir = root_dir / "config"
        state_dir = root_dir / ".run" / "state"
        out_dir = root_dir / ".run" / "outputs"
        log_dir = root_dir / ".run" / "logs"
        tmp_dir = root_dir / ".run" / "tmp"

        script_name = pathlib.Path(sys.argv[0]).stem
        script_dir = str(pathlib.Path(sys.argv[0]).parent.name)
        if script_name == "__main__":
            if script_dir == "arxiv_catchup":
                logfile_name = "main.log"
            elif script_dir == "gui":
                logfile_name = "gui.log"
            else:
                raise RuntimeError("Unknown entry point")
        else:
            logfile_name = f"{script_name}.log"

        self.paths = Paths(
            log=log_dir / logfile_name,
            previous_date=state_dir / "prev_search.txt",
            search_terms=config_dir / "search_terms.yaml",
            catchup=out_dir / "catchup.txt",
            search_xml=tmp_dir / "search.xml",
            papers_xml=tmp_dir / "papers.xml",
        )

        # Check that the config file exists
        if not self.paths.search_terms.exists():
            raise RuntimeError(f"Could not find config file: {self.paths.search_terms}")

        # Create directories (if they don't already exist)
        create_dir(state_dir)
        create_dir(log_dir)
        create_dir(out_dir)
        create_dir(tmp_dir)

    def add_logger(self) -> None:
        """
        Setting up the logger requires knowlegde of this Storage manager.
        Add the logger object to this class for future log messages.
        """

        # Obtain the logger
        self.logger = logging.getLogger(__name__)

    def read_search_term_file(self) -> SearchTerms:
        """Loads the user-defined search terms from the `search_terms.yaml` into a dictionary.
        Performs some basic checks on the data.

        outputs
        -------
        search_terms : The terms that will be searched for in the matching/scoring algorithms.
        """

        # 14 branches to load the information and perform all error checks and cleaning
        # Do not view it as worthwhile to split the function at this point
        # Disable Pylint warning for >12 branches
        # pylint: disable=R0912

        self.logger.info("Loading search terms from %s", self.paths.search_terms)

        # Load the .yaml into a dictionary
        with open(self.paths.search_terms, "r", encoding="utf8") as f:

            raw_search_terms = yaml.safe_load(f)

        # Extract the fields from the .yaml that we require

        # # CATEGORIES

        # At least one category is required
        if raw_search_terms[YamlFields.CATEGORIES.value] is None:

            self.logger.critical(
                "No search terms were found in the 'categories' entry in the configuration file.\n"
                "          Please check the file and add at least one item.\n"
            )
            raise SearchTermReadError(
                "No search categories found. Add atleast one to the .yaml."
            )

        # Remove duplicates, but preserve order from the config file
        cats = list(dict.fromkeys(raw_search_terms[YamlFields.CATEGORIES.value]))

        # # AUTHORS

        # If no authors, warn the use
        if raw_search_terms[YamlFields.AUTHORS.value] is None:

            self.logger.warning("No 'authors' found in the configuration file.")
            authors = []

        # Normalise author strings and remove duplicates
        else:

            # Remove duplicates, but preserve order from the config file
            raw_authors = [
                normalise_string(a) for a in raw_search_terms[YamlFields.AUTHORS.value]
            ]
            authors = list(dict.fromkeys(raw_authors))

            # Print debug info
            for author in authors:

                self.logger.debug("Found author: %s", author)

        # # INCLUDED WORDS

        # If no included words are found, warn the user
        if raw_search_terms[YamlFields.INCLUDED.value] is None:

            self.logger.warning("No 'included_words' found in the configuration file.")

            inc_words = []

        # Otherwise, remove duplicates and log all found included words
        else:

            # Remove duplicates and sort
            raw_inc_words = list(raw_search_terms[YamlFields.INCLUDED.value])
            inc_words = sorted(set(raw_inc_words))

            for included_word in inc_words:

                self.logger.debug("Found included word: %s", included_word)

        # # EXCLUDED WORDS

        # If no excluded words are found, warn the user
        if raw_search_terms[YamlFields.EXCLUDED.value] is None:

            self.logger.warning(
                "No 'excluded_words' were found in the configuration file."
            )
            exc_words = []

        # Otherwise, remove duplicates and log all found excluded words
        else:

            # Remove duplicates and sort
            raw_exc_words = list(raw_search_terms[YamlFields.EXCLUDED.value])
            exc_words = sorted(set(raw_exc_words))

            for excluded_word in exc_words:

                self.logger.debug("Found excluded word: %s", excluded_word)

        # Check to see if any word is in both the 'included' and 'excluded fields
        for inc_word in inc_words:

            if inc_word in exc_words:

                self.logger.warning(
                    "The term '%s' appears in both the Included and Excluded fields.",
                    inc_word,
                )

        # Ensure that there is at least one search term between the 'authors' and '_words' fields.
        if len(authors) == 0 and len(inc_words) == 0 and len(exc_words) == 0:

            self.logger.critical(
                "No search terms were found between the 'authors', 'included_words', and "
                "'excluded_words' entries in the configuration file.\n"
                "          Please check the file and add at least one item to at least one of "
                "these fields.\n"
            )
            raise SearchTermReadError(
                "No search terms found. Add atleast one to the .yaml."
            )

        search_terms = SearchTerms(
            categories=cats,
            authors=authors,
            included_words=inc_words,
            excluded_words=exc_words,
        )

        return search_terms

    def read_catchup_file(self) -> list[str]:
        """Read the catchup file.

        outputs
        -------
        links : Contains all arXiv paper links from the `catchup.txt` file.
        """

        links: list[str] = []

        with open(self.paths.catchup, "r", encoding="utf8") as f:

            for line in f:

                link = line.strip()

                if link[:22] != "https://arxiv.org/abs/":

                    self.logger.critical(
                        "Found:    %s\n"
                        "          Expected: https://arxiv.org/abs/0123.45678v9 format\n",
                        link,
                    )
                    raise ValueError(
                        "One or more links in the catchup file is malformed."
                    )

                id_num = link[22:]
                self.logger.debug("Found %s with link: %s", id_num, link)
                links.append(id_num)

        return links

    def read_xml_file(
        self,
        ns: dict[str, str],
        expected_url: str,
        search: bool,
    ) -> ET.ElementTree:
        """Read an .xml file and check to ensure it matches the current expected search parameters.

        inputs
        ------
        ns           : arXiv namespaces for the xml file.
        expected_url : The url that we expect in the xml file given the search parameters
        search       : Flag, True if for the search xml, False for the papers xml.
        """

        # If we are operating on the search XML
        if search:

            filename = self.paths.search_xml

        else:

            filename = self.paths.papers_xml

        # Load the file
        try:
            xml_tree = typing.cast(ET.ElementTree, ET.parse(filename))
        except ET.ParseError as e:
            self.logger.critical("Could not parse XML: %s", e)
            raise XmlReadError(f"Malformed XML file: {filename}") from e

        # Check the url from the loaded xml matches the current search url
        # Extract the url from the xml. It will *always* be the first link
        returned_urlblock = xml_tree.find("atom:link", ns)
        if returned_urlblock is None:
            self.logger.critical(
                "arXiv data did not include a search link. It is corrupted (returned None).\n"
            )
            raise XmlReadError("Malformed search link.")
        returned_url = returned_urlblock.attrib["href"]

        url_mismatch = expected_url != returned_url

        # If the urls do not match, discard and restart the search
        if url_mismatch:

            self.logger.warning(
                "The .xml file information does not match the current search. "
                "Discarding the file and re-connecting."
            )
            self.logger.debug("Expected: %s", expected_url)
            self.logger.debug("Found:    %s", returned_url)

            # Clear the .xml file
            self.delete_file(filename)

        else:

            self.logger.debug(
                "The .xml file information matches the current search. Continuing."
            )

        return xml_tree

    def read_previous_date_file(
        self,
        end_time: datetime.datetime,
        search_time: datetime.time,
        post_time: datetime.time,
    ) -> tuple[datetime.datetime, datetime.date]:
        """Read the previous search date from a file.

        inputs
        ------
        end_time    : End date+time for the previous search.
        search_time : Time that the searches start/end at.
        post_time   : Time that the daily lists are posted.
        """

        self.logger.debug("No start date was input.")

        # If the file doesn't exist:
        if not self.paths.previous_date.exists():

            self.logger.debug(
                "No previous search file found. Setting to the day prior to the end_date."
            )

            # Compute the list time before the previous by passing the end_time found above
            #     into the calc_search_endtime() function
            prev_end_time = calc_search_endtime(end_time, search_time, post_time)

            self.write_previous_date_file(prev_end_time.date())

        # The file is now guaranteed to exist. Load it and extract the previous runtime
        # File should only be one line. Only read the first.
        with open(self.paths.previous_date, "r", encoding="utf-8") as f:

            raw_date = f.readline()

            # Do an error check. Should never error.
            if len(raw_date) != 10:
                raise ValueError(
                    f"Corrupted previous date file: {self.paths.previous_date}"
                )

            start_time, start_date = parse_date(
                self.logger, raw_date, "start-date", search_time, post_time
            )

        return start_time, start_date

    def write_catchup_file(
        self,
        args: argparse.Namespace,
        papers_of_note: list[str],
    ) -> None:
        """Write all links to the `catchup.txt` file.

        inputs
        ------
        args           : CLI arguments.
        papers_of_note : Contains the arxiv IDs of all interesting papers.
        """

        self.logger.info(
            "Writing all links to the end of the file: %s", self.paths.catchup
        )

        with open(self.paths.catchup, "a+", encoding="utf-8") as f:

            for arxiv_id in papers_of_note:

                if args.only_ids:

                    f.write(f"{arxiv_id}\n")

                else:

                    link = f"https://arxiv.org/abs/{arxiv_id}"

                    f.write(f"{link}\n")

    def write_xml_file(
        self, xml_root: ET.Element, ns: dict[str, str], search: bool
    ) -> None:
        """Write the xml data to a file.
        NOTE: We always want to overwrite the search XML.
              We always want to append to the papers XML if it exists, else create it.

        inputs
        ------
        xml_root : The root of the xml data to write to a file.
        ns       : arXiv XML namespaces.
        search   : Flag, True if for the search xml, False for the papers xml.
        """

        # If we are operating on the search XML
        if search:

            self.logger.debug("Saving xml to file: %s", self.paths.search_xml)
            tree = ET.ElementTree(xml_root)
            tree.write(self.paths.search_xml, encoding="utf-8")

        # If we are operating on the papers XML
        else:

            # check if the file exists
            if not self.paths.papers_xml.exists():

                self.logger.debug("Saving xml to file: %s", self.paths.papers_xml)
                tree = ET.ElementTree(xml_root)
                tree.write(self.paths.papers_xml, encoding="utf-8")

            else:

                self.logger.debug("Appending xml to file %s", self.paths.papers_xml)

                # Load the contents of the file
                master_tree = ET.parse(self.paths.papers_xml)
                master_root = master_tree.getroot()

                # Append each new entry to the file
                for entry in xml_root.findall("atom:entry", ns):

                    # Append each entry from the input onto the master_root (i.e. the xml loaded
                    #     from the file). Note that master_root is a reference to master_tree, so
                    #     appending an entry to master_root also appends it to master_tree.
                    master_root.append(entry)

                # Write the new file
                master_tree.write(
                    self.paths.papers_xml,
                    encoding="utf-8",
                )

    def write_previous_date_file(self, date: datetime.date) -> None:
        """Write the previous search date to a file.

        inputs
        ------
        date     : Date that is being written
        """

        self.logger.info(
            "Writing the date %s to the file: %s", date, self.paths.previous_date
        )

        with open(self.paths.previous_date, "w", encoding="utf8") as f:

            f.write(date.isoformat())

    def write_aux_files(self, end_date: datetime.date, n_papers: int) -> None:
        """Write the auxiliary files.
        The only file currently written is for the previous search date.

        end_date : The end_date of the current search.
        n_papers : The number of papers found in the search.
        """

        # Check if any papers were found
        if n_papers == 0:

            self.logger.warning(
                "As no papers were found, the date file was not updated"
            )

        # If papers were found, update the date file
        else:

            # Write the end date of the search to a file for the next run
            self.write_previous_date_file(end_date)

    def delete_file(self, filename: pathlib.Path) -> None:
        """Deletes a file.
        NOTE: Will delete ANY file passed to it.

        inputs
        ------
        logger   : The logger object.
        filename : Path+filename of the file being deleted.
        """

        self.logger.info("Deleting file: %s", filename)
        file = pathlib.Path(filename)

        # Check if file exists. If it does, delete, otherwise do nothing.
        if file.exists():
            file.unlink()
        else:
            self.logger.debug("Could not find file, skipping delete operation.")

    def delete_temp_files(self, keep_flag: bool) -> None:
        """Clear the temporary files created by the script.

        inputs
        ------
        keep_flag : Delete temp files if false, otherwise keep the temp files.
        """

        # Only delete the files if keep_flag is False
        if not keep_flag:

            self.delete_file(self.paths.search_xml)
            self.delete_file(self.paths.papers_xml)

        else:

            self.logger.info("Not deleting temporary files.")

    def delete_catchup_file(self, delete_flag: bool) -> None:
        """Deletes the `catchup.txt` file (contains all links that have been saved over previous
        runs). Only used by the auxiliary script `open_catchup.py`.
        NOTE: This function checks to ensure the file is formatted correctly to prevent deletions
              when users manually alter the file, or if the CLI option to only output the ID
              numbers is used.

        inputs
        ------
        delete_flag : If True, delete file, otherwise do nothing
        """

        # If the user says yes, delete the file
        if delete_flag:

            self.logger.debug("Deleting file: %s", self.paths.catchup)

            # Check that the file is of the correct format to prevent deleting some other file
            # Loop through all lines, ensuring they begin with the correct text
            with open(self.paths.catchup, "r", encoding="utf8") as f:

                for line in f:

                    link = line.strip()

                    if link[:22] != "https://arxiv.org/abs/":

                        self.logger.critical(
                            "The catchup file is not formatted correctly. "
                            "Double check its contents manually.\n"
                        )
                        raise ValueError("Malformed catchup file.")

            # If the file is of the correct format, delete it
            self.delete_file(self.paths.catchup)

        # Else, do nothing
        else:

            self.logger.info("Doing nothing.")
