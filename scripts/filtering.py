# Import functions
from .string_handling import split_initials, find_token
from .utils           import progress_bar

# Import libraries
import pandas  as pd
import numpy   as np
import logging
import re

def authors_match(a: str, b: str) -> bool:
    """Check if two author strings match.

    inputs
    ------
    a, b : The two authors that are being tested against one another.

    outputs
    -------
    : True if a matches b, False otherwise.
    """

    # Strip the two names
    A = a.strip().split()
    B = b.strip().split()

    # Ensure both stripped strings have an entry
    if not A or not B:
        return False
    
    # If the surnames are not exact matches
    if A[-1] != B[-1]:
        return False

    # Extract given names
    givens_a, givens_b = A[:-1], B[:-1]

    # Split initials (if they are initials without whitespace)
    givens_a = split_initials(givens_a)
    givens_b = split_initials(givens_b)
    
    # Compute number of given names
    n = min(len(givens_a), len(givens_b))

    # Loop through the given names
    for i in range(n):

        # Extract the tokens (i.e. full name or initial) and their values
        token_a, value_a = find_token(givens_a[i])
        token_b, value_b = find_token(givens_b[i])

        # # Check if the tokens and values don't match
        # If both tokens are full names but are not equal:
        if token_a == "full" and token_b == "full" and value_a != value_b:
            return False
        
        # If both tokens are initials and are not equal
        if token_a == "initial" and token_b == "initial" and value_a != value_b:
            return False
        
        # If one is an initial and one is full, and the initial doesn't match the first letter of the full:
        if token_a == "initial" and token_b == "full" and value_a != value_b[0]:
            return False
        if token_a == "full" and token_b == "initial" and value_a[0] != value_b:
            return False
    
    # If passing all tests for all surnames and given names, it is a match!
    return True

def author_search(logger, df_papers, entry_count, key_authors):
    """Searches a paper for the authors of interest.

    inputs
    ------
    logger      : RootLogger
        The logger object.
    df_papers   : pandas.DataFrame
        Contains all papers.
    entry_count : int
        Index of the paper in the DataFrame.
    authors     : list
        All authors of interest that are being searched for.
    """

    if key_authors is None:
        logger.debug("No authors to search for...")
        
    # If there is at least one author of interest
    if key_authors is not None:

        logger.debug("Searching for Authors")

        # Loop over the authors of the paper
        for paper_author in df_papers.loc[entry_count, "Authors"]:

            # Loop over the authors in the search terms
            for key_author in key_authors:

                # Search the author field of the paper for any key authors
                key_author_match = authors_match(key_author, paper_author)

                # If an author is found:
                if key_author_match:

                    logger.debug("Found author: {:} | Matched with: {:}".format(key_author, paper_author))
                    
                    # Increase the number of author matches by 1
                    df_papers.loc[entry_count, "Authors Matches"] += 1
                    
                    # Add the author to the list of found authors
                    # Use the author name from the paper so that the user is shown exactly what was matched
                    df_papers.loc[entry_count, "Found Authors"].append(paper_author)

        if df_papers.loc[entry_count, "Authors Matches"] == 0:
            logger.debug(" ... none found")

    return

def word_search(logger: logging.Logger, df_papers: pd.DataFrame, entry_count: int, search_terms: dict[str, str], key: str) -> None:
    """Searches a paper for keyword matches.

    inputs
    ------
    logger       : The logger object.
    df_papers    : Contains all papers and their information.
    entry_count  : Index of the paper in the DataFrame.
    search_terms : Contains all of the search terms.
    key          : The search_terms dictionary key for which types of words should be searched for.
    """

    logger.debug("Searching for {:}".format(key))

    # # Compute the number of words we are searching for. Used to normalise the score?
    # num_words = len(search_terms[key])

    # Search all titles and abstracts for words in the supplied key
    for word in search_terms[key]:

        # Search the author field in the entry
        title_match = re.search(r"\b"+word+r"\b", df_papers.loc[entry_count, "Title"], re.IGNORECASE)

        # If a match is found in the title:
        if title_match:

            # Count the number of matches
            num_title_matches = len( re.findall(r"\b"+word+r"\b", df_papers.loc[entry_count, "Title"], re.IGNORECASE) )

            logger.debug("Found {:} {:} time(s) in the title.".format(word, num_title_matches))

            # Add to score
            df_papers.loc[entry_count, key+" Matches"]["Title"] += num_title_matches

        # If something exists in the abstract field, search it for matches
        if df_papers.loc[entry_count, "Abstract"] is not None:
            
            abstract_match = re.search(r"\b"+word+r"\b", df_papers.loc[entry_count, "Abstract"], re.IGNORECASE)

            # If a match is found in the abstract:
            if abstract_match:

                # Count the number of matches
                num_abstract_matches = len( re.findall(r"\b"+word+r"\b", df_papers.loc[entry_count, "Abstract"], re.IGNORECASE) )

                logger.debug("Found {:} {:} time(s) in the abstract.".format(word, num_abstract_matches))

                df_papers.loc[entry_count, key+" Matches"]["Abstract"] += num_abstract_matches
            
    # Compute the total number of matches
    df_papers.loc[entry_count, key+" Matches"]["Total"] = ( df_papers.loc[entry_count, key+" Matches"]["Title"]
                                                          + df_papers.loc[entry_count, key+" Matches"]["Abstract"] )

    if df_papers.loc[entry_count, key+" Matches"]["Total"] == 0:
        logger.debug(" ... none found")

    return

