# Import libraries
import datetime
import os

# Technically this script is not tied to the daily listings and when they are posted.
# However, as the API is not updated simultaneously -- with papers being added at approximately the same time as the daily listings.
# Hence, it is best to time the searches around the daily listings.

# The daily list of papers is typically released around 02:00 UTC to 04:00 UTC, though can be a little later. We use 06:00 UTC here for safety.
# They are published on Monday, Tuesday, Wednesday, Thursday, and Friday (UTC).
# The lists contain all papers published from 19:00 UTC two posting days ago to 19:00 UTC on the prior posting day

# For example:
#     If searching on Wednesday at 20:00 UTC, we need to search the list posted on Wednesday at 06:00 UTC, which will include papers from Monday 19:00 UTC to Tuesday 19:00 UTC.
#     If searching on Tuesday at 05:00 UTC, we need to search the list posted on Monday day at 06:00 UTC, which will include papers from Thursday 19:00 UTC to Friday 19:00 UTC.

# No lists are released on certain days. These days are chosen ad-hoc, and are days that are important to USAians. It includes Christmas, their Thanksgiving, and others.
# The API is not updated on these days, so the search should return zero results, and raise an error.
# Running the following day should work, and no papers *should* be missed (not tested)

def write_date(filename, date):
    """Write a datetime.date object to a file.

    inputs
    ------
    filename : str
        Path+filename of the `prev_search.txt` file.
    date     : datetime.date
        Date that is being written
    """

    with open(filename, "w") as f:
        f.write(date.isoformat())

    return

def is_posting_day_bool(dt):
    """Determines if the input day iss an arXiv posting day.
    Does not account for deferred listings.

    inputs
    ------
    dt : datetime.date
        Date to be checked if it is a posting day

    outputs
    -------
    : bool
        True if date is valid, False otherwise
    """

    # dt.weekday() = 0 for Monday, ..., 4 for Friday, 5 for Saturday, and 6 for Sunday

    # Lists are posted for 0 <= dt.weekday() <= 4

    return dt.weekday() <= 4

def is_searching_day_bool(dt):
    """Determines if the input day is a valid arXiv search day.

    inputs
    ------
    dt : datetime.date
        Date to be checked if it is a valid search day

    outputs
    -------
    : bool
        True if date is valid, False otherwise
    """

    # dt.weekday() = 0 for Monday, ..., 4 for Friday, 5 for Saturday, and 6 for Sunday

    # Searching days are 0 <= dt.weekday() <=3 and dt.weekday() == 6

    if dt.weekday() == 6:

        return True
    
    elif 0 <= dt.weekday() <= 3:

        return True
    
    else:

        return False

def calc_search_endtime(now, post_time, search_time):
    """Computes the most recent arXiv daily list posting relative to the input time.

    inputs
    ------
    now       : datetime.time (with timezone and date)
        Either the current time, or the time input from the CLI.
    post_time : datetime.time (with timezone)
        Time that arXiv postings occur

    outputs
    -------
    search_endtime : datetime.time (with timezone and date)
        Most recent valid search endtime relative to the input `now`.
    """

    # If now is after post_time, search_time will be 19:00 the previous day
    if now.timetz() > post_time:
        temp_date = now - datetime.timedelta(days=1)

    # Else, if now is before post_time, search_time will be 19:00 the day before previous
    else:
        temp_date = now - datetime.timedelta(days=2)

    while not is_searching_day_bool(temp_date):

        temp_date -= datetime.timedelta(days=1)

    search_endtime = datetime.datetime.combine(temp_date.date(), search_time)

    return search_endtime

def calc_next_posttime(now, post_time):
    """Return the datetime of the next arXiv daily list posting relative to the input time `now`.

    inputs
    ------
    now       : datetime.time (with timezone and date)
        Either the current time, or the time input from the CLI.
    post_time : datetime.time (with timezone)
        Time that arXiv postings occur

    outputs
    -------
    next_post_time : datetime.time (with timezone and date)
        Next valid arXiv list post time relative to the input `now`.
    """

    # If now is after post_time, the next post_time will be 06:00 the following day
    if now.timetz() > post_time:

        temp_date = now + datetime.timedelta(days=1)

    # Else, if now is before post_time, the next post_time will be 06:00 the next post_day
    else:
        temp_date = now

    while not is_posting_day_bool(temp_date):

        temp_date += datetime.timedelta(days=1)

    next_post_time = datetime.datetime.combine(temp_date.date(), post_time)

    return next_post_time

def parse_date(date_str, name, search_time, list_post_time, logger):
    """Take an input string and convert to the correct datetime object.

    inputs
    ------
    date_str       : str
        ISO representation of the date
    name           : str
        Name of the date (e.g. start_time, end_time)
    search_time    : datetime.time (timezone aware)
        Time of the arXiv search start/end points
    list_post_time : datetime.time (timezone aware)
        Time of the arXiv daily postings

    outputs
    -------
    parsed_time : datetime.time (timezone aware)
        Time, with the correct timezone
    parsed_date : datetime.date (timezone aware)
        Date, with the correct timezone
    """

    try:

        raw_datetime = datetime.datetime.combine(datetime.datetime.strptime(date_str, "%Y-%m-%d"), search_time)
        parsed_date  = raw_datetime.date()
        parsed_time  = raw_datetime.timetz()

        # If the date is not a valid search date, warn the user and roll the day back to the previous valid day
        if not is_searching_day_bool(parsed_date):

            logger.warning("{:} is not a valid search date. Rolling back to the previous valid day".format(name))

            parsed_date = calc_search_endtime(raw_datetime, search_time, list_post_time).date()

        return parsed_time, parsed_date
    
    except ValueError:

        logger.critical("{:} must be in the YYYY-mm-dd format.\n".format(name))
        raise

