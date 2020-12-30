# foragealert

Many plants and fungi have ideal foraging conditions, where the weather has to be just right. This software keeps track of hourly weather data and alerts when the rules for a particular foraging item have been satisfied.

## Defining rules

Rules are defined in an XML file. Valid variables are:
- _"day"_: relative day where 0 is today, 1 is yesterday, etc.
- _"hour"_: the hour within the day
- _"temperature"_: the temperature at that time
- _"apparenttemperature"_: the apparent temperature at that time
- _"precipitationintensity"_: precipitation intensity at that time
- _"precipitationprobability"_: precipitation probability at that time
- _"humidity"_: humidity at that time
- _"dewpoint"_: dewpoint at that time
- _"windspeed"_: wind speed at that time
- _"windbearing"_: wind bearing at that time
- _"windgust"_: wind gust at that time
- _"pressure"_: pressure at that time
- _"cloudcover"_: cloud cover at that time
- _"uvindex"_: UV index at that time
- _"visibility"_: visibility at that time
- _"pick"_: best or necessary pick times. Must be defined separately to weather or month rules.
- _"month"_: months where it is in season. Must be defined separately to weather or pick time rules.

Ranges can be specified by adding the suffixies "_min", "_max", or "_list" to these variable names

## Running

Run as hourly cronjob in update mode to update the weather. Run in alert mode to get an alert.
