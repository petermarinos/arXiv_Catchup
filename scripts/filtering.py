# Import libraries
from scripts.utils import progress_bar

import numpy as np

import re

def filter_papers(df, search_terms):
    """Filters the papers based on some criteria (currently the search terms).

    inputs
    ------
    df           : pandas.DataFrame
        Contains all papers and their information.
    search_terms : dict
        Contains all search terms used to filter papers.

    outputs
    -------
    entries_of_note_unique : list
        Contains the indices of all papers that pass the filter.
    """

    if search_terms["Authors"] is not None:
        author_strfill = len(max(search_terms["Authors"], key=len))

    # Loop over all entries
    author_match_count = 0
    entries_of_note = []
    author_str = ""
    print("Finding papers of interest.")
    for entry_count in range(0, len(df)):

        progress_bar(entry_count, len(df)) # No time estimate as it should always be fast. ~1200 papers take less than a second on a 2023 macbook
        
        # Search all author lists for the key authors
        if search_terms["Authors"] is not None:
            for author in search_terms["Authors"]:

                # Search the author field in the entry
                author_match = re.search(r"\b"+author+r"\b", df["Authors"][entry_count])

                if author_match:
                    
                    # Set the entry in the dataframe for the author match to True
                    df.loc[entry_count, "Author Match"] = True

                    # If one author is found, output an extra line to the terminal
                    if author_match_count == 0:
                        # print("    Found Author(s)")
                        author_str += "\n    Found Author(s)"
                        author_match_count = 1
                        
                    # print("    {: >{fill}}:  ".format(key_author, fill=author_strfill), df["url"][entry_count])
                    author_str += "\n    {: >{fill}}:  {url:}".format(author, fill=author_strfill, url=df["url"][entry_count])
        
        # Search all titles and abstracts for words that I care about
        for inc_word in search_terms["Included Words"]:

            # Search the author field in the entry
            title_match    = re.search(r"\b"+inc_word+r"\b", df["Title"][entry_count], re.IGNORECASE)

            if df["Abstract"][entry_count] is not None: # Skip empty abstract entries
                abstract_match = re.search(r"\b"+inc_word+r"\b", df["Abstract"][entry_count], re.IGNORECASE)
                
            if title_match or abstract_match:
                
                df.loc[entry_count, "IncWord Match"] = True
        
        # Search all titles and abstracts for words that I want to exclude
        if search_terms["Excluded Words"] is not None:
            for exc_word in search_terms["Excluded Words"]:

                # Search the author field in the entry
                title_match    = re.search(r"\b"+exc_word+r"\b", df["Title"][entry_count], re.IGNORECASE)

                if df["Abstract"][entry_count] is not None: # Skip empty abstract entries

                    abstract_match = re.search(r"\b"+exc_word+r"\b", df["Abstract"][entry_count], re.IGNORECASE)

                if title_match or abstract_match:

                    df.loc[entry_count, "ExcWord Match"] = True

        # If key_authors=True, always keep
        # If there were keyword matches and *no* matches with excluded words, keep
        if df["Author Match"][entry_count] == True:
            entries_of_note.append(entry_count)
        elif df["IncWord Match"][entry_count]==True and df["ExcWord Match"][entry_count]==False:
            entries_of_note.append(entry_count)

    progress_bar(len(df), len(df))
    print(author_str)

    entries_of_note_unique = np.unique(entries_of_note)

    return entries_of_note_unique