def date_error_check(current_time, start_date, end_date, list_post_time, logger):
    """Performs some error checks on the dates to ensure the search period is valid.

    inputs
    ------
    current_time   : datetime.time (timezone aware)
        Time the script was executed.
    start_date     : datetime.date (timezone aware)
        Start date of the search.
    end_date       : datetime.date (timezone aware)
        End date of the search.
    list_post_time : datetime.time (timezone aware)
        Time that the arXiv daily postings occur.
    """

    # Compute how long the search is covering
    prev_run = end_date - start_date

    # Compute the time that the next list will be posted
    nextlist_time   = calc_next_posttime(current_time, list_post_time)
    time_until_next = nextlist_time - current_time

    t_days    = time_until_next.days
    t_hours   = time_until_next.seconds//3600
    t_minutes = (time_until_next.seconds//60) - t_hours * 60

    next_post_string = ( "\n            "
                       + "The next list will be posted at {:%Y-%m-%d %H:%M (%Z)},".format(nextlist_time)
                       + "\n            "
                       + "which is {:} days, {:} hours, and {:} minutes from now.".format(t_days, t_hours, t_minutes) )

    # Compute number of days between now and the start of the search
    deltadays_now_to_search = ( current_time.date() - start_date ).days

    # Count the number of valid search days between start_date and end_date
    valid_search_days = 0
    temp_date = end_date
    while temp_date > start_date:
        valid_search_days += 1
        temp_date -= datetime.timedelta(days=1)

    # Raise some errors
    # If the search start date is in the future:
    if deltadays_now_to_search < 0:
        logger.critical("Search start date is in the future.\n")
        raise

    # If the search end date is in the future:
    elif ( current_time.date() - end_date ).days < 0:
        logger.critical("Search end date is in the future.\n")
        raise

    # If the end date is equal to the start date, tell the user to wait
    elif prev_run.days == 0:
        logger.critical("Search start/end dates are equal.{:}\n".format(next_post_string))
        raise

    # If the end date is before the start date
    elif prev_run.days < 0:
        logger.critical("Search start date is after the end date. Check for timezone issues.\n")
        raise

    # If the search period doesn't cover any searching days, tell the user to wait
    # Typically one of the previous errors will occur before this one if the entire search period is invalid
    elif deltadays_now_to_search < 7 and valid_search_days == 0:
        logger.critical("No valid search dates are included.{:}\n".format(next_post_string))
        raise

    # If there are no issues, let the user know how many days we are searching over
    else:
        logger.info("Days since the previous search: {:}".format(prev_run.days))

    return

def date_setup(args, filename_prevsearch, logger):
    """Set up the date that the script uses for the arXiv API calls.

    inputs
    ------
    args                : namespace
        CLI arguments.
    filename_prevsearch : str
        Path+filename of the `prev_search.txt` file that contains the date of the previous run.

    outputs
    -------
    start_date : datetime.date
        Start date of the arXiv API query.
    end_date   : datetime.date
        End date of the arXiv API query.
    """

    # Define the posting time of the daily list
    list_post_time = datetime.time(6, 0, tzinfo=datetime.timezone.utc) # 06:00 UTC

    # Define the posting time of the daily list
    search_time    = datetime.time(19, 0, tzinfo=datetime.timezone.utc) # 19:00 UTC

    # Obtain the current time, converted to the UTC timezone
    current_time = datetime.datetime.now(datetime.timezone.utc)

    # If start/end dates were passed on the command line, use them. Otherwise, set to None
    start_time, start_date = parse_date(args.start_date, "start-date", search_time, list_post_time, logger) if args.start_date else [None, None]
    end_time,   end_date   = parse_date(args.end_date,   "end-date", search_time, list_post_time, logger)   if args.end_date   else [None, None]

    # Compute the time at the end of the search
    # Only perform if the end_date was not passed in the command line
    if end_date is None:
        end_time = calc_search_endtime(current_time, list_post_time, search_time)
        end_date = end_time.date()

    # The date of the previous execution is saved in a file
    # If the file does not exist, create it and set the date to the listing before the last posting
    # Only perform if the start_date was not passed in the command line
    if start_date is None:
        if not os.path.exists(filename_prevsearch):

            # Compute the list time before the previous
            # This can be done by passing the end_time found above into the calc_search_endtime() function
            prev_end_time  = calc_search_endtime(end_time, list_post_time, search_time)
            
            write_date(filename_prevsearch, prev_end_time.date())

        # Load it and extract the previous runtime
        with open(filename_prevsearch, "r", encoding="utf-8") as f:

            start_time, start_date = parse_date(next(f), filename_prevsearch, search_time, list_post_time, logger)

    # Print some information. Useful to do it before error checks so that all information is visible
    logger.info("Searching from {:}/{:}/{:} 19:00 UTC to {:}/{:}/{:} 19:00 UTC".format(start_date.year, start_date.month, start_date.day, end_date.year, end_date.month, end_date.day))

    date_error_check(current_time, start_date, end_date, list_post_time, logger)

    return start_date, end_date