# Import libraries
from scripts.utils import progress_bar, clear_progress_bar

import numpy as np

import re

def author_search(df, entry_count, search_terms, logger):
    """
    All search terms are surrounded by break identifiers (\b).
    """

    author_str = ""
        
    # If there is at least one author of interest
    if search_terms["Authors"] is not None:

        logger.debug("Searching for Authors")

        author_match_str = ""

        # Define a value used to print a string that shows if any authors of interest are found
        if search_terms["Authors"] is not None:

            # Length of the longest name, plus eight characters for ', et al.' incase there are multiple matches
            author_strfill = len(max(search_terms["Authors"], key=len)) + 8

        # Loop over the authors in the search terms
        for author in search_terms["Authors"]:

            # Search the author field in the entry
            author_match = re.search(r"\b"+author+r"\b", df["Authors"][entry_count])

            # If an author is found:
            if author_match:

                clear_progress_bar(logger, 10)
                logger.debug("Found {:}".format(author))
                    
                # If the paper has an author match, add it to a string
                # If no match has been found yet:
                if not df.loc[entry_count, "Authors Match"]:
                    author_match_str = "\n    {: >{fill}}:  {url:}".format(author, fill=author_strfill, url=df["url"][entry_count])
                # If the paper has already had a match, add et at.
                else:
                    author_match_str = "\n    {: >{fill}}:  {url:}".format(author+", et al.", fill=author_strfill, url=df["url"][entry_count])
                
                # Set the entry in the dataframe for the author match key to True
                df.loc[entry_count, "Authors Match"] = True

                # Increase the score by 10 points for each match
                df.loc[entry_count, "Score"] += 10

        author_str = author_match_str

    return df, author_str

def word_search(df, entry_count, search_terms, key, multiplier, logger):
    """
    All search terms are surrounded by break identifiers (\b).

    inputs
    ------
    multiplier : float
        Multiplies the score
    """

    logger.debug("Searching for {:}".format(key))

    # Search all titles and abstracts for words in the supplied key
    for word in search_terms[key]:

        # Search the author field in the entry
        title_match = re.search(r"\b"+word+r"\b", df["Title"][entry_count], re.IGNORECASE)

        # If a match is found in the title:
        if title_match:

            # Count the number of matches
            number_title_matches = len( re.findall(r"\b"+word+r"\b", df["Title"][entry_count], re.IGNORECASE) )

            clear_progress_bar(logger, 10)
            logger.debug("Found {:} {:} time(s) in the title.".format(word, number_title_matches))

            # Add to score
            df.loc[entry_count, "Score"] += multiplier * 10 * number_title_matches

        # If something exists in the abstract field, search it for matches
        if df["Abstract"][entry_count] is not None:
            
            abstract_match = re.search(r"\b"+word+r"\b", df["Abstract"][entry_count], re.IGNORECASE)

            # If a match is found in the abstract:
            if abstract_match:

                # Count the number of matches
                number_abstract_matches = len( re.findall(r"\b"+word+r"\b", df["Abstract"][entry_count], re.IGNORECASE) )

                logger.debug("Found {:} {:} time(s) in the abstract.".format(word, number_abstract_matches))

                # Add to score
                df.loc[entry_count, "Score"] += multiplier * 5 * number_abstract_matches
            
        # If a match is found anywhere, set the IncWord flag to True
        if title_match or abstract_match:
            
            print(key+" Match")
            df.loc[entry_count, key+" Match"] = True

    return df

def score_papers(df, search_terms, logger):

    # Loop over all entries
    entries_of_note = []
    author_str = "    Found Author(s)"
    for entry_count in range(0, len(df)):

        progress_bar(entry_count, len(df)) # No time estimate as it should always be fast. ~1200 papers take less than a second on a 2023 macbook

        clear_progress_bar(logger, 10)
        logger.debug("Seaching for matches in paper {:}.".format(df.loc[entry_count, "arXiv Number"]))
        
        # Seach for Authors
        df, author_matches_str = author_search(df, entry_count, search_terms, logger)
        author_str            += author_matches_str

        # Search for included words
        df = word_search(df, entry_count, search_terms, "Included Words", +1, logger)

        # Search for excluded words
        df = word_search(df, entry_count, search_terms, "Excluded Words", -1, logger)
        
        logger.debug("Paper {:} was scored {:}".format(df["arXiv Number"][entry_count], df["Score"][entry_count]))

    progress_bar(len(df), len(df))

    return df, author_str

