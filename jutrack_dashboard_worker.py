import os

import hashlib
import json
import datetime
import sys
from json import JSONDecodeError

# -------------------- CONFIGRATION -----------------------
storage_folder = '/mnt/jutrack_data'
studys_folder = storage_folder
users_folder = storage_folder + '/users'
devices_folder = ""


# -------------------- VALIDATION -------------------------


class JutrackError(Exception):
    """Base class for exceptions in this module."""
    pass


class JutrackValidationError(JutrackError):
    """Exception raised for unsuccessful validation of the json content.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


# compare MD5 values
def is_md5_matching(md5, calc_md5):
    if calc_md5 == md5:
        return True
    else:
        return False


# compare data content with what is valid
def is_valid_data(body, action, verbose=0):
    """Perform all possible tests and return a flag"""
    data = is_valid_json(body, verbose)

    if len(data) == 0:
        raise JutrackValidationError("ERROR: The uploaded content was empty.")

    if 'status' in data:
        return data

    # study_id = data[0]['studyId']
    # user_id = data[0]['username']

    # is_valid_study(study_id)
    # is_valid_user(study_id, username)

    if action == "write_data":
        sensorname = data[0]['sensorname']
        is_valid_sensor(sensorname)

    return data


def is_valid_json(body, verbose):
    try:
        data = json.load(body)
        if verbose:
            print("NOTICE: The uploaded content is valid json.")
    except JSONDecodeError as e:
        raise JutrackValidationError("ERROR: The uploaded content is not valid json. \tERROR-Message: " + e.msg)

    return data


def is_valid_study(study_id):
    if not os.path.isdir(data_folder + "/" + study_id):
        raise JutrackValidationError("Invalid study detected: " + str(study_id))


def is_valid_user(study_id, username):
    if not os.path.isfile(user_folder + "/" + study_id + "_" + username + '.json'):
        raise JutrackValidationError("Invalid user for study " + study_id + " detected: " + str(username))
