"""Tool wrappers for current local time and date information."""

from brain.time_utils import get_date, get_day, get_time


def validate_empty(arguments):
    if not isinstance(arguments, dict) or arguments:
        raise ValueError("This tool does not accept arguments.")


def current_time(arguments):
    return {"time": get_time()}


def current_date(arguments):
    return {"date": get_date()}


def current_day(arguments):
    return {"day": get_day()}
