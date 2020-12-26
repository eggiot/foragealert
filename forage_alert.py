#!/usr/bin/env python3

import datetime
import argparse
import sqlite3
import os
import re
import sys
from darksky import forecast
from os.path import expanduser

# get Dark Sky API key
ds_attribution = "Powered by Dark Sky: https://darksky.net/poweredby/."
with open(expanduser("~/bin/my_utilities/config/darksky-key")) as f:
    ds_key = f.readline().strip()

parser = argparse.ArgumentParser()
parser.add_argument("latitude", help="Latitude",
                    type=float)
parser.add_argument("longitude", help="Longitude",
                    type=float)
parser.add_argument("-m", "--mode",
                    help="One of 'alert' or 'update'")
# version number and Dark Sky attribution
parser.add_argument('-v', '--version', action='version',
                    version="%(prog)s 1.0. " + ds_attribution,
                    help="Show program's version number and exit.")
args = parser.parse_args()

location_request = args.latitude, args.longitude

# global variables
CURRENT_DAY = 0
CURRENT_HOUR = datetime.datetime.now().hour
# hour lists
ALL_DAY = list(range(24))
ALL_NIGHT = list(range(7))
ALL_EVENING = list(range(19, 23))
# day lists
PAST_WEEK = list(range(7))
PAST_2_WEEKS = list(range(14))
PAST_MONTH = list(range(31))
PAST_YEAR = list(range(365))

JAN, FEB, MAR, APR, MAY, JUN = 1, 2, 3, 4, 5, 6
JUL, AUG, SEP, OCT, NOV, DEC = 7, 8, 9, 10, 11, 12

SUMMER = list(range(JUN, AUG))
SPRING = list(range(MAR, APR))
AUTUMN = list(range(SEP, NOV))
WINTER = [DEC, JAN, FEB]

RELATIVE_DAY = 0
ABSOLUTE_DAY = 1
NON_DAY = 2

db_file_path = expanduser("~/bin/my_utilities/databases/foragealert/db.db")
db_new = not os.path.isfile(db_file_path)
sqlite3_detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
db = sqlite3.connect(db_file_path, detect_types=sqlite3_detect_types)


# HELPER FUNCTIONS
def matches_regex(regex, text):
    """
    Returns true only if the whole of the text matches the regex
    """
    match = re.match(regex, text)
    return match.span() == (0, len(text))


def errorandquit(error_message):
    """
    Print help message plus an error message"""
    parser.print_help(sys.stderr)
    sys.stderr.write(sys.argv[0] + ": " + error_message + "\n")
    sys.exit(1)


def day_relative_to_absolute(relative):
    """
    Converts a relative day (0 being today, 1 being yesterday, etc) to an
    absolute day(in the format YYYY-MM-DD)
    """
    today = datetime.datetime.today()
    delta = datetime.timedelta(days=relative)
    return (today - delta).strftime("%Y-%m-%d")


def day_absolute_to_relative(absolute):
    """
    Converts an absolute date (format YYYY-MM-DD into a relative day)
    """
    today = datetime.datetime.today()
    date = datetime.datetime.strptime(absolute, "%Y-%m-%d")
    return abs((today - date).days)


def test_rule_validity(rule):
    try:
        rule["hours"]
        rule["days"]
        return True
    except KeyError:
        return False


def test_day_format(day):
    """
    Tests input to see if it's a relative day, an absolute day or neither
    """
    try:
        int(day)
        return RELATIVE_DAY
    except ValueError:
        pass
    regex = "[0-9]+-[0-9]+-[0-9]+"
    try:
        if matches_regex(regex, day):
            return ABSOLUTE_DAY
        else:
            return NON_DAY
    except AttributeError:
        return NON_DAY


def day_range(days):
    return list(range(days))


# DATABASE FUNCTIONS
def create_db():
    """
    Create the database. To be used if the database has not yet been created
    """
    cursor = db.cursor()

    cursor.execute("CREATE TABLE weather(id integer PRIMARY KEY, hour integer,\
                    day date, temperature decimal, precip decimal,\
                    humidity decimal, windspeed decimal, windbearing decimal,\
                    windgust decimal, pressure decimal, cloudcover decimal,\
                    visibility decimal)")

    cursor.close()


def update_weather():
    """
    This function gets the current weather and adds it to our weather database
    """
    current = []
    with forecast(ds_key, *location_request, units="uk2") as location:
        raw = location['hourly']['data'][0]
        current.append(CURRENT_HOUR)
        current.append(day_relative_to_absolute(CURRENT_DAY))
        current.append(raw["temperature"])
        current.append(raw["precipProbability"] * 100)
        current.append(raw["humidity"] * 100)
        current.append(raw["windSpeed"])
        current.append(raw["windBearing"])
        current.append(raw["windGust"])
        current.append(raw["pressure"])
        current.append(raw["cloudCover"] * 100)
        current.append(raw["visibility"])

    current = ["'" + str(value) + "'" for value in current]
    current = ", ".join(current)

    columns = ["hour", "day", "temperature", "precip", "humidity", "windspeed",
               "windbearing", "windgust", "pressure", "cloudcover",
               "visibility"]

    columns = ["'" + value + "'" for value in columns]
    columns = ", ".join(columns)

    statement = ["INSERT INTO weather (", columns, ") VALUES(", current, ")"]
    statement = "".join(statement)

    cursor = db.cursor()
    cursor.execute(statement)
    cursor.close()


