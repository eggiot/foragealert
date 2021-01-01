#!/usr/bin/env python3

import datetime
import argparse
import re
import sys
from os.path import expanduser
import xmltodict
from matching import match_rule
from matching import build_range_list
import db

# get Dark Sky API key
ds_attribution = "Powered by Dark Sky: https://darksky.net/poweredby/."

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

db_location = "~/bin/my_utilities/databases/foragealert/db.db"
db_object = db.get_db(expanduser(db_location))

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


# Rule class
class Rule():
    def __init__(self, rule_dict):
        self.rule_dict = {k: int(v) for (k, v) in rule_dict.items()}
        # list keys should be a string of comma separated integer values
        list_keys = [key for key in self.rule_dict if "_list" in key]
        for key in list_keys:
            value = self.rule_dict[key]
            self.rule_dict[key] = [int(v) for v in value.split(",")]
        self.hours = build_range_list(self.rule_dict, "hour", 0, 23, 23, [])
        self.days = build_range_list(self.rule_dict, "day", 0, 100, 7, [])
        self.pick_hours = build_range_list(self.rule_dict, "pick", 0, 1, 23,
                                           [])
        self.months = build_range_list(self.rule_dict, "month", 0, 12, 12, [])

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
            return pick_now or pick_today
        elif self.months:
            current_month = datetime.datetime.now().month
            return current_month in self.months
        else:
            # get the weather for the hours and days specified
            weathers = db.get_weather(self.days, self.hours, db_object)
            weathers = all(match_rule(w, self.rule) for w in weathers)

            # calculate percentage of True values
            if self.amount < 100:
                num_matches = len([current for current in weathers if current])
                num_tests = len(weathers)
                percentage = num_matches / num_tests * 100
                return percentage >= self.amount
            # are there any non-matching instances?
            else:
                return False not in weathers


# ForagingItem class
class ForagingItem():
    def __init__(self, name, rule_dicts=None):
        self.name = name
        self.rules = []
        self.status = True

        # list of rule_dicts
        if rule_dicts:
            self.rules = [Rule(rule_dict) for rule_dict in rule_dicts]

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
            print(f"You should forage {self.name} right now!")


def xml_to_foraging_items(xml):
    foraging_items = []
    # save xml data as ordered dict. item name as key, dict of rules as value
    raw_items = xmltodict.parse(xml)["items"]

    # convert raw dicts into foraging item with attached rules
    for item_name, item_rules in raw_items.items():
        # key is foraging object name, value are rule_dicts
        current_item = ForagingItem(item_name, rule_dicts=item_rules.values())
        foraging_items.append(current_item)
    return foraging_items


# check mode and act accordingly
if args.mode == "update":
    db.update_weather(location_request, db_object)
elif args.mode == "alert":
    with open(args.items, 'r') as file:
        data = file.read()

    foraging_items = xml_to_foraging_items(data)

    for foraging_item in foraging_items:
        foraging_item.check()
