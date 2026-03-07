"""The Paper class."""

# Import dependency type checking libraries
from __future__ import annotations
from typing import TYPE_CHECKING

# Import libraries
from dataclasses import dataclass
from enum import Enum
import xml.etree.ElementTree as ET
import logging
import re

# Import functions
from .xml_handling import (
    extract_paper_id_version,
    extract_paper_links,
    extract_paper_textfields,
    extract_paper_cats,
    extract_paper_authors,
)
from .string_handling import authors_match, words_match_pattern

# Import classes for type checking
if TYPE_CHECKING:
    from .storage_manager import SearchTerms


# Define some small classes. Bounds the expected values and prevents errors within strings.
class WordKind(Enum):
    """Define the kinds of words we expect to use in the matching/scoring algorithms"""

    INCLUDED = "included_words"
    EXCLUDED = "excluded_words"


class SectionKind(Enum):
    """Define the kinds of sections that we expect to find matches/scores for."""

    TITLE = "title"
    ABSTRACT = "abstract"
    TOTAL = "total"


@dataclass
class CountScore:
    """Define the class that will hold the number of matches and scores. Default all to zero"""

    matches: int = 0
    scores: float = 0.0


@dataclass
class PaperInfo:
    """Holds all information for a paper.
    Stores all data from the arXiv query, plus a few derived values.
    """

    # 11 attributes from the .xml
    # 4 attributes are derived
    # => 15 attributes
    # Want to store *all* data. Even if not used now, it will simplify including later.
    # Disable pylint warning for >7 attributes
    # pylint: disable=R0902

    # Values in order they are found in the .xml data
    id_num: str
    version: int
    title: str
    date_updated: str
    link_abs: str
    link_pdf: str
    abstract: str | None
    category: list[str]
    date_published: str
    comment: str | None
    authors: list[str]

    # Derived values, in ~ the same order
    revised: bool
    n_words_title: int
    n_words_abstract: int
    n_authors: int


@dataclass
class PaperScores:
    """Holds all score-related information for a paper."""

    found_authors: list[str]
    n_author_matches: int
    author_score: float
    matches_scores: dict[WordKind, dict[SectionKind, CountScore]]
    final_score: float


