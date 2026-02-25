"""Functions to handle .xml files."""

# Import libraries
import xml.etree.ElementTree as ET
import logging
import re

# Import functions
from .string_handling import normalise_string


def extract_paper_id_version(
    logger: logging.Logger, ns: dict[str, str], entry: ET.Element
) -> tuple[str, int, str, str, bool]:
    """Extract the arXiv ID and version numbers, updated/published dates, and compute if the paper
    is a revision.

    inputs
    ------
    logger : The logger object.
    ns     : XML namespaces used by arXiv.
    entry  : The paper's entry in the .xml data.
    """

    # Extract the arXiv ID number
    arxiv_id = entry.find("atom:id", ns)

    if arxiv_id is None or arxiv_id.text is None:

        logger.critical("Could not extract the arXiv ID number.\n")

        raise TypeError("Malformed arXiv ID number.")

    id_num = arxiv_id.text.split("/")[-1][:10]
    version = int(arxiv_id.text.split("/")[-1][11:])

    logger.debug(f"arXiv ID: {id_num}, version: {version}")

    # Extract the updated datetime
    raw_updated = entry.find("atom:updated", ns)

    if raw_updated is None or raw_updated.text is None:

        logger.critical("Could not extract the updated date.\n")

        raise TypeError("Malformed updated date")

    updated = raw_updated.text

    logger.debug(f"Updated on: {updated}")

    # Extract the published datetime
    raw_published = entry.find("atom:published", ns)

    if raw_published is None or raw_published.text is None:

        logger.critical("Could not extract the published date.\n")

        raise TypeError("Malformed published date.")

    published = raw_published.text

    logger.debug(f"Published on: {published}")

    # Derive the revised flag
    revised = (updated > published) or (version > 1)

    logger.debug(f"Revised: {revised}")

    return id_num, version, updated, published, revised


def extract_paper_links(
    logger: logging.Logger, ns: dict[str, str], entry: ET.Element
) -> tuple[str, str]:
    """Extract the arXiv abs/pdf links.

    inputs
    ------
    logger : The logger object.
    ns     : XML namespaces used by arXiv.
    entry  : The paper's entry in the .xml data.
    """

    # Extract the link to the pdf page
    links = entry.findall("atom:link", ns)

    if len(links) < 2:

        logger.critical("Could not find all urls.\n")

        raise ValueError("Malformed urls (could not find required urls).")

    link_abs = None  # ensure type checkers know they are strings
    link_pdf = None  # ensure type checkers know they are strings

    for link in links:

        attrs = link.attrib

        if attrs.get("rel") == "alternate" and attrs.get("type") == "text/html":

            link_abs = attrs.get("href")

        elif (
            attrs.get("rel") == "related"
            and attrs.get("type") == "application/pdf"
            and attrs.get("title") == "pdf"
        ):

            link_pdf = attrs.get("href")

    if link_abs is None:

        logger.critical("Could not find the abstract url.\n")

        raise TypeError("Malformed abs url")

    if link_pdf is None:

        logger.critical("Could not find the .pdf url.\n")

        raise TypeError("Malformed pdf url")

    logger.debug(f"Main page: {link_abs}")
    logger.debug(f".pdf page: {link_pdf}")

    return link_abs, link_pdf


def extract_paper_textfields(
    logger: logging.Logger, ns: dict[str, str], entry: ET.Element
) -> tuple[str, str, str, int, int]:
    """Extract the title, abstract, and comment fields. Also compute the number of words in the
    title and abstract fields.

    inputs
    ------
    logger : The logger object.
    ns     : XML namespaces used by arXiv.
    entry  : The paper's entry in the .xml data.
    """

    # Extract the title
    raw_title = entry.find("atom:title", ns)

    if raw_title is None or raw_title.text is None:

        logger.critical("Could not extract the title.\n")

        raise TypeError("Malformed title.")

    title = raw_title.text.strip()

    logger.debug(f"Title: {title}")

    # Extract the abstract
    raw_abstract = entry.find("atom:summary", ns)

    if raw_abstract is None or raw_abstract.text is None:

        logger.critical("Could not extract the abstract.\n")

        raise TypeError("Malformed abstract.")

    abstract = raw_abstract.text.strip()

    logger.debug("Abstract was found")
    # logger.debug(f"Abstract: {abstract}") # Can print a bit too much information

    n_words_title = len(re.findall(r"\w+", title))
    n_words_abstract = len(re.findall(r"\w+", abstract))

    logger.debug(f"Wordcount: Title = {n_words_title} | Abstract = {n_words_abstract}")

    # Extract the comment. Replace with an empty string if it isn't found.
    raw_comment = entry.find("arxiv:comment", ns)

    if raw_comment is None or raw_comment.text is None:

        logger.debug("No comment found.")

        comment = ""

    else:

        comment = raw_comment.text.strip()

    logger.debug(f"Comment: {comment}")

    return title, abstract, comment, n_words_title, n_words_abstract


def extract_paper_cats(
    logger: logging.Logger, ns: dict[str, str], entry: ET.Element
) -> list[str]:
    """Extract all categories the paper was submitted to.

    inputs
    ------
    logger : The logger object.
    ns     : XML namespaces used by arXiv.
    entry  : The paper's entry in the .xml data.
    """

    # Extract the category
    raw_category = entry.findall("atom:category", ns)

    if len(raw_category) == 0:

        logger.critical("Could not extract the category.\n")

        raise ValueError("Malformed categories (could not find any).")

    category = [cat.attrib["term"] for cat in raw_category]

    logger.debug(f"Category: {category}")

    return category


def extract_paper_authors(
    logger: logging.Logger, ns: dict[str, str], entry: ET.Element
) -> tuple[list[str], int]:
    """Extract all authors from the paper entry.

    inputs
    ------
    logger : The logger object.
    ns     : XML namespaces used by arXiv.
    entry  : The paper's entry in the .xml data.
    """

    # Extract the author list
    author_list: list[str] = []

    authors = entry.findall("atom:author", ns)

    if len(authors) == 0:

        logger.critical("Count not find author list.\n")

        raise ValueError("Malformed authors (could not find any).")

    for author in authors:

        name = author.find("atom:name", ns)

        if name is None or name.text is None:

            logger.critical("Could not extract an author from the list.\n")

            raise TypeError("Malformed author name. Could not extract.")

        normalised_name = normalise_string(name.text)
        author_list.append(normalised_name)

    n_authors = len(author_list)

    logger.debug(f"Found Authors: {author_list}")
    logger.debug(f"Number of authors: {n_authors}")

    return author_list, n_authors


def convert_request_to_xml_root(logger: logging.Logger, arxiv_data: str) -> ET.Element:
    """Convert the raw output from connecting to the servers into a .xml root object.

    inputs
    ------
    logger     : The logger object.
    arxiv_data : The raw data returned from an arXiv server connection.
    """

    try:

        # Parse the results from the connection into an xml
        xml_root = ET.fromstring(arxiv_data)

        return xml_root

    # If there is an error parsing the xml, raise an error
    except ET.ParseError as error:

        # May need to add a way to warn and skip.
        # This error shouldn't occur, but potenially could be due to malformed paper entries
        # It is rare error and difficult to know the cause -- it has only ever occured in
        #     historical searches when testing.

        # # For now, raise an error
        logger.critical("XML parsing error. Please upload log file to github.\n")
        logger.debug(error)
        raise ValueError("Failed to parse the XML data from the servers.") from error
