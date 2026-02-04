# Readme

This script searches the arXiv (within the categories of interest) for all papers since the previous execution.
It then performs some basic keyword matching, and opens all papers with matches in the web browser.

Add the following to your bash script:

`alias arxiv='python3 /path/to/arXiv_Catchup/scan.py'`

The search can then be performed in the CLI from anywhere by running:

`$ arxiv`

## Usage

There are three files that contain certain terms that will be searched for.

`key_authors.txt` contains the last names of all authors. Every paper with a match will be opened in the browser, and a line will be written in the command line with the url.

`key_words.txt` contains various words. Every paper with a match will be opened in the browser, unless a word from the exclusion list is found.

`exclusion_words.txt` contains various words. Every paper with a match will *not* be opened in the browser, unless a key author is also found for said paper.

Add each term on a separate line.
Lines starting with `#` are ignored.
Multi-word terms can be used, as can author names with spaces.
