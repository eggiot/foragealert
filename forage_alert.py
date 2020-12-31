#!/usr/bin/env python3

import datetime
import argparse
import sqlite3
import os
import re
import sys
from darksky import forecast
from os.path import expanduser
import xmltodict

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
parser.add_argument("-i", "--items",
                    help="XML file containing item definitions")
# version number and Dark Sky attribution
parser.add_argument('-v', '--version', action='version',
                    version="%(prog)s 1.0. " + ds_attribution,
                    help="Show program's version number and exit.")
args = parser.parse_args()

location_request = args.latitude, args.longitude

db_file_path = expanduser("~/bin/my_utilities/databases/foragealert/db.db")
db_new = not os.path.isfile(db_file_path)
sqlite3_detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
db = sqlite3.connect(db_file_path, detect_types=sqlite3_detect_types)


# HELPER FUNCTIONS
def matches_regex(regex, text):
    """ Returns true only if the whole of the text matches the regex
    """
    match = re.match(regex, text)
    return match.span() == (0, len(text))


def errorandquit(error_message):
    """ Print help message plus an error message
    """
    parser.print_help(sys.stderr)
    sys.stderr.write(sys.argv[0] + ": " + error_message + "\n")
    sys.exit(1)


def day_relative_to_absolute(relative):
    """ Converts a relative day to an absolute date string
    """
    today = datetime.datetime.today()
    delta = datetime.timedelta(days=relative)
    return (today - delta).strftime("%Y-%m-%d")


def day_absolute_to_relative(absolute):
    """ Converts an absolute date string to relative day
    """
    today = datetime.datetime.today()
    date = datetime.datetime.strptime(absolute, "%Y-%m-%d")
    return abs((today - date).days)


def is_relative_day(day):
    """Tests if a day is a relative day
    """
    return type(day) == int


def is_absolute_day(day):
    """Tests if a day is an absolute day
    """
    return matches_regex("[0-9]+-[0-9]+-[0-9]+", day)


def format_list_for_db(values):
    """Converts a python list to a sqlite list string
    """
    db_values = ", ".join([f"'{str(value)}'" for value in values])
    return f"({db_values})"


# DATABASE FUNCTIONS
def create_db():
    """ Create the database.
    """
    cursor = db.cursor()
    columns = ["id integer PRIMARY KEY", "hour integer", "day date",
               "temp decimal", "apptemp decimal", "precipint decimal",
               "precipprob decimal", "humidity decimal", "dewpoint decimal",
               "windspeed decimal", "windbearing decimal", "windgust decimal",
               "pressure decimal", "cloudcover decimal", "uvindex decimal",
               "visibility decimal"]
    columns = format_list_for_db(columns)
    cursor.execute("CREATE TABLE weather" + columns)
    cursor.close()


def update_weather():
    """Gets the current weather and adds it to our weather database
    """
    current = []
    current_day = 0
    with forecast(ds_key, *location_request, units="uk2") as location:
        raw = location['hourly']['data'][0]
        current.append(datetime.datetime.now().hour)
        current.append(day_relative_to_absolute(current_day))
        current.append(raw["temperature"])
        current.append(raw["apparentTemperature"])
        current.append(raw["precipIntensity"])
        current.append(raw["precipProbability"] * 100)
        current.append(raw["humidity"] * 100)
        current.append(raw["dewPoint"])
        current.append(raw["windSpeed"])
        current.append(raw["windBearing"])
        current.append(raw["windGust"])
        current.append(raw["pressure"])
        current.append(raw["cloudCover"] * 100)
        current.append(raw["uvIndex"])
        current.append(raw["visibility"])
    current = format_list_for_db(current)

    columns = ["hour", "day", "temp", "apptemp", "precipint", "precipprob",
               "humidity", "dewpoint", "windspeed", "windbearing",
               "windgust", "pressure", "cloudcover", "uvindex", "visibility"]
    columns = format_list_for_db(columns)
    statement = f"INSERT INTO WEATHER {columns} VALUES {current}"
    cursor = db.cursor()
    cursor.execute(statement)
    cursor.close()


