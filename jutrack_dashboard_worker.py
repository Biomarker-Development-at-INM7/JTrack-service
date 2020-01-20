import os

import hashlib
import json
import argparse
import glob
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
    if not os.path.isdir(studys_folder + "/" + study_id):
        raise JutrackValidationError("Invalid study detected: " + str(study_id))


def is_valid_user(study_id, username):
    if not os.path.isfile(users_folder + "/" + study_id + "_" + username + '.json'):
        raise JutrackValidationError("Invalid user for study " + study_id + " detected: " + str(username))


# -------------------------- FUNCTIONALITY ------------------------------


def create_csv_table(study_id):
    study_folder = storage_folder + '/study_id'
    first_study_path = get_first_file_in_folder(study_folder)
    study_dict = get_json_content(first_study_path)


# check json in folders recursively
def get_first_file_in_folder(folder_to_check):
    file_obj = ""
    for name in glob.glob(folder_to_check + '/**/*.*', recursive=True):
        file_obj = name
    return file_obj


def get_json_content(file_path):
    content = None

    with open(file_path) as json_file:
        try:
            content = json.load(json_file)
        except JSONDecodeError as e:
            print("ERROR: The file " + file_path + " is not a valid json file. \tERROR-Message: " + e.msg)
        json_file.close()

    return content
