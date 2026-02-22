"""Functions to handle .xml files."""

# Import libraries
import xml.etree.ElementTree as ET
import logging
import re

# Import functions
from .string_handling import normalise_string


def extract_paper_info(
    logger: logging.Logger, ns: dict[str, str], entry: ET.Element
) -> tuple[
    str,
    int,
    str,
    str,
    str,
    str,
    str,
    list[str],
    str,
    str,
    list[str],
    int,
    bool,
    int,
    int,
]:
    """Extract all information from the xml Element returned by the arXiv servers.
    Performs error checks on all components, repalcing with default values where appropriate.
    If the field is *mandatory*, then an error will be raised for a corrupted .xml.

    inouts
    ------
    logger : The logger object.
    ns     : XML namespaces used by arXiv.
    entry  : The XML returned by the servers.
    """

    # Put each of the checks into their own mini-functions?
    # Could then import the link function in corpus.py when checking the links

    # Extract the arXiv ID number
    arxiv_id = entry.find("atom:id", ns)
    if arxiv_id is None or arxiv_id.text is None:
        logger.exception("Could not extract the arXiv ID number.\n")
        raise TypeError("Malformed arXiv ID number.")
    id_num = arxiv_id.text.split("/")[-1][:10]
    version = int(arxiv_id.text.split("/")[-1][11:])
    logger.debug(f"arXiv ID: {id_num}, version: {version}")

    # Extract the title
    raw_title = entry.find("atom:title", ns)
    if raw_title is None or raw_title.text is None:
        logger.exception("Could not extract the title.\n")
        raise TypeError("Malformed title.")
    title = raw_title.text.strip()
    logger.debug(f"Title: {title}")

    # Extract the updated datetime
    raw_updated = entry.find("atom:updated", ns)
    if raw_updated is None or raw_updated.text is None:
        logger.exception("Could not extract the updated date.\n")
        raise TypeError("Malformed updated date")
    updated = raw_updated.text
    logger.debug(f"Updated on: {updated}")

    # Extract the link to the pdf page
    links = entry.findall("atom:link", ns)
    if len(links) < 2:
        logger.exception("Could not find all urls.\n")
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
        logger.exception("Could not find the abstract url.\n")
        raise TypeError("Malformed abs url")
    if link_pdf is None:  #
        logger.exception("Could not find the .pdf url.\n")
        raise TypeError("Malformed pdf url")
    logger.debug(f"Main page: {link_abs}")
    logger.debug(f".pdf page: {link_pdf}")

    # Extract the abstract
    raw_abstract = entry.find("atom:summary", ns)
    if raw_abstract is None or raw_abstract.text is None:
        logger.exception("Could not extract the abstract.\n")
        raise TypeError("Malformed abstract.")
    abstract = raw_abstract.text.strip()
    logger.debug("Abstract was found")
    # logger.debug(f"Abstract: {abstract}")

    # Extract the category
    raw_category = entry.findall("atom:category", ns)
    if len(raw_category) == 0:
        logger.exception("Could not extract the category.\n")
        raise ValueError("Malformed categories (could not find any).")
    category = [cat.attrib["term"] for cat in raw_category]
    logger.debug(f"Category: {category}")

    # Extract the published datetime
    raw_published = entry.find("atom:published", ns)
    if raw_published is None or raw_published.text is None:
        logger.exception("Could not extract the published date.\n")
        raise TypeError("Malformed published date.")
    published = raw_published.text
    logger.debug(f"Published on: {published}")

    # Extract the comment. Replace with an empty string if it isn't found.
    raw_comment = entry.find("arxiv:comment", ns)
    if raw_comment is None or raw_comment.text is None:
        logger.debug("No comment found.")
        comment = ""
    else:
        comment = raw_comment.text.strip()
    logger.debug(f"Comment: {comment}")

    # Extract the author list
    author_list: list[str] = []
    authors = entry.findall("atom:author", ns)
    if len(authors) == 0:
        logger.exception("Count not find author list.\n")
        raise ValueError("Malformed authors (could not find any).")
    for author in authors:
        name = author.find("atom:name", ns)
        if name is None or name.text is None:
            logger.exception("Could not extract an author from the list.\n")
            raise TypeError("Malformed author name. Could not extract.")
        normalised_name = normalise_string(name.text)
        author_list.append(normalised_name)
    logger.debug(f"Found Authors: {author_list}")

    # Derive some additional information
    revised = (updated > published) or (version > 1)
    logger.debug(f"Revised: {revised}")

    n_authors = len(author_list)
    logger.debug(f"Number of authors: {n_authors}")

    n_words_title = len(re.findall(r"\w+", title))
    n_words_abstract = len(re.findall(r"\w+", abstract))
    logger.debug(f"Wordcount: Title = {n_words_title} | Abstract = {n_words_abstract}")

    logger.debug("Paper successfully extracted from xml.")

    return (
        id_num,
        version,
        title,
        updated,
        link_abs,
        link_pdf,
        abstract,
        category,
        published,
        comment,
        author_list,
        n_authors,
        revised,
        n_words_title,
        n_words_abstract,
    )
