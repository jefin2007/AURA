from datetime import datetime


def get_time():
    return datetime.now().strftime("%I:%M %p")


def get_date():
    return datetime.now().strftime("%d %B %Y")


def get_day():
    return datetime.now().strftime("%A")