def filter_papers_score(df, search_terms, logger):
    """Filters the papers based on some criteria (currently the search terms).
    If a paper is scored above some threshold, it is shown.
    NOTE: 

    inputs
    ------
    df           : pandas.DataFrame
        Contains all papers and their information.
    search_terms : dict
        Contains all search terms used to filter papers.
    logger       : RootLogger
        The logger object

    outputs
    -------
    entries_of_note_unique : list
        Contains the indices of all papers that pass the filter.
    """

    # Define the threshold
    # Should be calculated based on the number of included/excluded words?
    # Or, show the top x% of papers?
    threshold = 50

    logger.info("Finding papers of interest.")

    # Score the papers
    df, author_str = score_papers(df, search_terms, logger)

    # Loop over all entries
    entries_of_note = []
    for entry_count in range(0, len(df)):

        logger.debug("arXiv:{:} was scored {:}".format(df.loc[entry_count, "arXiv Number"], df.loc[entry_count, "Score"]))

        # If an Author was found, append it to the entries of note
        if df["Score"][entry_count] >= threshold:

            entries_of_note.append(entry_count)

    # Print the list of the found authors and their papers
    # Do not pass this through the logger -- it should always be shown (if at least one was found)
    if any(df["Authors Match"]):
        print(author_str)

    entries_of_note_unique = np.unique(entries_of_note)

    return entries_of_note_unique

def filter_papers_binary(df, search_terms, logger):
    """Filters the papers based on some criteria (currently the search terms).
    If a paper matches the criteria, is is shown.
    NOTE: This method is not favoured. Papers that are not interesting to the user can be shown based on the inclusion of certain key words, leading to a large list that needs to be manually gone through. Meanwhile, papers that would be considered interesting can be excluded based on other key words, leading to interesting papers not being shown at all.

    inputs
    ------
    df           : pandas.DataFrame
        Contains all papers and their information.
    search_terms : dict
        Contains all search terms used to filter papers.
    logger       : RootLogger
        The logger object

    outputs
    -------
    entries_of_note_unique : list
        Contains the indices of all papers that pass the filter.
    """

    logger.info("Finding papers of interest.")

    # Score the papers
    df, author_str = score_papers(df, search_terms, logger)

    # Loop over all entries
    entries_of_note = []
    for entry_count in range(0, len(df)):

        # If an Author was found, append it to the entries of note
        if df["Authors Match"][entry_count] == True:

            print("adding paper")

            entries_of_note.append(entry_count)

        # If there were included word matches and *no* excluded word matches, append
        elif ( df["Included Words Match"][entry_count] == True ) and ( df["Excluded Words Match"][entry_count] == False ):

            print("adding paper")

            entries_of_note.append(entry_count)

    # Print the list of the found authors and their papers
    # Do not pass this through the logger -- it should always be shown (if at least one was found)
    if any(df["Authors Match"]):
        print(author_str)

    entries_of_note_unique = np.unique(entries_of_note)

    return entries_of_note_unique

# Current method to filter papers.
def filter_papers(df, search_terms, logger):
    """Filter papers"""

    # # Binary search. Filter based on terms found.
    # entries_or_note_unique = filter_papers_binary(df, search_terms, logger)

    # Score search. Filter based on score.
    entries_or_note_unique = filter_papers_score(df, search_terms, logger)

    # # Machine-laerning search. Filter based on score from the ML algorithm
    # # Not yet implemented
    # entries_or_note_unique = filter_papers_ML(df, search_terms, logger)

    return entries_or_note_unique