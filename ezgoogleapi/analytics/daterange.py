import warnings
from datetime import datetime, timedelta, time
from typing import Union

'''
Module to create dynamic date ranges for Google Analytys queries. 
'''

def c(dates):
    return [dates[0].replace(hour=0, minute=0, second=0, microsecond=0),
            dates[1].replace(hour=0, minute=0, second=0, microsecond=0)]


TODAY = datetime.now()
YESTERDAY = c([TODAY - timedelta(days=1), TODAY - timedelta(days=1)])
LAST_WEEK = c([TODAY - timedelta(days=TODAY.weekday(), weeks=1),
             TODAY - timedelta(days=TODAY.weekday(), weeks=1) + timedelta(days=6)])
LAST_7_DAYS = c([YESTERDAY[0] - timedelta(days=7), YESTERDAY[0]])
THIS_MONTH = c([TODAY.replace(day=1), YESTERDAY[0]])
LAST_MONTH = c([(TODAY.replace(day=1) - timedelta(days=1)).replace(day=1),
              TODAY.replace(day=1) - timedelta(days=1)])
LAST_90_DAYS = c([TODAY - timedelta(days=91), YESTERDAY[0]])
LAST_YEAR = c([datetime(TODAY.year - 1, 1, 1), datetime(TODAY.year - 1, 12, 31)])
THIS_YEAR = c([datetime(TODAY.year, 1, 1), YESTERDAY[0]])


def quarter(q_num: int, year: int) -> list:
    '''
    Get date range for a specific quarter of a year, but cannot be in the future.
    :param q_num: Quarter number as an int between 1 and 4
    :param year: Year as an int
    :return: List of length 2 containing the start and end date of the quarter as a datetime object.
    '''
    q_lookup = {
        1: [datetime(TODAY.year, 1, 1), datetime(TODAY.year, 3, 31)],
        2: [datetime(TODAY.year, 4, 1), datetime(TODAY.year, 6, 30)],
        3: [datetime(TODAY.year, 7, 1), datetime(TODAY.year, 9, 30)],
        4: [datetime(TODAY.year, 10, 1), datetime(TODAY.year, 12, 31)]
    }
    if q_num == 0:
        diffs = {num: TODAY - date_[0] for num, date_ in q_lookup.items() if
                 TODAY - date_[0] > timedelta(days=0)}
        current_quarter = list(diffs.values()).index(min(diffs.values())) + 1
        return [q_lookup[current_quarter][0], YESTERDAY[0]]

    if q_num == -1:
        diffs = {num: TODAY - date_[0] for num, date_ in q_lookup.items() if
                 TODAY - date_[0] > timedelta(days=0)}
        current_quarter = list(diffs.values()).index(min(diffs.values())) + 1
        year = TODAY.year
        if current_quarter == 1:
            q_num = 4
            year -= 1
        else:
            q_num = current_quarter - 1

    q = q_lookup[q_num]
    if year != TODAY.year:
        q = [d.replace(year=year) for d in q]

    if q[0] > TODAY and q[1] > TODAY:
        raise UserWarning(
            f'Dates for Q{q_num} of {year} are in the future and will not yield any results in Google Analytics.')

    elif q[1] > TODAY:
        warnings.warn(f'Q{q_num} of {year} is the current quarter. Date range will end yesterday.')
        q[1] = YESTERDAY[0]

    return q


LAST_QUARTER = c(quarter(-1, TODAY.year))
CURRENT_QUARTER = c(quarter(0, TODAY.year))


def weeks(week: Union[int, tuple, list], year: int, first_day: str = 'mon') -> list:
    '''
    Get date range for specific ISO weeks of a year.

    :param week: Week number as an int or a week range as a tuple or list. Ex. for weeks 12 to 21: (12, 21) or [12, 21].
    :param year: Full year as an int.
    :param first_day: [optional] Specify the first day of the week: 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'.
        Default: 'mon'.
    :return: List of length 2 containing the start and end date of the week range as a datetime object.
    '''

    if type(week) == int:
        week = (week, week)

    first_day_of_year = datetime(year, 1, 1)
    first_day_of_week = first_day_of_year + timedelta(weeks=week[0]) - timedelta(days=first_day_of_year.weekday())

    days_calc = {'tue': 1, 'wed': 2, 'thu': 3, 'fri': -3, 'sat': -2, 'sun': -1}

    if first_day != 'mon':
        first_day_of_week = first_day_of_week + timedelta(days=days_calc[first_day])

    week_diff = week[1] - week[0]
    last_day_of_week = first_day_of_week + timedelta(weeks=week_diff, days=6)

    date_range = [first_day_of_week, last_day_of_week]

    if date_range[0] > TODAY and date_range[1] > TODAY:
        raise UserWarning(
            f'Week given date range is in the future and will not yield any '
            f'results in Google Analytics.')
    elif date_range[1] > TODAY:
        warnings.warn(f'Week {week[1]} is (partially) in the future. The end date will be set to yesterday.',
                      UserWarning)
        date_range[1] = YESTERDAY[0]

    return c(date_range)


def combine_ranges(*ranges):
    new_range = list(set(item for sublist in ranges for item in sublist))
    start = min(new_range)
    end = max(new_range)
    return c([start, end])




