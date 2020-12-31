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