def score_papers_matches(self):
    """Scores the papers based on the number of matches found.
    NOTE: This function also counts the number of matches.

    inputs
    ------
    self : Papers object
    """

    self.logger.info("Finding keyword matches")

    # Loop over all entries
    for entry_count in range(0, len(self.df_papers)):

        progress_bar(entry_count, len(self.df_papers)) # No time estimate as it should always be fast. A mac laptop can filter 750 papers per second

        self.logger.debug("Seaching for matches in arXiv:{:}.".format(self.df_papers.loc[entry_count, "arXiv Number"]))
        
        # Seach for Authors
        author_search(self.logger,
                                           self.df_papers,
                                           entry_count,
                                           self.search_terms["Authors"])

        # Search for included words
        word_search(self.logger,
                    self.df_papers,
                    entry_count,
                    self.search_terms,
                    "Included Words")

        # Search for excluded words
        word_search(self.logger,
                    self.df_papers,
                    entry_count,
                    self.search_terms,
                    "Excluded Words")

        self.logger.debug("Computing a score for arXiv:{:}.".format(self.df_papers.loc[entry_count, "arXiv Number"]))

        # # Compute penalties
        # Author lists are penalised for being above a count of 25
        # Titles are boosted/penalised for being below/above a word count of 18
        # Abstracts are boosted/penalised for being below/above a word count of 250
        authors_penalty  =  25 / self.df_papers.loc[entry_count, "Number of Authors"]
        title_penalty    =  18 / self.df_papers.loc[entry_count, "Number of Words"]["Title"]
        abstract_penalty = 250 / self.df_papers.loc[entry_count, "Number of Words"]["Abstract"]
        self.logger.debug("Penalties | Authors = {:} | Title = {:} | Abstract = {:} |".format(authors_penalty, title_penalty, abstract_penalty))

        # Compute the Author score:
        authors_found   = self.df_papers.loc[entry_count, "Authors Matches"]
        authors_score   = min(authors_found * authors_penalty, 1.)
        self.df_papers.loc[entry_count, "Authors Score"] = max(authors_score, 0)

        self.logger.debug("Author statistics:")
        self.logger.debug("| Total authors = {:} | Found = {:} |".format(self.df_papers.loc[entry_count, "Number of Authors"], authors_found))
        self.logger.debug("| Author score = {:} |".format(self.df_papers.loc[entry_count, "Authors Score"]))


        # # Compute word scores
        # They are bound to the interval [0, 1] via min/max functions
        # An interesting title has one or two matches
        # An interesting abstract has ~5 matches

        # Compute the Included Word scores:
        inc_title_count    = self.df_papers.loc[entry_count, "Included Words Matches"]["Title"]
        inc_abstract_count = self.df_papers.loc[entry_count, "Included Words Matches"]["Abstract"]
        inc_title_score    = min( title_penalty * inc_title_count / 1.0, 1.0 )
        inc_abstract_score = min( abstract_penalty * inc_abstract_count / 5.0, 1.0 )
        inc_total_score    = ( inc_title_score + inc_abstract_score ) / 2.0
        # Place scores into the dataframe
        self.df_papers.loc[entry_count, "Included Words Score"]["Title"]    = inc_title_score
        self.df_papers.loc[entry_count, "Included Words Score"]["Abstract"] = inc_abstract_score
        self.df_papers.loc[entry_count, "Included Words Score"]["Total"]    = inc_total_score

        self.logger.debug("Included word statistics:")
        self.logger.debug("| Title Matches = {:} | Title Score = {:} |".format(inc_title_count, inc_title_score))
        self.logger.debug("| Abstract Matches = {:} | Abstract Score = {:} |".format(inc_abstract_count, inc_abstract_score))
        self.logger.debug("| Total Score = {:} |".format(inc_total_score))

        # Compute the Excluded words scores:
        exc_title_count    = self.df_papers.loc[entry_count, "Excluded Words Matches"]["Title"]
        exc_abstract_count = self.df_papers.loc[entry_count, "Excluded Words Matches"]["Abstract"]
        exc_title_score    = min( title_penalty * exc_title_count / 1.0, 1.0 )
        exc_abstract_score = min( abstract_penalty * exc_abstract_count / 5.0, 1.0 )
        exc_total_score    = ( exc_title_score + exc_abstract_score ) / 2.0
        # Place scores into the dataframe
        self.df_papers.loc[entry_count, "Excluded Words Score"]["Title"]    = exc_title_score
        self.df_papers.loc[entry_count, "Excluded Words Score"]["Abstract"] = exc_abstract_score
        self.df_papers.loc[entry_count, "Excluded Words Score"]["Total"]    = exc_total_score

        self.logger.debug("Excluded word statistics:")
        self.logger.debug("| Title Matches = {:} | Title Score = {:} |".format(exc_title_count, exc_title_score))
        self.logger.debug("| Abstract Matches = {:} | Abstract Score = {:} |".format(exc_abstract_count, exc_abstract_score))
        self.logger.debug("| Total Score = {:} |".format(-exc_total_score))

        # Compute the Final score:
        self.df_papers.loc[entry_count, "Final Score"] = max(inc_total_score - exc_total_score, +0)

        self.logger.debug("Final Score = {:}".format(self.df_papers.loc[entry_count, "Final Score"]))

    progress_bar(len(self.df_papers), len(self.df_papers))

    return

