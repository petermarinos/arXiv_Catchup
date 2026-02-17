# Import functions
from .string_handling import normalise_string

# Import libraries
import xml.etree.ElementTree as ET
# import argparse
# import datetime
import logging
import re

class Paper:

    # One paper
            
    def __init__(self, logger: logging.Logger, ns: dict[str, str], entry: ET.Element) -> None:

        # # Extract values, and perform some error checking
        logger.debug("Attempting to extract a paper from an xml ...")

        # Extract the arXiv ID number
        arXiv_ID = entry.find("atom:id", ns)
        if arXiv_ID is None or arXiv_ID.text is None:
            logger.critical("Could not extract the arXiv ID number.\n")
            raise
        else:
            self.ID      = arXiv_ID.text.split("/")[-1][:10]
            self.version = int( arXiv_ID.text.split("/")[-1][11:] )
            logger.debug("arXiv ID: {:}, version: {:}".format(self.ID, self.version))

        # Extract the title
        title = entry.find("atom:title", ns)
        if title is None or title.text is None:
            logger.critical("Could not extract the title.\n")
            raise
        else:
            self.title = title.text.strip()
            logger.debug("Title: {:}".format(self.title))

        # Extract the updated datetime
        updated = entry.find("atom:updated", ns)
        if updated is None or updated.text is None:
            logger.critical("Could not extract the updated date.\n")
            raise
        else:
            self.updated = updated.text
            logger.debug("Updated on: {:}".format(self.updated))

        # Extract the link to the pdf page
        link = entry.findall("atom:link", ns)
        if link is None:
            logger.critical("Could not extract the main url.\n")
            raise
        else:
            self.link_abs = link[0].attrib["href"]
            self.link_pdf = link[1].attrib["href"]
            logger.debug("Main page: {:}".format(self.link_abs))
            logger.debug(".pdf page: {:}".format(self.link_pdf))

        # Extract the abstract
        abstract = entry.find("atom:summary", ns)
        if abstract is None or abstract.text is None:
            logger.critical("Could not extract the abstract.\n")
            raise
        else:
            self.abstract = abstract.text.strip()
            logger.debug("Abstract was found")
            # logger.debug("Abstract: {:}".format(self.abstract))

        # Extract the category
        category = entry.findall("atom:category", ns)
        if category is None:
            logger.critical("Could not extract the category.\n")
            raise
        else:
            self.category = [cat.attrib["term"] for cat in category]
            logger.debug("Category: {:}".format(self.category))

        # Extract the published datetime
        published = entry.find("atom:published", ns)
        if published is None or published.text is None:
            logger.critical("Could not extract the published date.\n")
            raise
        else:
            self.published = published.text
            logger.debug("Published on: {:}".format(self.published))

        # Extract the comment
        comment = entry.find("arxiv:comment", ns)
        if comment is None or comment.text is None:
            logger.debug("No comment found.")
        else:
            self.comment = comment.text.strip()
            logger.debug("Comment: {:}".format(self.comment))

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
            self.authors = author_list
            logger.debug("Found Authors: {:}".format(author_list))
        
        # Place additional information into this object
        self.revised   = (self.updated > self.published) or (self.version > 1)
        self.n_authors = len(self.authors)
        self.n_words   = {"Title"    : len( re.findall(r'\w+', self.title) ),
                          "Abstract" : len( re.findall(r'\w+', self.abstract) )}
        
        logger.debug("Revised: {:}".format(self.revised))
        logger.debug("Number of authors: {:}".format(self.n_authors))
        logger.debug("Wordcount: Title = {:} | Abstract = {:}".format(self.n_words["Title"], self.n_words["Abstract"]))
        
        logger.debug("Paper successfully extracted from xml.")

    # def scoreAuthors():
    #     print("todo")

    # def scoreIncluded():
    #     print("todo")

    # def scoreExcluded():
    #     print("todo")

class Corpus:
    # The corpus (all papers)

    def __init__(self) -> None:

        self.corpus:dict[str, Paper] = {}

    def addPaperToCorpus(self, logger: logging.Logger, ns: dict[str, str], entry: ET.Element) -> None:

        # Extract the paper from the xml entry
        paper = Paper(logger, ns, entry)

        # Add the paper to the corpus dictionary
        key = paper.ID + "v{:d}".format(paper.version) # include version to ensure each key is unique. We will drop revisions later
        value = paper
        self.corpus[key] = value

    def clearCorpus(self,  logger: logging.Logger):

        logger.debug("Replacing corpus with an empty dictionary.")

        # Replace the corpus with an empty dictionary
        self.corpus:dict[str, Paper] = {}

    def getCorpusLength(self):

        self.length = len(self.corpus.keys())

    def dropRevisions(self,  logger: logging.Logger):

        logger.debug("Removing revised papers.")

        # Obtain the number of papers before dropping
        N = self.length

        temp_dict:dict[str, Paper] = {}

        for key, value in self.corpus.items():
            if not value.revised:
                temp_dict[key] = value

        self.corpus = temp_dict

        # Update the number of papers
        self.getCorpusLength()
        num_dropped = N - self.length
        logger.debug("Dropped {:} revised entries.".format(num_dropped))

# In score_papers_matches:
# for paper in Corpus:
#     paper.scoreAuthors()
#     paper.scoreIncluded()
#     paper.scoreExcluded()