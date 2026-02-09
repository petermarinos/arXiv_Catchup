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
    
    # Compute the time it will take to download all papers
    time_to_search_minutes = max_num*sleep_timer/(blocksize*60)
    
    # Print a warning if it is going to take a long time
    if 1 <= time_to_search_minutes < 5:

        print("WARNING: there are {:d} papers. The search will take {:.1f} minutes.".format(max_num, time_to_search_minutes))

    # Prompt the user if it is going to take a really long time.
    elif time_to_search_minutes >= 5:

        user_prompt = input("WARNING: there are {:d} papers. The search will take {:.1f} minutes. Continue? [y/N]: ".format(max_num,time_to_search_minutes)).strip().lower()

        # If they want to continue, do nothing.
        # If they do not want to continue, end the search
        if user_prompt != "y":

            sys.exit("Cancelling the search. Reduce search window to decrease the number of results.")

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

"""Example arXiv API pull:
<ns0:feed xmlns:ns0="http://www.w3.org/2005/Atom" xmlns:ns1="http://a9.com/-/spec/opensearch/1.1/" xmlns:ns2="http://arxiv.org/schemas/atom">
  <ns0:id>https://arxiv.org/api/RdGiJmCzUo9LqFSmMy0zaOoHqng</ns0:id>
  <ns0:title>arXiv Query: search_query=submittedDate:"{start_date}1900 TO {end_date}1900" AND cat:{cat_urlstring}&amp;id_list=&amp;start={ii}&amp;max_results={max_num}</ns0:title>
  <ns0:updated>YYYY-mm-ddTHH:MM:SSZ</ns0:updated>
  <ns0:link href="{url_search}" type="application/atom+xml" />
  <ns1:itemsPerPage>{interval}</ns1:itemsPerPage>
  <ns1:totalResults>{max_num}}</ns1:totalResults>
  <ns1:startIndex>{ii}}</ns1:startIndex>
  <ns0:entry>
    [paper entries, see below]
  </ns0:entry>
</ns0:feed>
"""

"""Example paper entry:
  <ns0:entry>
    <ns0:id>http://arxiv.org/abs/{arXiv:ID}</ns0:id>
    <ns0:title>Title text</ns0:title>
    <ns0:updated>YYYY-mm-ddTHH:MM:SSZ</ns0:updated>
    <ns0:link href="https://arxiv.org/abs/{arXiv:ID}" rel="alternate" type="text/html" />
    <ns0:link href="https://arxiv.org/pdf/{arXiv:ID}" rel="related" type="application/pdf" title="pdf" />
    <ns0:summary>Abstract text</ns0:summary>
    <ns0:category term="cat0" scheme="http://arxiv.org/schemas/atom" />
    <ns0:category term="cat1" scheme="http://arxiv.org/schemas/atom" />
    <ns0:published>2026-02-06T18:51:45Z</ns0:published>
    <ns2:comment>Comment text</ns2:comment>
    <ns2:primary_category term="cat0" />
    <ns0:author>
      <ns0:name>example name 0</ns0:name>
    </ns0:author>
    <ns0:author>
      <ns0:name>example name 1</ns0:name>
    </ns0:author>
  </ns0:entry>
"""

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

def arxiv_search(ns, url, start_date, end_date, cats, max_num, search_sleeptimer, search_blocksize):
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
