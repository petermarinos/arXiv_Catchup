# README

Tired of reading all the Titles/Abstracts/Author Lists of every paper posted on the arXiv every single day?
Here is the solution!

This script searches the arXiv (within the categories of interest) for all papers since the previous execution.
It then performs some basic keyword matching, and opens all papers with matches in the web browser.

Thank you to arXiv for use of its open access interoperability.

## Usage

### Running

The script can be executed from any directory by running:

`python3 /path/to/arXiv_Catchup/catchup.py`

For frequent execution, add the following to your bash script:

`alias arxiv='python3 /path/to/arXiv_Catchup/catchup.py'`

The search can then be performed in the CLI from any directory by running:

`$ arxiv`

### CLI Arguments

There are additional arguments that can be used:
- `-f`, `--force-open` skips all confirmation dialogues and opens all links
- `-w`, `--write-to-file` skips all confirmation dialogues and writes all links to a file
- `-n`, `--new-window` opens all links in a new window (does not work on mac)
- `-s`, `--start-date` manually sets the start date for the search
- `-e`, `--end-date` manually sets the end date for the search

If both `-f` and `-w` are passed, then the scipt will do both. If neither are passed, then the script will prompt the user for their preference.
These CLI arguments can be added to the bash alias.

### Auxiliary Files

The file `search_terms.yaml` contains all terms that are used in the search.
There are four fields, `Categories`, `Authors`, `Included Words`, and `Excluded Words`.
Examples of the format required for each can be found in the provided file.
- `Categories` defines which arXiv categories are searched over. At least one must be included. The list of possible categories can be found at https://arxiv.org/category_taxonomy
- `Authors` defines which authors to highlight. Every paper with a match will be opened, and a line will be written in the command line with the url. Do not include accented characters/ligatures/etc, these are handled by the script. For example, only include 'Lopez' -- variations such as 'López' and L{\'o}pez are handled automatically. If unsure on how a special character/LaTeX command is presented in ASCII, test on the function `normalise_string()`. For submissions to journals that are more restrictive on special characters, some authors may use a spelling different to the ASCII encoding -- for those cases it is recommended to also include the alternative spellings.
- `Included Words` defines which words include papers in the results. Every match will be included, unless a word from the exclusion list is also found. At least one must be included.
- `Excluded Words` defines which words exclude papers from the results. Every match blocks a paper from being included, unless one of the authors of interest is found.

Lines starting with `#` are ignored.
Multi-word terms can be used, as can author names with spaces.
If adding acronyms, include their pluralised forms (e.g. SN and SNe or CR and CRs).
If cloning the repo, please add this file to the ignored list via the command `$ git update-index --skip-worktree search_terms.yaml` to prevent your personal search terms updating to the main branch.

The script creates the file `prev_search.txt`, which contains the date of the previous run in ISO format.
This file is ignored if manually setting the start-date of the search on the CLI.

All links are written to a file `catchup.txt` (if choosing to write to the file). Each arXiv link is written on a new line, and the script will always append the new results to the end of the file.

### Daily Mailings

There are no daily listings posted over the weekend or on some USA public holidays.

Weekends are handled by the script, which will give an error if being executed before the next listing is posted.
The papers posted on the weekend will be caught when run on Monday.

There are also "deferred mailing" days.
These days are chosen ad-hoc, and are days that are important to USAians.
It includes Christmas, their Thanksgiving, and others
Technically, this script is not tied to the daily listings, and uses a large offset in the search times.
Hence, no papers *should* be missed from the deferred mailing days (not tested).
The next deferred mailing where this can be tested will be on Friday 2026/06/19.

### Requirements

Only four packages are not part of the default python3 standard library, `pylatexenc`, `numpy`, `pandas`, and `yaml`.
Use the included `requirements.txt` file with pip to create an environment.

## Future Improvements

Using a list of words to exclude can result in some interesting papers not being opened if they include a sentence on their potential application to the wider literature.
However, it reduces the list of papers that need to be checked manually by a significant margin.
Additionally, using a list of key words where there needs to be one match can result in an interesting paper *not* being detected if the authors didn't include one.
Finally, the number of papers that are genuinely interesting each week is very low, but the script still opens on the order of ~100 to be manually checked.

This could be solved by adding a machine learning module.
- Look in a directory containing `.pdf` files of all the papers you have found interesting in the past to train the model
- Run the model on the titles/abstracts of each paper and rate them
- Only open the papers if their rating is above some threshold
