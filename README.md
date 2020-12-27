# foragealert

Many plants and fungi have ideal foraging conditions, where the weather has to be just right. This software keeps track of hourly weather data and alerts when the rules for a particular foraging item have been satisfied.

## Defining rules

Rules are defined in an XML file. Valid variables are "day", "hour", "temp", "precip", "humidity", "windspeed", "windbearing", "windgust", "pressure", "cloudcover", and "visibility". Ranges can be specified by adding the suffixies "_min", "_max", or "_list" to these variable names

## Running

Run as hourly cronjob in update mode to update the weather. Run in alert mode to get an alert.
