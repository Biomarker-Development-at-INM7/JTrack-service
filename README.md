# JTrack Service

Is a collection of python scripts that serve as Endpoints to the jtrack app or are executed in cron jobs on the server side.

## Overview
JTrack services contains the following scripts:

*   [jtrackService.wsgi](#jtrackService.wsgi) : The code for the API to handle App requests
*   [jtrack_fetch_resources.wsgi](#jtrack_fetch_resources.wsgi) : The code to fetch image resources for `EMA App`
*   [jtrack_csv_cronjob.py](#jtrack_csv_cronjob.py) : Examines the written data and creates tables for the `dashboard`
*   [jtrack_sanity_check.py](#jtrack_sanity_check.py) : Checks uploaded `JSON` files for errors

## jtrackService.wsgi
This script is called on a specific endpoint to mainly write and update files by providing an `ACTION`-Header in the request.
The three possible actions are:
*   [write_data](#write_data)
*   [add_user](#add_user)
*   [write_data](#write_data)

To ensure security, a checksumming-layer is included as well as multiple validation layers for `study`, `user`, `device` and `sensor`.

### write_data
Expects a `POST`-Request with `JSON` data to store data based on the parameters `studyID`, `userID`, `deviceID` and `sensorname`. To ensure there are no duplicate names or overwritten files, a `timestamp` is included in the file name.

To additionally ensure that no data is mistakenly ignored, if `JSON` parameters are empty or a study already archived, files are also written to a `junk` folder.
### add_user
Expects a `POST`-Request with `JSON` data for a `user` to register a user to an existing study and store a `JSON` file for the `user`. It also sets the user `status ` to active.
`add_user` can be used for multiple apps that are related to JTrack such as the `EMA App`.
### update_user
Expects a `POST`-Request with `JSON` data to update `user` data such as the `status` for an app e.g. if a user leaves a study or withdraws from an App.

## jtrack_fetch_resources.wsgi
This script is called on a specific endpoint to mainly get resources from the server by providing an `ACTION`-Header in the `request`.
Until now only `download`is a valid action that results in a `response` with an archive of images for the `EMA App`
## jtrack_csv_cronjob.py
This script is called on a 5-second interval to examine the written files of each active `study` on a per-user basis. 
For each `study` this results in a `.csv-file` with the following columns:
* app
* subject_name
* device_id
* date_registered
* date_left_study
* time_in_study
* status_code

Additionally for each sensor there are two columns `n_batches` und `last_time_received`.

## jtrack_sanity_check.py
This script runs though all JSON files and checks whether each file fits the JSON specification. Otherwise files with errors are printed to an output file.
