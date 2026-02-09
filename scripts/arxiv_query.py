# Import libraries
from scripts.string_handling import normalise_string
from scripts.utils           import progress_bar

import xml.etree.ElementTree as ET
import pandas                as pd

import urllib.request
import time
import sys

def arxiv_errorcheck(max_num, sleep_timer, blocksize):
    """Runs some basic error checks on the reesults of the arXiv API pull
    """

    # If no papers were found in the search, raise an error
    # This should catch deferred mailings
    if max_num == 0:
        raise ValueError("There were no papers submitted to the arXiv.\n            Refine search dates and/or categories and check for deferred mailings:\n            https://info.arxiv.org/help/availability.html")

    # If there are too many papers then there can be issues with the arXiv API.
    # While the API will likely return an error, catch it here as well just in case
    if max_num >= 30000:
        
        raise ValueError("Number of papers is too large. Refine search dates and/or categories.")
    
    # 200 papers will take one minute. Print a warning.
    if 200 <= max_num < 2000:

        print("WARNING: there are {:d} papers. The search will take {:.1f} minutes.".format(max_num, max_num*sleep_timer/(blocksize*60)))

    # 2,000 papers will take ten minutes. Prompt the user.
    elif max_num >= 2000:

        user_prompt = input("WARNING: there are {:d} papers. The search will take {:.1f} minutes. Continue? [y/N]: ".format(max_num, max_num*sleep_timer/(blocksize*60))).strip().lower()

        # If they want to continue, do nothing.
        # If they do not want to continue, end the search
        if user_prompt != "y":

            sys.exit("Cancelling the search.")

    return

def arxiv_query(url, start_date, end_date, cats, start_num, end_num):

    # Format the url
    formatted_url = url.format(start_year  = start_date.year,
                               start_month = start_date.month,
                               start_day   = start_date.day,
                               end_year    = end_date.year,
                               end_month   = end_date.month,
                               end_day     = end_date.day,
                               cats        = cats,
                               start_num   = start_num,
                               end_num     = end_num)
    
    # Query the server
    with urllib.request.urlopen(formatted_url) as f:
        xml_data = f.read()

    # Parse the xml
    parsed_xml_data = ET.fromstring(xml_data)

    return parsed_xml_data

def arxiv_initial_pull(ns, url, start_date, end_date, cats, search_sleeptimer, search_blocksize):
    """Performs the initial query to obtain important run information
    """

    print("Obtaining arXiv info. Estimated time: {:d} seconds".format(search_sleeptimer)) # Always a single sleep

    # Display a progress bar
    progress_bar(0, 1, 3)

    # Perform the query
    xml_data = arxiv_query(url,
                           start_date,
                           end_date,
                           cats,
                           0,
                           1)
    
    max_num = int(xml_data.find("opensearch:totalResults", ns).text)
    
    progress_bar(1, 1)
    print("")

    arxiv_errorcheck(max_num, search_sleeptimer, search_blocksize)

    return max_num

def extract_paper(ns, xml):
    """
    returns
    papers : list
    """
    
    papers = []

    # Loop over the entries (papers) within the current search
    for entry in xml.findall("atom:entry", ns):

        # Previously, when parsing the emails, there would be 'revised' versions. I would skip them, and they typically had no abstract.
        # The search that is being used now specifically uses "submitted date" as the criteria for being included, so I think there will never be any revised papers or empty abstracts.
        # However, I have kept the relevant columns and error checks just in case.

        published_date = entry.find("atom:published", ns).text
        updated_date   = entry.find("atom:updated", ns).text

        author_list = [author.find("atom:name", ns).text for author in entry.findall("atom:author", ns)]

        # Place information in a dictionary
        paper = {
            "arXiv Number"    : entry.find("atom:id", ns).text.split("/")[-1],
            "Title"           : entry.find("atom:title", ns).text.strip(),
            "Authors"         : normalise_string( ", ".join(f"{author}" for author in author_list) ),
            "Revised?"        : updated_date > published_date,
            "Abstract"        : entry.find("atom:summary", ns).text.strip(),
            "url"             : entry.find("atom:id", ns).text.strip(),
            "Author Match"    : False,
            "IncWord Match"   : False,
            "ExcWord Match"   : False,
        }

        papers.append(paper)

    return papers

def arxiv_loop_pull(ns, url, start_date, end_date, cats, max_num, search_sleeptimer, search_blocksize):
    """Performs the initial query to obtain important run information
    """

    entries = []
    print("Searching for papers. Estimated time: {:d} seconds".format(-search_sleeptimer*(max_num//-search_blocksize)))
    for ii in range(0, max_num, search_blocksize):

        # Compute the progress of the loop
        if ii+search_blocksize > max_num:
            remaining_steps = 1
        else:
            remaining_steps = -((max_num-ii)//-search_blocksize)

        # Print the progress bar
        progress_bar(ii, max_num, remaining_steps * search_sleeptimer)
        # Sleep before the query so that there is no dead time on the last query. Also need to sleep here as we do not wait after the initial API call
        time.sleep(search_sleeptimer)

        # Query the API
        parsed_xml = arxiv_query(url, start_date, end_date, cats, ii, ii+search_blocksize)
        
        entries.extend(extract_paper(ns, parsed_xml))

    progress_bar(max_num, max_num)
    print("")

    # Place into a dataframe
    df = pd.DataFrame(entries)

    return df
