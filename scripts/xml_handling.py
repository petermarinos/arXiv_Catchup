# Import functions
from .string_handling import normalise_string

# Import libraries
import xml.etree.ElementTree as ET
import logging
import re

def extract_paper_info(logger: logging.Logger, ns: dict[str, str], entry: ET.Element) -> tuple[str, int, str, str, str, str, str, list[str], str, str, list[str], int, bool, int, int]:

    # Extract the arXiv ID number
    arXiv_ID = entry.find("atom:id", ns)
    if arXiv_ID is None or arXiv_ID.text is None:
        logger.critical("Could not extract the arXiv ID number.\n")
        raise
    else:
        id_num  = arXiv_ID.text.split("/")[-1][:10]
        version = int( arXiv_ID.text.split("/")[-1][11:] )
        logger.debug("arXiv ID: {:}, version: {:}".format(id_num, version))

    # Extract the title
    title = entry.find("atom:title", ns)
    if title is None or title.text is None:
        logger.critical("Could not extract the title.\n")
        raise
    else:
        title = title.text.strip()
        logger.debug("Title: {:}".format(title))

    # Extract the updated datetime
    updated = entry.find("atom:updated", ns)
    if updated is None or updated.text is None:
        logger.critical("Could not extract the updated date.\n")
        raise
    else:
        updated = updated.text
        logger.debug("Updated on: {:}".format(updated))

    # Extract the link to the pdf page
    link = entry.findall("atom:link", ns)
    if link is None:
        logger.critical("Could not extract the main url.\n")
        raise
    else:
        link_abs = link[0].attrib["href"]
        link_pdf = link[1].attrib["href"]
        logger.debug("Main page: {:}".format(link_abs))
        logger.debug(".pdf page: {:}".format(link_pdf))

    # Extract the abstract
    abstract = entry.find("atom:summary", ns)
    if abstract is None or abstract.text is None:
        logger.critical("Could not extract the abstract.\n")
        raise
    else:
        abstract = abstract.text.strip()
        logger.debug("Abstract was found")
        # self.logger.debug("Abstract: {:}".format(self.abstract))

    # Extract the category
    category = entry.findall("atom:category", ns)
    if category is None:
        logger.critical("Could not extract the category.\n")
        raise
    else:
        category = [cat.attrib["term"] for cat in category]
        logger.debug("Category: {:}".format(category))

    # Extract the published datetime
    published = entry.find("atom:published", ns)
    if published is None or published.text is None:
        logger.critical("Could not extract the published date.\n")
        raise
    else:
        published = published.text
        logger.debug("Published on: {:}".format(published))

    # Extract the comment
    comment = entry.find("arxiv:comment", ns)
    if comment is None or comment.text is None:
        logger.debug("No comment found.")
        comment = ""
    else:
        comment = comment.text.strip()
        logger.debug("Comment: {:}".format(comment))

    # Extract the author list
    author_list = []
    authors = entry.findall("atom:author", ns)
    if authors is None:
        logger.critical("Could not extract the author list.\n")
        raise
    else:
        for author in authors:
            name = author.find("atom:name", ns)
            if name is None or name.text is None:
                logger.critical("Could not extract the author list.\n")
                raise
            else:
                normalised_name = normalise_string(name.text)
                author_list.append(normalised_name)
        authors = author_list
        logger.debug("Found Authors: {:}".format(author_list))
        n_authors = len(authors)
    
    # Place additional information into this object
    revised   = (updated > published) or (version > 1)
    n_authors = len(authors)
    n_words_title   = len( re.findall(r'\w+', title) )
    n_words_abstract = len( re.findall(r'\w+', abstract) )
    
    logger.debug("Revised: {:}".format(revised))
    logger.debug("Number of authors: {:}".format(n_authors))
    logger.debug("Wordcount: Title = {:} | Abstract = {:}".format(n_words_title, n_words_abstract))
    
    logger.debug("Paper successfully extracted from xml.")

    return id_num, version, title, updated, link_abs, link_pdf, abstract, category, published, comment, authors, n_authors, revised, n_words_title, n_words_abstract