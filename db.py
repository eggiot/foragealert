import sqlite3

db_file_path = expanduser("~/bin/my_utilities/databases/foragealert/db.db")
db_new = not os.path.isfile(db_file_path)
sqlite3_detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
db = sqlite3.connect(db_file_path, detect_types=sqlite3_detect_types)
if db_new:
    db.create_db()


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
