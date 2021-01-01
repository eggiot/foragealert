import sqlite3
import os
from os.path import expanduser
from darksky import forecast
import datetime


def get_db(file_path):
    """Returns a sqlite cursor, creating database if it doesn't exist.
    """
    db_new = not os.path.isfile(file_path)
    sqlite3_detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    db = sqlite3.connect(file_path, detect_types=sqlite3_detect_types)
    if db_new:
        create_db(db)
    return db


def format_list_for_db(values):
    """Converts a python list to a sqlite list string
    """
    db_values = ", ".join([str(value) for value in values])
    return f"({db_values})"


# DATABASE FUNCTIONS
def create_db(db):
    """ Create the database.
    """
    cursor = db.cursor()
    columns = ["id integer PRIMARY KEY", "hour integer", "day date",
               "temp decimal", "apptemp decimal", "precipint decimal",
               "precipprob decimal", "humidity decimal", "dewpoint decimal",
               "windspeed decimal", "windbearing decimal", "windgust decimal",
               "pressure decimal", "cloudcover decimal", "uvindex decimal",
               "visibility decimal"]
    columns = ", ".join(columns)
    cursor.execute(f"CREATE TABLE weather({columns})")
    cursor.close()


def update_weather(location_request, db):
    """Gets the current weather and adds it to our weather database
    """
    with open(expanduser("~/bin/my_utilities/config/darksky-key")) as f:
      ds_key = f.readline().strip()
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
    print(statement)
    cursor = db.cursor()
    cursor.execute(statement)
    cursor.close()


def get_weather(days, hours, db):
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
