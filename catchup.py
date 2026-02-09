from scripts.main import main

import os

if __name__ == "__main__":

    ## Setup
    # Find the directory of the script
    cdir = os.path.dirname(os.path.realpath(__file__))

    main(cdir)
