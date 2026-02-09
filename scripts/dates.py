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
# As this script is not tied to the daily listings, and provides a large offset in the search, no papers *should* be missed (not tested)

def write_date(filename, date):

    with open(filename, "w") as f:
        f.write(date.isoformat())

    return

def is_posting_day_bool(dt):

    # dt.weekday() = 0 for Monday, ..., 4 for Friday, 5 for Saturday, and 6 for Sunday

    # Lists are posted for 0 <= dt.weekday() <= 4

    return dt.weekday() <= 4

def is_searching_day_bool(dt):

    # dt.weekday() = 0 for Monday, ..., 4 for Friday, 5 for Saturday, and 6 for Sunday

    # Searching days are 0 <= dt.weekday() <=3 and dt.weekday() == 6

    if dt.weekday() == 6:

        return True
    
    elif 0 <= dt.weekday() <= 3:

        return True
    
    else:

        return False

def calc_search_endtime(now, post_time, search_time):
    """Return the datetime of the most recent arXiv daily list posting relative to the input time `now`.
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

def parse_date(date_str, name, search_time, list_post_time):

    try:

        raw_datetime = datetime.datetime.combine(datetime.datetime.strptime(date_str, "%Y-%m-%d"), search_time)
        parsed_date  = raw_datetime.date()
        parsed_time  = raw_datetime.timetz()

        # If the date is not a valid search date, warn the user and roll the day back to the previous valid day
        if not is_searching_day_bool(parsed_date):

            print("WARNING: {:} is not a valid search date. Rolling back to the previous valid day".format(name))

            parsed_date = calc_search_endtime(raw_datetime, search_time, list_post_time).date()

        return parsed_time, parsed_date
    
    except ValueError:

        raise ValueError(f"{name} must be in YYYY-MM-DD format")

def date_error_check(current_time, start_date, end_date, list_post_time):

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
        raise ValueError("Search start date is in the future.")

    # If the search end date is in the future:
    elif ( current_time.date() - end_date ).days < 0:
        raise ValueError("Search end date is in the future.")

    # If the end date is equal to the start date, tell the user to wait
    elif prev_run.days == 0:
        raise ValueError("Search start/end dates are equal."+next_post_string)

    # If the end date is before the start date
    elif prev_run.days < 0:
        raise ValueError(f"Search start date is after the end date. Check for timezone issues.")

    # If the search period doesn't cover any searching days, tell the user to wait
    # Typically one of the previous errors will occur before this one if the entire search period is invalid
    elif deltadays_now_to_search < 7 and valid_search_days == 0:
        raise ValueError("No valid search dates are included."+next_post_string)

    # If there are no issues, let the user know how many days we are searching over
    else:
        print("Days since the previous search: {:}".format(prev_run.days))

    return

def date_setup(args, filename_prevsearch):

    # Define the posting time of the daily list
    list_post_time = datetime.time(6, 0, tzinfo=datetime.timezone.utc) # 06:00 UTC

    # Define the posting time of the daily list
    search_time    = datetime.time(19, 0, tzinfo=datetime.timezone.utc) # 19:00 UTC

    # Obtain the current time, converted to the UTC timezone
    current_time = datetime.datetime.now(datetime.timezone.utc)

    # If start/end dates were passed on the command line, use them. Otherwise, set to None
    start_time, start_date = parse_date(args.start_date, "start-date", search_time, list_post_time) if args.start_date else [None, None]
    end_time,   end_date   = parse_date(args.end_date,   "end-date", search_time, list_post_time)   if args.end_date   else [None, None]

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

            start_time, start_date = parse_date(next(f), filename_prevsearch, search_time, list_post_time)

    # Print some information. Useful to do it before error checks so that all information is visible
    print("Searching from {:}/{:}/{:} 19:00 UTC to {:}/{:}/{:} 19:00 UTC".format(start_date.year, start_date.month, start_date.day, end_date.year, end_date.month, end_date.day))

    date_error_check(current_time, start_date, end_date, list_post_time)

    return start_date, end_date