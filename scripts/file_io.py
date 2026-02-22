"""Functions for file I/O operations."""

# Import standard libraries
import xml.etree.ElementTree as ET
import webbrowser
import argparse
import datetime
import logging
import pathlib
import time
import os

# Import functions
from .ui import progress_bar


def read_catchup(
    logger: logging.Logger, filename: pathlib.Path, sleep_time: float
) -> list:
    """Read the `catchup.txt` file and open all links in the browser.

    inputs
    ------
    logger     : The logger object.
    filename   : Path_filename of the `catchup.txt` file.
    sleep_time : Wait time between opening links in the browser.

    outputs
    -------
    links : Contains all arXiv paper links from the `catchup.txt` file.
    """

    links = []

    with open(filename, "r", encoding="utf8") as f:

        for line in f:

            link = line.strip()

            if link[:21] != "http://arxiv.org/abs/":

                print("")
                logger.exception(
                    f"Found:    {link}\nExpected: http://arxiv.org/abs/0123.45678v9 format\n"
                )
                raise ValueError("One or more links in the catchup file is malformed.")

            links.append(link)

    total = len(links)

    request_count = 0
    for link in links:

        progress_bar(request_count, total, (total - request_count) * sleep_time)

        if request_count > 0:
            time.sleep(sleep_time)

        if request_count == 0:

            webbrowser.open(link, new=1)  # new=1: open in a new browser window

        else:

            webbrowser.open(link, new=2)  # new=2: open in a new tab

        request_count += 1

    progress_bar(total, total)

    return links


def write_aux_files(
    logger: logging.Logger,
    filename: pathlib.Path,
    end_date: datetime.date,
    n_papers: int,
) -> None:
    """Write the auxiliary files.
    The only file currently written is for the previous search date.

    logger   : The root logger object..
    filename : Filename+path for the auxiliary file.
    end_date : The end_date of the current search.
    n_papers : The number of papers found in the search.
    """

    # Check if any papers were found
    if n_papers == 0:

        logger.warning("As no papers were found, the date file was not updated")

    # If papers were found, update the date file
    else:

        # Write the end date of the search to a file for the next run
        write_date(logger, filename, end_date)


def write_links(
    logger: logging.Logger,
    args: argparse.Namespace,
    papers_of_note: list[str],
    filename: pathlib.Path,
) -> None:
    """Write all links to the `catchup.txt` file.

    inputs
    ------
    logger         : The logger object.
    args           : CLI arguments.
    papers_of_note : Contains the arxiv IDs of all interesting papers.
    filename       : Path+filename of the `catchup.txt` file.
    """

    logger.info("Writing all links to the end of the file: {filename}")

    with open(filename, "a+", encoding="utf-8") as f:

        for arxiv_id in papers_of_note:

            if args.only_ids:

                f.write(f"{arxiv_id}\n")

            else:

                link = "https://arxiv.org/abs/" + arxiv_id

                f.write(f"{link}\n")


def write_xml(
    logger: logging.Logger,
    filename: pathlib.Path,
    xml_data: ET.Element,
    ns: dict[str, str],
    overwrite: bool = False,
) -> None:
    """Writes an XML to a .xml file.

    inputs
    ------
    logger    : The logger object.
    filename  : Path+filename of the `.xml` file.
    xml       : XML data from the arXiv queries.
    ns        : XML namespaces that arXiv uses.
    overwrite : File will be overwritten if True.
    """

    # Logging messages set to debug in this function
    # The files are not meant to be touched by the user and are deleted at the end

    if overwrite:

        logger.debug(f"Saving xml to file: {filename}")
        tree = ET.ElementTree(xml_data)
        tree.write(filename, encoding="utf-8")

    else:

        # check if the file exists
        if not os.path.exists(filename):

            # Write the xml
            write_xml(logger, filename, xml_data, ns, overwrite=True)

            return

        logger.debug(f"Appending xml to file {filename}")

        # Load the file
        master_tree = ET.parse(filename)
        master_root = master_tree.getroot()

        new_tree = ET.ElementTree(xml_data)
        new_root = new_tree.getroot()

        # Obtain each entry and append to the file
        if new_root is None:
            logger.exception(
                "Malformed or corrupted .xml from arXiv. It returned None."
            )
            raise TypeError("Malformed or corrupted .xml from arXiv. It returned None.")
        for entry in new_root.findall("atom:entry", ns):
            master_root.append(entry)

        # Write the new file
        master_tree.write(
            filename,
            encoding="utf-8",
        )

    return


def write_date(
    logger: logging.Logger, filename: pathlib.Path, date: datetime.date
) -> None:
    """Write a datetime.date object to a file.

    inputs
    ------
    logger   : The logger object.
    filename : Path+filename of the `prev_search.txt` file.
    date     : Date that is being written
    """

    logger.info(f"Writing the date {date} to the file: {filename}.")

    with open(filename, "w", encoding="utf8") as f:

        f.write(date.isoformat())
