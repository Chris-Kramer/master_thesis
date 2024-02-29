###########
# Imports #
###########
import sqlite3
from contextlib import closing
import modules.data_retrieval.retrieve_sets_params as get_sets_params

#############
# Functions #
#############
def convert_id_to_date(date_id: int, con: sqlite3.Connection) -> str:
    """
    Takes an integer, which represents the ID of a date and returns a string representing that date. 
    """
    with closing(con.cursor()) as cur:
        return cur.execute(f"SELECT date FROM dates WHERE ID == {date_id}").fetchone()[0]


def convert_date_to_id(date: str, con: sqlite3.Connection) -> int:
    """
    Takes a string, which represents a date and returns an integer, which represents the ID of that date
    """
    with closing(con.cursor()) as cur:
        return cur.execute(f"SELECT ID FROM dates WHERE date == '{date}'").fetchone()[0]


def get_date_time_slots(date_id: int, con: sqlite3.Connection) -> list[int]:
    """
    Takes a date ID and returns a list of integers representing the IDs of the time-slots associated with that date.
    """
    with closing(con.cursor()) as cur:
        time_slots = cur.execute(f"SELECT ID from time_slots WHERE date_id == {date_id}").fetchall()
    return [time_slot[0] for time_slot in time_slots]


def get_day_type(date_id: int, con: sqlite3.Connection) -> int:
    """
    Takes a date ID and returns a string representing the day type.
    """
    with closing(con.cursor()) as cur:
        return cur.execute(f"SELECT day_type FROM dates WHERE ID == {date_id}").fetchone()[0] 


def get_day_types_in_range(start_day: int, end_day: int, con:sqlite3.Connection) -> list[int]:
    """
    Returns a list of day types between a start date and an end date.
    """
    day_types = []
    for day in range(start_day, end_day):
        day_types.append(get_day_type(day, con))
    return day_types


def no_holidays(start_day: int, end_day: int, con: sqlite3.Connection) -> bool:
    """
    Returns a boolean indicating if there is any holidays between a start date and an end date.
    """
    return "holiday" not in get_day_types_in_range(start_day, end_day, con)


def find_day_range(earliest_day: int, latest_day: int, n_days: int, con: sqlite3.Connection):
    """
    Searches for a range of n_days between a start date and an end day, where there is no holidays.
    """
    for day in range(earliest_day, latest_day, n_days):
        if no_holidays(day, day + n_days, con):
            return (day, day + n_days)
    return None


def create_auditor_holidays(first_day: int, last_day: int, con: sqlite3.Connection, n_days = 42) -> dict[int, list[int]]:
    """
    Returns a dictionary containing lists of auditor holidays
    """
    auditor_holidays = {}
    for auditor in get_sets_params.get_employees(con):
        if 1 <= auditor <= 5:
            auditor_holidays[auditor] = find_day_range(first_day + 90, last_day, n_days, con)
        elif 6 <= auditor <= 10:
            auditor_holidays[auditor] = find_day_range(first_day + 180, last_day, n_days, con)
        else:
            auditor_holidays[auditor] = find_day_range(first_day + 250, last_day, n_days, con)
    return auditor_holidays