def get_weather(day, hour):
    """
    This is the most general-purpose weather api call. It gets the weather on
    the specified day at the specified hour. This is the foundation on which
    the more complex api calls are built. The specified day is relative to the
    current day, with the current day being 0 and the previous day being 1, etc
    """

    if test_day_format(day) == RELATIVE_DAY:
        day = day_relative_to_absolute(day)
    statement = ["SELECT * FROM weather WHERE day == '", str(day),
                 "' AND hour == '", str(hour), "'"]
    statement = "".join(statement)
    cursor = db.cursor()
    cursor.execute(statement)
    data = cursor.fetchall()
    cursor.close()

    try:
        data = data[0]
        weather = {"hour": hour, "day": day_absolute_to_relative(day),
                   "temp": data[3],
                   "precipitation": data[4], "humidity": data[5],
                   "windspeed": data[6], "windbearing": data[7],
                   "windgust": data[8], "pressure": data[9],
                   "cloudcover": data[10], "visibility": data[11]}
        return weather
    except IndexError:
        return None


# MATCHING FUNCTIONS
def strip_match_keys(match_key):
    """
    Strip "_list", "_min", or "_max" from match_key
    """
    to_strip = ["_list", "_min", "_max"]
    for value in to_strip:
        if value in match_key:
            match_key = match_key.rstrip(value)
    return match_key


def match_rule_value(weather, rule, value):
    """
    This function checks to see if the value in weather matches the value or
    falls between the value range in rule.

    Assumes that weather defines absolute values, not ranges, which is always
    true if extracted with get_weather.

    Assumes that rule defines a range using key(s) in the format "value_min"
    and / or "value_max" or defines an absolute value using the key "value",
    or defines a number of absolute values using the key "value_list".
    """
    UPPER_BOUNDED = 0
    LOWER_BOUNDED = 1
    BOTH_BOUNDED = 2
    SINGLE_VALUE = 3
    LIST_VALUE = 4

    min_key = value + "_min"
    max_key = value + "_max"
    list_key = value + "_list"

    # how is the value defined within the rule?
    if value in rule:
        range_type = SINGLE_VALUE
    elif list_key in rule:
        range_type = LIST_VALUE
    elif max_key in rule:
        if min_key in rule:
            range_type = BOTH_BOUNDED
        else:
            range_type = UPPER_BOUNDED
    elif min_key in rule:
        range_type = LOWER_BOUNDED
        # the value doesn't matter so we match
        return True
    else:
        # doesn't matter so return True
        return True

    # does the weather value match the rule?
    if range_type == SINGLE_VALUE:
        if weather[value] == rule[value]:
            return True
        else:
            return False
    elif range_type == LIST_VALUE:
        if weather[value] in rule[list_key]:
            return True
        else:
            return False
    elif range_type == LOWER_BOUNDED:
        if weather[value] >= rule[min_key]:
            return True
        else:
            return False
    elif range_type == UPPER_BOUNDED:
        if weather[value] <= rule[max_key]:
            return True
        else:
            return False
    elif range_type == BOTH_BOUNDED:
        if weather[value] <= rule[max_key] and weather[value] >= rule[min_key]:
            return True
        else:
            return False


def match_rule(weather, rule):
    """
    This function matches weather against the rule. If the fields
    specified in weather match those same fields in rule, it
    returns True, otherwise False
    """
    for key in weather:
        try:
            key = strip_match_keys(key)
            if not match_rule_value(weather, rule, key):
                return False
        except KeyError:
            return False
    return True


# ForagingItem class

class ForagingItem():
    def __init__(self):
        self.rules = []
        self.status = True

    def check(self):
        for rule in self.rules:
            if not self.__test__rule__(rule):
                self.status = False
                return False
        self.status = True
        return True

    def __test_rule__(rule):
        """
        This function returns True if the weather at the hours and days
        specified in the rule has matched the weather specified in the
        rule over the specified percentage of instances
        """
        weathers = []

        if not test_rule_validity(rule):
            errorandquit("A rule was not valid")

        # build a list of all required days
        if "day_list" in rule:
            days = rule["day_list"]
        elif "day_min" in rule:
            if "day_max" in rule:
                days = range(rule["day_min"], rule["day_max"])
            else:
                errorandquit("Day range not specified")
        elif "day" in rule:
            days = [rule["day"]]
        else:
            errorandquit("Day range not specified")

        # build a list of all required hours
        if "hour_list" in rule:
            hours = rule["hour_list"]
        elif "hour_min" in rule:
            if "hour_max" in rule:
                hours = range(rule["hour_min"], rule["hour_max"])
            else:
                errorandquit("Hour range not specified")
        elif "hour" in rule:
            hours = [rule["hour"]]
        else:
            errorandquit("Hour range not specified")

        # get the weather for the hours and days specified
        for day in days:
            for hour in hours:
                current_weather = get_weather(day, hour)
                if current_weather:
                    weathers.append(current_weather)

        # how often should the rule be the case (default=100)
        if "amount" in rule:
            amount = rule["amount"]
        else:
            amount = 100

        # test and convert to list of True and False values
        weathers = [match_rule(weather, rule) for weather in weathers]

        # calculate percentage of True values
        if amount < 100:
            num_matches = len([current for current in weathers if current])
            num_tests = len(weathers)
            percentage = num_matches / num_tests * 100
            if percentage >= amount:
                return True
            else:
                return False
        # are there any non-matching instances?
        else:
            if False in weathers:
                return False
            else:
                return True


# DOING THINGS

if db_new:
    create_db()

# check mode and act accordingly
if args.mode == "update":
    update_weather()
elif args.mode == "alert":
    pass