def score_papers_ML(self):
    """Scores the papers based on a machine-learning algorithm.
    NOTE: This method is not implemented. Current plan is to create a model that can be traied by the user on a directory containing many .pdf files. This function would then use said model to score each paper in the arXiv search.

    inputs
    ------
    self : Papers object

    outputs
    -------
    entries_of_note_unique : list
        Contains the indices of all papers that pass the filter.
    """

    self.logger.error("Attempting to use ML model to filter papers. This has not been implemented yet. Returning no results.\n")
    raise

def filter_papers_score(self):
    """Filters the papers based on the number and type of matches with the search terms.
    If a paper is scored above some threshold, it is shown.
    NOTE: May need some more optimisation.

    inputs
    ------
    self : Papers object

    outputs
    -------
    entries_of_note_sorted : list
        Contains the indices of all papers that pass the filter, in order of their score.
    """

    # Define the thresholds
    # Words
    # 0.50 => quite generous with what papers are opened. 
    # 0.65 => feels like a good limit to ensure the papers are interesting
    # 0.85 => can potentially miss something
    # 1.00 => too strict if there are any 'excluded words'
    word_threshold = 0.65
    # Authors
    author_threshold = 0.95 # At least one author in every 25

    self.logger.info("Filtering papers based on scores")

    # Loop over all entries
    entries_of_note = []
    scores          = []
    for entry_count in range(0, len(self.df_papers)):

        # Extract arXiv ID
        ID = self.df_papers.loc[entry_count, "arXiv Number"]

        # Extract scores
        author_score = self.df_papers.loc[entry_count, "Authors Score"]
        word_score   = self.df_papers.loc[entry_count, "Final Score"]

        # If an Author was found, append it to the entries of note
        if author_score >= author_threshold:

            self.logger.debug("Adding paper: {:} (Author score = {:})".format(ID, author_score))

            entries_of_note.append(entry_count)
            scores.append(author_score)

        # Otherwise, if the score is above the threshold, append it to the entries of note
        elif word_score >= word_threshold:

            self.logger.debug("Adding paper: {:} (Word score = {:})".format(ID, word_score))

            entries_of_note.append(entry_count)
            scores.append(word_score)

    # Sort the entries of note by their score
    self.logger.info("Sorting papers based on score (descending).")
    entries_of_note_sorted = np.array(entries_of_note)[np.array(scores).argsort()[::-1]]

    return entries_of_note_sorted

def filter_papers_matches(self):
    """Filters the papers based on matches with the search terms.
    NOTE: This method is not favoured. Papers that are not interesting to the user can be shown based on the inclusion of certain key words, leading to a large list that needs to be manually checked. Meanwhile, papers that would be considered interesting can be excluded based on other key words, leading to interesting papers not being shown at all.

    inputs
    ------
    self : Papers object

    outputs
    -------
    entries_of_note_unique : list
        Contains the indices of all papers that pass the filter.
    """

    self.logger.info("Filtering papers based on word matching")

    # Loop over all entries
    entries_of_note = []
    for entry_count in range(0, len(self.df_papers)):

        # If an Author was found, append it to the entries of note
        if self.df_papers.loc[entry_count, "Authors Matches"] >= 1:

            self.logger.debug("Adding paper: {:} (found author)".format(self.df_papers.loc[entry_count, "arXiv Number"]))

            entries_of_note.append(entry_count)

        # If there were included word matches and *no* excluded word matches, append
        elif ( self.df_papers.loc[entry_count, "Included Words Matches"]["Total"] >= 1 ) and ( self.df_papers.loc[entry_count, "Excluded Words Matches"]["Total"] == 0 ):

            self.logger.debug("Adding paper: {:} (found word)".format(self.df_papers.loc[entry_count, "arXiv Number"]))

            entries_of_note.append(entry_count)

    return entries_of_note