class Paper:
    """Describes each paper -- the information and scores."""

    # Define constants used for scoring calculations
    # Two components to the logic:
    # 1) how many matches are required to be considered interesting, and
    # 2) the interesting-ness density
    # Require at least x matches per field to be considered interesting.
    AUTHOR_REQ_MATCHES = 1
    TITLE_REQ_MATCHES = 1
    ABSTRACT_REQ_MATCHES = 5
    # Fields with lengths below/above x are boosted/penalised
    AUTHOR_REQ_DENSITY = 25  # Author counts above => penalised
    TITLE_REQ_DENSITY = 18  # Title word counts above => penalised
    ABSTRACT_REQ_DENSITY = 250  # Abstract word counts above => penalised

    def __init__(self, ns: dict[str, str], entry: ET.Element) -> None:
        """Create the Paper object that represents a single paper.

        inputs
        -----
        ns     : XML namespaces.
        entry  : XML data for a single paper.
        """

        # 11 variables from the .xml
        # 4 variables derived from the .xml
        # 6 variables to store future scores
        # => 21 variables
        # Want to store *all* paper information. Disable pylint warning for >15 variables
        # pylint: disable=R0914

        # Obtain the logger
        self.logger = logging.getLogger(__name__)

        # # Extract values, and perform some error checking
        # self.logger.debug("Attempting to extract a paper from an xml ...")

        # Extract values from the paper
        id_num, version, updated, published, revised = extract_paper_id_version(
            self.logger, ns, entry
        )
        link_abs, link_pdf = extract_paper_links(self.logger, ns, entry)
        title, abstract, comment, n_words_title, n_words_abstract = (
            extract_paper_textfields(self.logger, ns, entry)
        )
        category = extract_paper_cats(self.logger, ns, entry)
        authors, n_authors = extract_paper_authors(self.logger, ns, entry)

        # Place values into the dataclass
        self.paper_info = PaperInfo(
            id_num=id_num,
            version=version,
            title=title,
            date_updated=updated,
            link_abs=link_abs,
            link_pdf=link_pdf,
            abstract=abstract,
            category=category,
            date_published=published,
            comment=comment,
            authors=authors,
            revised=revised,
            n_words_title=n_words_title,
            n_words_abstract=n_words_abstract,
            n_authors=n_authors,
        )

        # Initialise the scores. Will set them all to zero by default
        matches_scores: dict[WordKind, dict[SectionKind, CountScore]] = {
            wk: {sk: CountScore() for sk in SectionKind} for wk in WordKind
        }

        self.paper_scores = PaperScores(
            found_authors=[],
            n_author_matches=0,
            author_score=0.0,
            matches_scores=matches_scores,
            final_score=0.0,
        )

    def match_authors(self, key_authors: list[str] | None) -> None:
        """Find matches between the authors of the Paper and authors in the search terms.

        inputs
        ------
        key_authors : List containing all authors to search for.
        """

        # If there are no authors to search for, skip the search
        if key_authors is None:
            self.logger.debug("No authors to search for...")
            return

        # If there is at least one author of interest
        # self.logger.debug("Searching for Authors")

        # Loop over the authors of the paper
        for paper_author in self.paper_info.authors:

            # Loop over the authors in the search terms
            for key_author in key_authors:

                # Search the author field of the paper for any key authors
                key_author_match = authors_match(key_author, paper_author)

                # If an author is found:
                if key_author_match:

                    self.logger.debug(
                        "    Found author: %s | Matched with: %s",
                        key_author,
                        paper_author,
                    )

                    # Increase the number of author matches by 1
                    self.paper_scores.n_author_matches += 1

                    # Add the author to the list of found authors
                    # Use the author name from the paper
                    # This way the user is shown exactly what was matched
                    self.paper_scores.found_authors.append(paper_author)

        # # If no matches were found for this Paper:
        # if self.paper_scores.n_author_matches == 0:
        #     self.logger.debug(" ... none found")

    def match_words(self, key_words: SearchTerms, match_type: WordKind) -> None:
        """Find matches between the Title/Abstract of the Paper and key words in the search terms.

        inputs
        ------
        key_words  : List containing all key words to search for
        match_type : The type of match we are searching for ('Included Words' or 'Excluded Words').
        """

        # Extract the words to search for from the key_words dictionary
        # Do not need to use .get() as match_type is limited to the type WordKind
        if match_type == WordKind.INCLUDED:
            words = key_words.included_words
        elif match_type == WordKind.EXCLUDED:
            words = key_words.excluded_words
        else:
            raise ValueError("Could not resolve match type.")

        # If there are no key_words to search for, skip the search
        if len(words) == 0:
            self.logger.debug("No %s to search for...", match_type)
            return

        # self.logger.debug("Searching for %s", match_type)

        # Search all titles and abstracts for words in the supplied key
        for word in words:

            # # Define the pattern to search for
            pattern = words_match_pattern(word)

            # # Define the text to search through
            title = self.paper_info.title  # DO NOT ESCAPE

            # Search the author field in the entry
            title_match = re.search(pattern, title, re.IGNORECASE)

            # If a match is found in the title:
            if title_match:

                # Count the number of matches
                num_title_matches = len(re.findall(pattern, title, re.IGNORECASE))

                self.logger.debug(
                    "    Found '%s' %s time(s) in the title.", word, num_title_matches
                )

                # Add to score
                self.paper_scores.matches_scores[match_type][
                    SectionKind.TITLE
                ].matches += num_title_matches

            # If something exists in the abstract field, search it for matches
            if self.paper_info.abstract is not None:

                # Define the text to search through
                abstract = self.paper_info.abstract  # DO NOT ESCAPE

                abstract_match = re.search(pattern, abstract, re.IGNORECASE)

                # If a match is found in the abstract:
                if abstract_match:

                    # Count the number of matches
                    num_abstract_matches = len(
                        re.findall(pattern, abstract, re.IGNORECASE)
                    )

                    self.logger.debug(
                        "    Found '%s' %s time(s) in the abstract.",
                        word,
                        num_abstract_matches,
                    )

                    self.paper_scores.matches_scores[match_type][
                        SectionKind.ABSTRACT
                    ].matches += num_abstract_matches

        # Compute the total number of matches
        self.paper_scores.matches_scores[match_type][SectionKind.TOTAL].matches = (
            self.paper_scores.matches_scores[match_type][SectionKind.TITLE].matches
            + self.paper_scores.matches_scores[match_type][SectionKind.ABSTRACT].matches
        )

        # # Summary of matches
        # self.logger.debug(
        #     "Matches | "
        #     f"Title {self.paper_scores.matches[match_type]['Title']} | "
        #     f"Abstract {self.paper_scores.matches[match_type]['Abstract']} |"
        # )

        # # If no matches were found:
        # if self.paper_scores.matches[match_type]["Total"] == 0:
        #     self.logger.debug(" ... none found")

    def score_authors(self) -> None:
        """Score the Paper based on the author list."""

        # self.logger.debug("** Author Scores **")

        # # Compute penalties
        # Author lists are penalised for being above a count of self.AUTHOR_REQ_DENSITY
        # The penalty is minor, but slightly de-prioritises collaboration papers
        authors_penalty = self.AUTHOR_REQ_DENSITY / self.paper_info.n_authors

        # Compute the Author score:
        authors_found = len(self.paper_scores.found_authors)
        authors_score = min(
            authors_penalty * authors_found / self.AUTHOR_REQ_MATCHES, 1.0
        )
        self.paper_scores.author_score = authors_score

        # # Logging messages. Creates a large amount of output and are no longer necessary
        # # Keeping here in case the algorithms are altered
        # self.logger.debug(f"| Author Penalty = {authors_penalty:.2f} |")
        # self.logger.debug(
        #     f"| Total authors = {len(self.paper_info.authors):d} | Found = {authors_found:d} |"
        # )
        # self.logger.debug(f"| Author score = {self.paper_scores.author_score:.2f} |")

    def score_words(self, match_type: WordKind) -> None:
        """Score the Paper based on the found words in the Title/Abstract.

        inputs
        ------
        match_type : The type of match we are searching for ('Included Words' or 'Excluded Words').
        """

        # self.logger.debug("** %s Scores **", match_type)

        # Compute penalties
        title_penalty = self.TITLE_REQ_DENSITY / self.paper_info.n_words_title
        abstract_penalty = self.ABSTRACT_REQ_DENSITY / self.paper_info.n_words_abstract

        # Extract the number of matches
        inc_title_count = self.paper_scores.matches_scores[match_type][
            SectionKind.TITLE
        ].matches
        inc_abstract_count = self.paper_scores.matches_scores[match_type][
            SectionKind.ABSTRACT
        ].matches

        # # Compute word scores
        # They are bound to the interval [0, 1] via min functions
        inc_title_score = min(
            title_penalty * inc_title_count / self.TITLE_REQ_MATCHES, 1.0
        )
        inc_abstract_score = min(
            abstract_penalty * inc_abstract_count / self.ABSTRACT_REQ_MATCHES, 1.0
        )
        inc_total_score = (inc_title_score + inc_abstract_score) / 2

        # Place scores into the Papers object
        self.paper_scores.matches_scores[match_type][
            SectionKind.TITLE
        ].scores = inc_title_score
        self.paper_scores.matches_scores[match_type][
            SectionKind.ABSTRACT
        ].scores = inc_abstract_score
        self.paper_scores.matches_scores[match_type][
            SectionKind.TOTAL
        ].scores = inc_total_score

        # # Logging messages. Creates a large amount of output and are no longer necessary
        # # Keeping here in case the algorithms are altered
        # self.logger.debug(
        #     f"| Title Penalty = {title_penalty:.2f} "
        #     f"| Abstract Penalty = {abstract_penalty:.2f} |"
        # )
        # self.logger.debug(
        #     f"| Title Matches = {inc_title_count:d} "
        #     f"| Title Score = {inc_title_score:.2f} |"
        # )
        # self.logger.debug(
        #     f"| Abstract Matches = {inc_abstract_count:d} "
        #     f"| Abstract Score = {inc_abstract_score:.2f} |"
        # )

        # self.logger.debug(f"| {match_type:} Score = {inc_total_score:.2f} |")

    def final_word_score(self) -> None:
        """Compute a final word score for a Paper.
        Score is based on the combination of 'Included Words' and 'Excluded Words'."""

        # Compute the Final score:
        self.paper_scores.final_score = max(
            self.paper_scores.matches_scores[WordKind.INCLUDED][
                SectionKind.TOTAL
            ].scores
            - self.paper_scores.matches_scores[WordKind.EXCLUDED][
                SectionKind.TOTAL
            ].scores,
            +0,
        )

        self.logger.debug(
            "arXiv:%s final Score = %.2f",
            self.paper_info.id_num,
            self.paper_scores.final_score,
        )