def get_weather(days, hours):
    """ Gets the weather on the specified days and hours.

    This is the most general-purpose weather api call. It gets the weather on
    the specified day at the specified hour. This is the foundation on which
    the more complex api calls are built. The specified day is relative to the
    current day, with the current day being 0 and the previous day being 1, etc
    """
    days = format_list_for_db(days)
    hours = format_list_for_db(hours)
    sql = f"SELECT * FROM weather WHERE day in {days} AND HOUR in {hours}"
    cursor = db.cursor()
    cursor.execute(sql)
    data = cursor.fetchall()
    cursor.close()

    weathers = []
    if len(data) > 0:
        for weather in data:
            weather = {"hour": weather[1],
                       "day": day_absolute_to_relative(weather[2]),
                       "temperature": weather[3],
                       "apparenttemperature": weather[4],
                       "precipitationintensity": weather[5],
                       "precipitationprobability": weather[6],
                       "humidity": weather[7],
                       "dewpoint": weather[8],
                       "windspeed": weather[9],
                       "windbearing": weather[10],
                       "windgust": weather[11],
                       "pressure": weather[12],
                       "cloudcover": weather[13],
                       "uvindex": weather[14],
                       "visibility": weather[15]}
            weathers.append(weather)
    return weathers


# MATCHING FUNCTIONS
def strip_match_keys(match_key):
    """Strip "_list", "_min", or "_max" from match_key
    """
    to_strip = ["_list", "_min", "_max"]
    for value in to_strip:
        if value in match_key:
            match_key = match_key.rstrip(value)
    return match_key


def match_rule_value(weather, rule, value):
    """ Checks a value in a weather against the range in a rule

    This function checks to see if the value in weather matches the value or
    falls between the value range in rule.

    Assumes that weather defines absolute values, not ranges, which is always
    true if extracted with get_weather.

    Assumes that rule defines a range using key(s) in the format "value_min"
    and / or "value_max" or defines an absolute value using the key "value",
    or defines a number of absolute values using the key "value_list".
    """
    min_key = value + "_min"
    max_key = value + "_max"
    list_key = value + "_list"

    # does the weather value match the rule?
    if value in rule:
        if weather[value] == rule[value]:
            return True
        else:
            return False
    elif list_key in rule:
        if weather[value] in rule[list_key]:
            return True
        else:
            return False
    elif min_key in rule and max_key in rule:
        if rule[min_key] <= weather[value] <= rule[max_key]:
            return True
        else:
            return False
    elif min_key in rule:
        if weather[value] >= rule[min_key]:
            return True
        else:
            return False
    elif max_key in rule:
        if weather[value] <= rule[max_key]:
            return True
        else:
            return False
    # doesn't matter, so returns True
    else:
        return True


def match_rule(weather, rule):
    """ This function matches weather against a rule.

    If the fields specified in weather match those same fields in rule, it
    returns True, otherwise False
    """
    keys = set([strip_match_keys(key) for key in weather])
    return all(match_rule_value(weather, rule, key) for key in keys)


def build_range_list(rule_dict, key, min_value, range_value, max_value,
                     default_value):
    """Defines a default range for an incompletely defined range in a rule.

    This function allows for the definition of a default range for an
    incompletely defined range in a rule dictionary. It will check
    rule_dict for key + suffixes. it will return a list containing the values
    of that default range within the constraints defined within rule_dict.

    min_value:  the minimum possible value if key_min is not defined
    range_value: the number of values above key_min that are allowed when
        key_max is not defined.
    max_value: the range can never go above this when key_max is not defined
    default_valueL the value if nothing is defined
    """
    list_key = key + "_list"
    min_key = key + "_min"
    max_key = key + "_max"

    # the range list is just the provided list
    if list_key in rule_dict:
        return rule_dict[list_key]
    elif min_key in rule_dict:
        # if a full range is defined using _min and _max, just return the range
        if max_key in rule_dict:
            return list(range(rule_dict[min_key], rule_dict[max_key] + 1))
        # if lower bounded, do the default range on top of lower bound
        else:
            max_range = rule_dict[min_key] + range_value
            if max_range > max_value:
                max_range = max_value
            return list(range(rule_dict[min_key], max_range))
    # if upper bounded, get all values from min value to upper bound
    elif max_key in rule_dict:
        if rule_dict[max_key] == min_value:
            return [min_value]
        else:
            return list(range(min_value, rule_dict[max_key] + 1))
    # single value defined
    elif key in rule_dict:
        return [rule_dict[key]]
    # nothing defined so return default value
    else:
        if type(default_value) == list:
            return default_value
        else:
            return [default_value]


