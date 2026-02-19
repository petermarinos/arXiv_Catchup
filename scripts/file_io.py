# Import classes
from .Corpus import Corpus

# Import functions
from .utils           import progress_bar

# Import libraries
import xml.etree.ElementTree as ET
import numpy                 as np
import webbrowser
import argparse
import datetime
import logging
import time
import os

def read_catchup(logger: logging.Logger, filename: str, sleep_time: float) -> list:
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

    with open(filename, "r") as f:

        for line in f:

            link = line.strip()

            if link[:21] != "http://arxiv.org/abs/":

                print("")
                logger.critical("One or more links in the catchup file is malformed.\n          Found    {:}\n          Expected http://arxiv.org/abs/0123.45678v9 format\n".format(link))
                raise

            links.append(link)

    total = len(links)

    request_count = 0
    for link in links:

        progress_bar(request_count, total, ( total - request_count ) * sleep_time)

        if request_count > 0:
            time.sleep(sleep_time)

        if request_count == 0:

            webbrowser.open(link, new=1)  # new=1: open in a new browser window

        else:

            webbrowser.open(link, new=2)  # new=2: open in a new tab

        request_count += 1

    progress_bar(total, total)

    return links

def write_links(args: argparse.Namespace, logger: logging.Logger, filename: str, corpus: Corpus) -> None:
    """Write all links to the `catchup.txt` file.

    inputs
    ------
    args           : CLI arguments.
    logger         : The logger object.
    filename       : Path+filename of the `catchup.txt` file.
    corpus         : Contains all papers and their information.
    papers_of_note : Contains the arxiv IDs of all interesting papers.
    """

    logger.info("Writing all links to the end of the file: {:}".format(filename))

    with open(filename, "a+", encoding="utf-8") as f:

        for arxiv_id in corpus.papers_of_note:

            if args.only_ids:
            
                f.write(f"{arxiv_id}\n")

            else:

                link = corpus.corpus[arxiv_id].paperInfo.link_abs
            
                f.write(f"{link}\n")

    return

def write_xml(logger: logging.Logger, filename: str, xml_data: ET.Element, ns: dict[str, str], overwrite: bool=False) -> None:
    """Writes an XML to a .xml file.

    inputs
    ------
    logger    : The logger object.
    filename  : Path+filename of the `.xml` file.
    xml       : XML data from the arXiv queries.
    ns        : XML namespaces that arXiv uses.
    overwrite : File will be overwritten if True.
    """

    # As these files are not meant to be touched by the user, and are deleted at the end, logging messages are set to debug

    if overwrite:

        logger.debug("Saving xml to file: {:}".format(filename))
        tree = ET.ElementTree(xml_data)
        tree.write(filename, encoding="utf-8")

    else:

        # check if the file exists
        if not os.path.exists(filename):

            # Write the xml
            write_xml(logger, filename, xml_data, ns, overwrite=True)

            return

        else:

            logger.debug("Appending xml to file {:}".format(filename))

            # Load the file
            master_tree = ET.parse(filename)
            master_root = master_tree.getroot()

            new_tree = ET.ElementTree(xml_data)
            new_root = new_tree.getroot()

            # Obtain each entry and append to the file
            if new_root is None:
                logger.critical("Malformed or corrupted .xml from arXiv. It returned None.\n")
                raise
            for entry in new_root.findall("atom:entry", ns):
                master_root.append(entry)

            # Write the new file
            master_tree.write(filename, encoding="utf-8", )

    return

def write_date(logger: logging.Logger, filename: str, date: datetime.date) -> None:
    """Write a datetime.date object to a file.
    While the current implementation only uses this to write Papers.start_date to Papers.paths['prevsearch'], this function is left as-is.

    inputs
    ------
    logger   : The logger object.
    filename : Path+filename of the `prev_search.txt` file.
    date     : Date that is being written
    """

    logger.info("Writing the date {:} to the file: {:}.".format(date, filename))

    with open(filename, "w") as f:

        f.write(date.isoformat())

    return