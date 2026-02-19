# Import functions
from .string_handling import normalise_string
from .xml_handling    import extract_paper_info
from .filtering       import authors_match

# Import libraries
from dataclasses import dataclass
from typing      import Literal

import xml.etree.ElementTree as ET
import logging
import re

# Define some literals. Bounds the expected values.
WordKind = Literal["Included Words", "Excluded Words"]
Section  = Literal["Title", "Abstract", "Total"]

@dataclass
class paperInfo:
    id_num           : str
    version          : int
    title            : str
    date_updated     : str
    link_abs         : str
    link_pdf         : str
    abstract         : str
    category         : list[str]
    date_published   : str
    comment          : str
    authors          : list[str]
    n_authors        : int
    revised          : bool
    n_words_title    : int
    n_words_abstract : int

@dataclass
class paperScores:

    # Define the objects within the dataclass
    found_authors    : list[str]
    n_author_matches : int
    matches          : dict[WordKind, dict[Section, int]]
    scores           : dict[WordKind, dict[Section, float]]
    final_score      : float

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

        # Compute all values
        id_num, version, title, updated, link_abs, link_pdf, abstract, category, published, comment, authors, n_authors, revised, n_words_title, n_words_abstract = extract_paper_info(self.logger, ns, entry)

        # Place values into the dataclass
        self.paperInfo = paperInfo(
                                   id_num = id_num,
                                   version = version,
                                   title = title,
                                   date_updated = updated,
                                   link_abs = link_abs,
                                   link_pdf = link_pdf,
                                   abstract = abstract,
                                   category = category,
                                   date_published = published,
                                   comment = comment,
                                   authors = authors,
                                   n_authors = n_authors,
                                   revised = revised,
                                   n_words_title = n_words_title,
                                   n_words_abstract = n_words_abstract,
                                  )

        # Initialise the scores. Will set them all to zero
        self.paperScores = paperScores([], 0, {}, {}, 0.)
    

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
            for paper_author in self.paperInfo.authors:

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
                        self.paperScores.found_authors.append(paper_author)

            # If no matches were found for this Paper:
            if self.n_author_matches == 0:
                self.logger.debug(" ... none found")

    # # Find matches between the text in the title and abstract and the words of interest
    def match_words(self, key_words: dict[str, str], match_type: WordKind) -> None:
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

                pattern = rf"(?<!\w){re.escape(word)}(?!\w)"

                # Search the author field in the entry
                title_match = re.search(pattern, self.paperInfo.title, re.IGNORECASE)

                # If a match is found in the title:
                if title_match:

                    # Count the number of matches
                    num_title_matches = len( re.findall(pattern, self.paperInfo.title, re.IGNORECASE) )

                    self.logger.debug("Found '{:}' {:} time(s) in the title.".format(word, num_title_matches))

                    # Add to score
                    self.paperScores.matches[match_type]["Title"] += num_title_matches

                # If something exists in the abstract field, search it for matches
                if self.paperInfo.abstract is not None:
                    
                    abstract_match = re.search(pattern, self.paperInfo.abstract, re.IGNORECASE)

                    # If a match is found in the abstract:
                    if abstract_match:

                        # Count the number of matches
                        num_abstract_matches = len( re.findall(pattern, self.paperInfo.abstract, re.IGNORECASE) )

                        self.logger.debug("Found '{:}' {:} time(s) in the abstract.".format(word, num_abstract_matches))

                        self.paperScores.matches[match_type]["Abstract"] += num_abstract_matches
                    
            # Compute the total number of matches
            self.paperScores.matches[match_type]["Total"] = ( self.paperScores.matches[match_type]["Title"] + self.paperScores.matches[match_type]["Abstract"] )

            self.logger.debug("Matches | Title {:} | Abstract {:} |".format(self.paperScores.matches[match_type]["Title"], self.paperScores.matches[match_type]["Abstract"]))

            # If no matches were found:
            if self.paperScores.matches[match_type]["Total"] == 0:
                self.logger.debug(" ... none found")

    # # Score the paper based on the author list
    def score_authors(self) -> None:
        """Score the Paper based on the author list.
        """

        self.logger.debug("** Author Scores **")

        # # Compute penalties
        # Author lists are penalised for being above a count of 25
        # The penalty is minor, but slightly de-prioritises collaboration papers
        authors_penalty  =  25 / self.paperInfo.n_authors
        self.logger.debug("| Author Penalty = {:.2f} |".format(authors_penalty))

        # Compute the Author score:
        authors_found     = len( self.paperScores.found_authors )
        authors_score     = min(authors_found * authors_penalty, 1.)
        self.author_score = max(authors_score, 0)

        self.logger.debug("| Total authors = {:d} | Found = {:d} |".format(len(self.paperInfo.authors), authors_found))
        self.logger.debug("| Author score = {:.2f} |".format(self.author_score))

    # # Score the paper based on the words used in a given category
    def score_words(self, match_type: WordKind) -> None:
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
        title_penalty    =  18 / self.paperInfo.n_words_title
        abstract_penalty = 250 / self.paperInfo.n_words_abstract
        self.logger.debug("| Title Penalty = {:.2f} | Abstract Penalty = {:.2f} |".format(title_penalty, abstract_penalty))

        # Compute the Included Word scores:
        inc_title_count    = self.paperScores.matches[match_type]["Title"]
        inc_abstract_count = self.paperScores.matches[match_type]["Abstract"]
        
        # # Compute word scores
        # They are bound to the interval [0, 1] via min/max functions
        # An interesting title has one or two matches
        # An interesting abstract has ~5 matches
        inc_title_score    = min( title_penalty * inc_title_count / 1.0, 1.0 )
        inc_abstract_score = min( abstract_penalty * inc_abstract_count / 5.0, 1.0 )
        inc_total_score    = ( inc_title_score + inc_abstract_score ) / 2.0

        # Place scores into the Papers object
        self.paperScores.scores[match_type]["Title"]    = inc_title_score
        self.paperScores.scores[match_type]["Abstract"] = inc_abstract_score
        self.paperScores.scores[match_type]["Total"]    = inc_total_score
        
        self.logger.debug("| Title Matches = {:d} | Title Score = {:.2f} |".format(inc_title_count, inc_title_score))
        self.logger.debug("| Abstract Matches = {:d} | Abstract Score = {:.2f} |".format(inc_abstract_count, inc_abstract_score))
        self.logger.debug("| {:} Score = {:.2f} |".format(match_type, inc_total_score))

    # # Compute a final score, considering both word categories
    def final_word_score(self) -> None:
        """Compute a final word score for a Paper based on the combination of 'Included Words' and 'Excluded Words'.
        """

        # Compute the Final score:
        self.final_score = max(self.paperScores.scores["Included Words"]["Total"] - self.paperScores.scores["Excluded Words"]["Total"], +0)

        self.logger.debug("Final Score = {:}".format(self.final_score))
