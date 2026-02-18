# Import libraries
import datetime
import logging

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

def is_posting_day_bool(dt: datetime.date) -> bool:
    """Determines if the input day iss an arXiv posting day.
    Does not account for deferred listings.

    inputs
    ------
    dt : Date to be checked if it is a posting day

    outputs
    -------
    : True if date is a valid posting day, False otherwise
    """

    # dt.weekday() = 0 for Monday, ..., 4 for Friday, 5 for Saturday, and 6 for Sunday

    # Lists are posted for 0 <= dt.weekday() <= 4

    return dt.weekday() <= 4

def is_searching_day_bool(dt: datetime.date) -> bool:
    """Determines if the input day is a valid arXiv search day.

    inputs
    ------
    dt : Date to be checked if it is a valid search day

    outputs
    -------
    : True if date is a valid search day, False otherwise
    """

    # dt.weekday() = 0 for Monday, ..., 4 for Friday, 5 for Saturday, and 6 for Sunday

    # Searching days are 0 <= dt.weekday() <=3 and dt.weekday() == 6

    if dt.weekday() == 6:

        return True
    
    elif 0 <= dt.weekday() <= 3:

        return True
    
    else:

        return False

def calc_search_endtime(input_time: datetime.datetime, search_time: datetime.time, post_time: datetime.time) -> datetime.datetime:
    """Computes the most recent arXiv daily list posting relative to the input time.

    inputs
    ------
    input_time  : datetime.time (with timezone and date)
        Either the current time, or the time input from the CLI.
    search_time : datetime.time (with timezone)
        Time that arXiv seaches use
    post_time   : datetime.time (with timezone)
        Time that arXiv postings occur

    outputs
    -------
    search_endtime : datetime.time (with timezone and date)
        Most recent valid search endtime relative to the input `now`.
    """

    # If now is after post_time, search_time will be 19:00 the previous day
    if input_time.timetz() > post_time:
        temp_date = input_time - datetime.timedelta(days=1)

    # Else, if now is before post_time, search_time will be 19:00 the day before previous
    else:
        temp_date = input_time - datetime.timedelta(days=2)

    while not is_searching_day_bool(temp_date):

        temp_date -= datetime.timedelta(days=1)

    search_endtime = datetime.datetime.combine(temp_date.date(), search_time)

    return search_endtime

def calc_next_posttime(input_time: datetime.datetime, post_time: datetime.time) -> datetime.datetime:
    """Return the datetime of the next arXiv daily list posting relative to the input time `now`.

    inputs
    ------
    input_time : datetime.time (with timezone and date)
        Either the current time, or the time input from the CLI.
    post_time  : datetime.time (with timezone)
        Time that arXiv postings occur

    outputs
    -------
    next_post_time : datetime.time (with timezone and date)
        Next valid arXiv list post time relative to the input `now`.
    """

    # If now is after post_time, the next post_time will be 06:00 the following day
    if input_time.timetz() > post_time:

        temp_date = input_time + datetime.timedelta(days=1)

    # Else, if now is before post_time, the next post_time will be 06:00 the next post_day
    else:
        temp_date = input_time

    while not is_posting_day_bool(temp_date):

        temp_date += datetime.timedelta(days=1)

    next_post_time = datetime.datetime.combine(temp_date.date(), post_time)

    return next_post_time

def parse_date(logger: logging.Logger, date_iso: str, date_name: str, search_time: datetime.time, post_time: datetime.time) -> tuple[datetime.datetime, datetime.date]:
    """Take an input string and convert to the correct datetime object.

    inputs
    ------
    logger      : RootLogger
        The logger object
    date_iso    : str
        ISO representation of the date
    date_name   : str
        Name of the date (e.g. start_time, end_time)
    search_time : datetime.time (timezone aware)
        Time of the arXiv search start/end points
    post_time   : datetime.time (timezone aware)
        Time of the arXiv daily postings

    outputs
    -------
    parsed_time : datetime.time (timezone aware)
        Time, with the correct timezone
    parsed_date : datetime.date (timezone aware)
        Date, with the correct timezone
    """

    try:

        raw_datetime = datetime.datetime.combine(datetime.datetime.strptime(date_iso, "%Y-%m-%d"), search_time)
        parsed_date  = raw_datetime.date()
        parsed_time  = raw_datetime.timetz()

        logger.debug("Attempting to set {:} to {:}".format(date_name, date_iso))

        # If the date is not a valid search date, warn the user and roll the day back to the previous valid day
        if not is_searching_day_bool(parsed_date):

            logger.warning("{:} is not a valid date. Rolling back to the previous valid day".format(date_name))

            parsed_date = calc_search_endtime(raw_datetime, search_time, post_time).date()

        logger.debug("Set {:} to {:}".format(date_name, parsed_date))

        return datetime.datetime.combine(parsed_date, parsed_time), parsed_date
    
    except ValueError:

        logger.critical("{:} must be in the YYYY-mm-dd format.\n".format(date_name))
        raise
