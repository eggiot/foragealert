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
