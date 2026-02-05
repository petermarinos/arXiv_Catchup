# Readme

Tired of reading all the Titles/Abstracts/Author Lists of every paper posted on the arXiv every single day?
Here is the solution!

This script searches the arXiv (within the categories of interest) for all papers since the previous execution.
It then performs some basic keyword matching, and opens all papers with matches in the web browser.

## Usage

### Running

Add the following to your bash script:

`alias arxiv='python3 /path/to/arXiv_Catchup/scan.py'`

The search can then be performed in the CLI from anywhere by running:

`$ arxiv`

### Auxilliary Files
There are three files that contain certain terms that will be searched for.

`key_authors.txt` contains the last names of all authors. Every paper with a match will be opened in the browser, and a line will be written in the command line with the url.

`key_words.txt` contains various words. Every paper with a match will be opened in the browser, unless a word from the exclusion list is found.

`exclusion_words.txt` contains various words. Every paper with a match will *not* be opened in the browser, unless a key author is also found for said paper.

Add each term on a separate line.
Lines starting with `#` are ignored.
Multi-word terms can be used, as can author names with spaces.

The script creates the file `catchup.txt`, which contains the date of the previous run in the format year, month, day, all on separate lines.
This date can be set manually to search back as far as desired.

### Other Notes

There are no daily listings posted over the weekend or on some USA public holidays.

Weekends are handled by the script, which will not bother searching if run on a weekend.
The papers posted on the weekend will be caught when run on Monday.

The USA public holidays are typically ad-hoc, so there is no way to account for them.
It is currently untested, but I expect the search would just return zero results, and said papers would be caught in the following search.
I may need to add a check to not update `catchup.txt` if there are zero found listings.
The next "deferred mailing" where this can be tested will be on Friday 2026/06/19.

## Future Improvements

Using a list of words to exclude can result in some interesting papers not being opened if they include a sentence on their potential application to the wider literature.
However, it reduces the list of papers that need to be checked manually by a significant margin.
Additionally, using a list of key words where there needs to be one match can result in an interesting paper *not* being detected if the authors didn't include one.
Finally, the number of papers that are genuinely interesting each week is very low, but the script still opens on the order of ~100 to be manually checked.

This could be solved by adding a machine learning module.
- Look in a directory containing `.pdf` files of all the papers you have found interesting in the past to train the model
- Run the model on the titles/abstracts of each paper and rate them
- Only open the papers if their rating is above some threshold