# Rule class
class Rule():
    def __init__(self, rule_dict):
        self.rule_dict = rule_dict
        # list keys should be a string of comma separated integer values
        list_keys = [key for key in self.rule_dict if "_list" in key]
        for key in list_keys:
            value = self.rule_dict[key]
            self.rule_dict[key] = [int(v) for v in value.split(",")]
        self.hours = build_range_list(self.rule, "hour", 0, 23, 23, [])
        self.days = build_range_list(self.rule, "day", 0, 100, 7, [])
        self.pick_hours = build_range_list(self.rule, "pick", 0, 1, 23, [])
        self.months = build_range_list(self.rule, "month", 0, 12, 12, [])

        if self.pick_hours and (self.hours or self.days or self.months):
            message = "Cannot define pick hours alongside hours, days, or\
                       months in the same rule."
            raise Exception(message)
        elif self.months and (self.hours or self.days):
            message = "Cannot define months alongside hours or days in the\
                       same rule."
            raise Exception(message)
        # set amount
        if "amount" in self.rule.keys():
            self.amount = self.rule["amount"]
            self.rule.pop("amount")
        else:
            self.amount = 100

    def test(self):
        """
        If a picking rule, returns True if the current time is within the
        picking hours.

        If a weather rule, returns True if the weather at the hours and days
        specified in the rule has matched the weather specified in the
        rule over the specified percentage of instances
        """
        if self.pick_hours:
            current_hour = datetime.datetime.now().hour
            pick_now = current_hour in self.pick_hours
            pick_today = any(hour > current_hour for hour in self.pick_hours)
            if pick_now:
                return True
            elif pick_today:
                return True
            else:
                return False
        elif self.months:
            current_month = datetime.datetime.now().month
            if current_month in self.months:
                return True
            else:
                return False
        else:
            # get the weather for the hours and days specified
            weathers = get_weather(self.days, self.hours)
            weathers = all(match_rule(w, self.rule) for w in weathers)

            # calculate percentage of True values
            if self.amount < 100:
                num_matches = len([current for current in weathers if current])
                num_tests = len(weathers)
                percentage = num_matches / num_tests * 100
                if percentage >= self.amount:
                    return True
                else:
                    return False
            # are there any non-matching instances?
            else:
                if False in weathers:
                    return False
                else:
                    return True


# ForagingItem class
class ForagingItem():
    def __init__(self, name):
        self.name = name
        self.rules = []
        self.status = True

    def add_rule(self, rule):
        self.rules.append(rule)

    def check(self):
        for rule in self.rules:
            if not rule.test():
                self.status = False
                return False
        self.status = True
        return True

    def alert(self):
        if self.check():
            print("You should forage " + self.name + " right now!")


def xml_to_foraging_items(xml):
    foraging_items = []
    # save xml data as ordered dict. item name as key, dict of rules as value
    raw_items = xmltodict.parse(xml)

    # convert raw dicts into foraging item with attached rules and add to
    # foraging_items list
    for raw_item in raw_items:
        current_item = ForagingItem(raw_item)
        current_item_rules = raw_items[raw_item]
        for rule in current_item_rules.values():
            current_item.add_rule(Rule(rule))
        foraging_items.append(current_item)
    return foraging_items


# DOING THINGS

if db_new:
    create_db()

# check mode and act accordingly
if args.mode == "update":
    update_weather()
elif args.mode == "alert":
    with open(args.items, 'r') as file:
        data = file.read()

    foraging_items = xml_to_foraging_items(data)

    for foraging_item in foraging_items:
        foraging_item.check()
