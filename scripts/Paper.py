# Import functions
from .string_handling import normalise_string
from .filtering       import authors_match

# Import libraries
import xml.etree.ElementTree as ET
import logging
import re

class Paper:
            
    # # Initialise the class
    def __init__(self, logger: logging.Logger, ns: dict[str, str], entry: ET.Element) -> None:
        """Create the Paper object that represents a single paper.

        inputs
        -----
        logger : The logger object.
        ns     : XML namespaces.
        entry  : XML data for a single paper.
        """

        self.logger = logger

        # # Extract values, and perform some error checking
        self.logger.debug("Attempting to extract a paper from an xml ...")

        # Extract the arXiv ID number
        arXiv_ID = entry.find("atom:id", ns)
        if arXiv_ID is None or arXiv_ID.text is None:
            self.logger.critical("Could not extract the arXiv ID number.\n")
            raise
        else:
            self.ID      = arXiv_ID.text.split("/")[-1][:10]
            self.version = int( arXiv_ID.text.split("/")[-1][11:] )
            self.logger.debug("arXiv ID: {:}, version: {:}".format(self.ID, self.version))

        # Extract the title
        title = entry.find("atom:title", ns)
        if title is None or title.text is None:
            self.logger.critical("Could not extract the title.\n")
            raise
        else:
            self.title = title.text.strip()
            self.logger.debug("Title: {:}".format(self.title))

        # Extract the updated datetime
        updated = entry.find("atom:updated", ns)
        if updated is None or updated.text is None:
            self.logger.critical("Could not extract the updated date.\n")
            raise
        else:
            self.updated = updated.text
            self.logger.debug("Updated on: {:}".format(self.updated))

        # Extract the link to the pdf page
        link = entry.findall("atom:link", ns)
        if link is None:
            self.logger.critical("Could not extract the main url.\n")
            raise
        else:
            self.link_abs = link[0].attrib["href"]
            self.link_pdf = link[1].attrib["href"]
            self.logger.debug("Main page: {:}".format(self.link_abs))
            self.logger.debug(".pdf page: {:}".format(self.link_pdf))

        # Extract the abstract
        abstract = entry.find("atom:summary", ns)
        if abstract is None or abstract.text is None:
            self.logger.critical("Could not extract the abstract.\n")
            raise
        else:
            self.abstract = abstract.text.strip()
            self.logger.debug("Abstract was found")
            # self.logger.debug("Abstract: {:}".format(self.abstract))

        # Extract the category
        category = entry.findall("atom:category", ns)
        if category is None:
            self.logger.critical("Could not extract the category.\n")
            raise
        else:
            self.category = [cat.attrib["term"] for cat in category]
            self.logger.debug("Category: {:}".format(self.category))

        # Extract the published datetime
        published = entry.find("atom:published", ns)
        if published is None or published.text is None:
            self.logger.critical("Could not extract the published date.\n")
            raise
        else:
            self.published = published.text
            self.logger.debug("Published on: {:}".format(self.published))

        # Extract the comment
        comment = entry.find("arxiv:comment", ns)
        if comment is None or comment.text is None:
            self.logger.debug("No comment found.")
        else:
            self.comment = comment.text.strip()
            self.logger.debug("Comment: {:}".format(self.comment))

        # Extract the author list
        author_list = []
        authors = entry.findall("atom:author", ns)
        if authors is None:
            self.logger.critical("Could not extract the author list.\n")
            raise
        else:
            for author in authors:
                name = author.find("atom:name", ns)
                if name is None or name.text is None:
                    self.logger.critical("Could not extract the author list.\n")
                    raise
                else:
                    normalised_name = normalise_string(name.text)
                    author_list.append(normalised_name)
            self.authors = author_list
            self.logger.debug("Found Authors: {:}".format(author_list))
        
        # Place additional information into this object
        self.revised   = (self.updated > self.published) or (self.version > 1)
        self.n_authors = len(self.authors)
        self.n_words   = {"Title"    : len( re.findall(r'\w+', self.title) ),
                          "Abstract" : len( re.findall(r'\w+', self.abstract) )}
        
        self.logger.debug("Revised: {:}".format(self.revised))
        self.logger.debug("Number of authors: {:}".format(self.n_authors))
        self.logger.debug("Wordcount: Title = {:} | Abstract = {:}".format(self.n_words["Title"], self.n_words["Abstract"]))

        # Initialise a few other values
        # May be best to move this to a new class/dataclass? 
        self.n_author_matches: int                    = 0
        self.found_authors:    list[str]              = []
        score_dict: dict[str, int | float]            = {"Title Score"      : 0.,
                                                         "Title Matches"    : 0,
                                                         "Abstract Score"   : 0.,
                                                         "Abstract Matches" : 0,
                                                         "Total Score"      : 0.,
                                                         "Total Matches"    : 0}
        self.words: dict[str, dict[str, int | float]] = {"Included Words" : score_dict.copy(),
                                                         "Excluded Words" : score_dict.copy()}
        
        self.logger.debug("Paper successfully extracted from xml.")

    # # Find matches between the paper authors and the authors of interest
    def match_authors(self, key_authors: list[str]) -> None:
        """Find matches between the authors of the Paper and authors in the search terms.

        inputs
        ------
        key_authors : List containing all authors to search for.
        """

        # If there are no authors to search for, skip the search
        if key_authors is None:
            self.logger.debug("No authors to search for...")
            
        # If there is at least one author of interest
        elif key_authors is not None:

            self.logger.debug("Searching for Authors")

            # Loop over the authors of the paper
            for paper_author in self.authors:

                # Loop over the authors in the search terms
                for key_author in key_authors:

                    # Search the author field of the paper for any key authors
                    key_author_match = authors_match(key_author, paper_author)

                    # If an author is found:
                    if key_author_match:

                        self.logger.debug("Found author: {:} | Matched with: {:}".format(key_author, paper_author))
                        
                        # Increase the number of author matches by 1
                        self.n_author_matches += 1
                        
                        # Add the author to the list of found authors
                        # Use the author name from the paper so that the user is shown exactly what was matched
                        self.found_authors.append(paper_author)

            # If no matches were found for this Paper:
            if self.n_author_matches == 0:
                self.logger.debug(" ... none found")

    # # Find matches between the text in the title and abstract and the words of interest
    def match_words(self, key_words: dict[str, str], match_type: str) -> None:
        """Find matches between the Title/Abstract of the Paper and key words in the search terms.

        inputs
        ------
        key_words  : List containing all key words to search for
        match_type : The type of match we are searching for, either 'Included Words' or 'Excluded Words'.
        """

        # If there are no key_words to search for, skip the search
        if key_words[match_type] is None:
            self.logger.debug("No {:} to search for...".format(match_type))

        elif key_words[match_type] is not None:

            self.logger.debug("Searching for {:}".format(match_type))

            # Search all titles and abstracts for words in the supplied key
            for word in key_words[match_type]:

                # Search the author field in the entry
                title_match = re.search(r"\b"+word+r"\b", self.title, re.IGNORECASE)

                # If a match is found in the title:
                if title_match:

                    # Count the number of matches
                    num_title_matches = len( re.findall(r"\b"+word+r"\b", self.title, re.IGNORECASE) )

                    self.logger.debug("Found '{:}' {:} time(s) in the title.".format(word, num_title_matches))

                    # Add to score
                    self.words[match_type]["Title Matches"] += num_title_matches

                # If something exists in the abstract field, search it for matches
                if self.abstract is not None:
                    
                    abstract_match = re.search(r"\b"+word+r"\b", self.abstract, re.IGNORECASE)

                    # If a match is found in the abstract:
                    if abstract_match:

                        # Count the number of matches
                        num_abstract_matches = len( re.findall(r"\b"+word+r"\b", self.abstract, re.IGNORECASE) )

                        self.logger.debug("Found '{:}' {:} time(s) in the abstract.".format(word, num_abstract_matches))

                        self.words[match_type]["Abstract Matches"] += num_abstract_matches
                    
            # Compute the total number of matches
            self.words[match_type]["Total Matches"] = ( self.words[match_type]["Title Matches"] + self.words[match_type]["Abstract Matches"] )

            self.logger.debug("Matches | Title {:} | Abstract {:} |".format(self.words[match_type]["Title Matches"], self.words[match_type]["Abstract Matches"]))

            # If no matches were found:
            if self.words[match_type]["Total Matches"] == 0:
                self.logger.debug(" ... none found")

    # # Score the paper based on the author list
    def score_authors(self) -> None:
        """Score the Paper based on the author list.
        """

        self.logger.debug("** Author Scores **")

        # # Compute penalties
        # Author lists are penalised for being above a count of 25
        # The penalty is minor, but slightly de-prioritises collaboration papers
        authors_penalty  =  25 / self.n_authors
        self.logger.debug("| Author Penalty = {:.2f} |".format(authors_penalty))

        # Compute the Author score:
        authors_found     = len( self.found_authors )
        authors_score     = min(authors_found * authors_penalty, 1.)
        self.author_score = max(authors_score, 0)

        self.logger.debug("| Total authors = {:} | Found = {:} |".format(len(self.authors), authors_found))
        self.logger.debug("| Author score = {:.2f} |".format(self.author_score))

    # # Score the paper based on the words used in a given category
    def score_words(self, match_type: str) -> None:
        """Score the Paper based on the found words in the Title/Abstract.

        inputs
        ------
        match_type : The type of match we are searching for, either 'Included Words' or 'Excluded Words'.
        """

        self.logger.debug("** {:} Scores **".format(match_type))

        # # Compute penalties
        # Titles are boosted/penalised for word counts below/above 18 (current median in astro)
        # Abstracts are boosted/penalised for word counts below/above 250 (typical limit)
        # Ensures that papers with very long abstracts are still scored similarly to those with short abstracts
        title_penalty    =  18 / self.n_words["Title"]
        abstract_penalty = 250 / self.n_words["Abstract"]
        self.logger.debug("| Title Penalty = {:.2f} | Abstract Penalty = {:.2f} |".format(title_penalty, abstract_penalty))

        # Compute the Included Word scores:
        inc_title_count    = self.words[match_type]["Title Matches"]
        inc_abstract_count = self.words[match_type]["Abstract Matches"]
        
        # # Compute word scores
        # They are bound to the interval [0, 1] via min/max functions
        # An interesting title has one or two matches
        # An interesting abstract has ~5 matches
        inc_title_score    = min( title_penalty * inc_title_count / 1.0, 1.0 )
        inc_abstract_score = min( abstract_penalty * inc_abstract_count / 5.0, 1.0 )
        inc_total_score    = ( inc_title_score + inc_abstract_score ) / 2.0

        # Place scores into the Papers object
        self.words[match_type]["Title Score"]    = inc_title_score
        self.words[match_type]["Abstract Score"] = inc_abstract_score
        self.words[match_type]["Total Score"]    = inc_total_score
        
        self.logger.debug("| Title Matches = {:} | Title Score = {:.2f} |".format(inc_title_count, inc_title_score))
        self.logger.debug("| Abstract Matches = {:.2f} | Abstract Score = {:.2f} |".format(inc_abstract_count, inc_abstract_score))
        self.logger.debug("| {:} Score = {:.2f} |".format(match_type, inc_total_score))

    # # Compute a final score, considering both word categories
    def final_word_score(self) -> None:
        """Compute a final word score for a Paper based on the combination of 'Included Words' and 'Excluded Words'.
        """

        # Compute the Final score:
        self.final_score = max(self.words["Included Words"]["Total Score"] - self.words["Excluded Words"]["Total Score"], +0)

        self.logger.debug("Final Score = {:}".format(self.final_score))
