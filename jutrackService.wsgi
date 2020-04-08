import os

import hashlib
import json
import datetime
import sys

# ---------------------------------------CONFIGURATION

# server version
__version__ = 0

valid_data = [
    'accelerometer',
    'activity',
    'application_usage',
    'barometer',
    'gravity_sensor',
    'gyroscope',
    'location',
    'magnetic_sensor',
    'rotation_vector',
    'linear_acceleration'
]

storage_folder = '/mnt/jutrack_data'
studys_folder = storage_folder + '/studys'
user_folder = storage_folder + '/users'


# ----------------------------------------VALIDATION-------------------------------------------------


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
        data = json.loads(body)
        if verbose:
            print("NOTICE: The uploaded content is valid json.")
    except Error as e:
        raise JutrackValidationError("ERROR: The uploaded content is not valid json. \tERROR-Message: " + e.msg)

    return data


def is_valid_study(study_id):
    if not os.path.isdir(studys_folder + "/" + study_id):
        raise JutrackValidationError("Invalid study detected: " + str(study_id))


def is_valid_user(study_id, username):
    if not os.path.isfile(user_folder + "/" + study_id + "_" + username + '.json'):
        raise JutrackValidationError("Invalid user for study " + study_id + " detected: " + str(username))


def is_valid_sensor(sensorname):
    if sensorname not in valid_data:
        # we only play with stuff we know...
        raise JutrackValidationError("Unaccepted sensorname detected: " + str(sensorname))


# ----------------------------------------PREPARATION------------------------------------------------


# Based on passed action term perform the action
def perform_action(action, data):
    if action == "write_data":
        output_file = exec_file(data)
        if output_file == "":
            print('No changes made')
        else:
            print(output_file + " written to disc.")

        return 'SUCCESS: Data successfully uploaded'
    elif action == "add_user":
        output_file = add_user(data)
        if output_file == "user exists":
            print("USER EXISTS: No changes made!")
            return "user exists"
        else:
            print(output_file + " written to disc.")

        return 'SUCCESS: User successfully added'
    elif action == "update_user":
        output_file = update_user(data)
        if output_file == "":
            print('No changes made')
        else:
            print(output_file + " written to disc.")

        return 'SUCCESS: User successfully updated'


# add uploaded files in folders according to BIDS format
def get_filename(data):
    i = datetime.datetime.now()
    timestamp = str(i.year) + '-' + str(i.month) + '-' + str(i.day) + 'T' + str(i.hour) + '-' + str(i.minute) + '-' \
        + str(i.second)

    study_id = data[0]['studyId']
    user_id = data[0]['username']
    device_id = data[0]['deviceid']
    data_name = data[0]['sensorname']

    # check for folder and create if a (sub-)folder does not exist
    data_folder = studys_folder + '/' + study_id + '/' + user_id + '/' + device_id + '/' + data_name
    if not os.path.isdir(data_folder):
        os.makedirs(data_folder)

    file_name = data_folder + '/' + study_id + '_' + user_id + '_' + device_id + '_' + data_name + '_' + timestamp
    return file_name, study_id


# if a file already exists we do not want to loose data, so we store under a name with a counter as suffix
def write_file(filename, data):
    target_file = filename + '.json'
    counter = 1

    while os.path.isfile(target_file):
        sys.stderr.write(target_file + " was already existing, therefore " + filename + '_' + str(counter) + '.json'
                         + " will be created.\r\n")
        target_file = filename + '_' + str(counter) + '.json'
        counter += 1

    with open(target_file, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return target_file


# ----------------------------------------EXECUTION--------------------------------------------------


def exec_file(data):
    file_name, study_id = get_filename(data)
    return write_file(file_name, data)


# stores user data (no personal data) in a new file
def add_user(data):
    study_id = data['studyId']
    user_id = data['username']

    # check for folder and create if a (sub-)folder does not exist
    if not os.path.isdir(user_folder):
        os.makedirs(user_folder)

    file_name = user_folder + '/' + study_id + '_' + user_id

    # Write to file and return the file name for logging
    target_file = file_name + '.json'
    if os.path.isfile(target_file):
        return "user exists"
    else:
        with open(target_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return target_file


# update an already existent user. If the user is somehow not found, add him
def update_user(data):
    i = datetime.datetime.now()
    timestamp = str(i.year) + '-' + str(i.month) + '-' + str(i.day) + 'T' + str(i.hour) + '-' + str(i.minute) + '-' \
        + str(i.second)

    study_id = data['studyId']
    user_id = data['username']
    status = data['status']

    file_name = user_folder + '/' + study_id + '_' + user_id

    if os.path.isfile(file_name + '.json'):
        with open(file_name + '.json') as f:
            content = json.load(f)
    else:
        return add_user(data)

    # append status and if status is left from client or unknown add time_left for study leave
    content['status'] = status
    if status == 1:
        content['time_left'] = data['time_left']
    elif status == 3:
        content['time_left'] = timestamp
    elif status == 0:
        content['time_left'] = ''
        # Write to file and return the file name for logging
    with open(file_name + '.json', 'w') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)

    return file_name + '.json'


# ----------------------------------------APPLICATION------------------------------------------------


# This method is called by the main endpoint
def application(environ, start_response):
    output = {}
    status = "200 OK"
    # We only accept POST-requests
    if environ['REQUEST_METHOD'] == 'POST':
        if 'HTTP_ACTION' in environ:
            action = environ['HTTP_ACTION']

            # read request body
            try:
                request_body = environ['wsgi.input'].read()
                
                # read passed MD5 value
                if 'HTTP_MD5' in environ:
                    md5 = environ['HTTP_MD5']
                else:
                    md5 = environ['HTTP_CONTENT-MD5']

                # calc_md5 = hashlib.md5(request_body).hexdigest()
                calc_md5 = hashlib.md5()
                calc_md5.update(request_body)
                calc_md5.hexdigest()

                # Check MD5 and content. If both is good perform actions
                if is_md5_matching(md5, calc_md5):
                    try:
                        data = is_valid_data(request_body, action, 0)
                        output = perform_action(action, data)
                        if output == "user exists":
                            status = '422 Existing Data Error'
                            output = {"message": "DATA-ERROR: The user you tried to add already exists!"}
                    except JutrackValidationError as e:
                        output = e.message
                else:
                    print('expected MD5: ' + str(calc_md5) + ', received MD5: ' + str(md5))
                    status = '500 Internal Server Error: There has been an MD5-MISMATCH!'
                    output = {"message": "MD5-MISMATCH: There has been a mismatch between the uploaded data and the received data, upload aborted!"}
            except ValueError:
                status = '500 Internal Server Error: ValueError occured during JSON parsing!'
                output = {"message": "The wsgi service was not able to parse the json content."}

        else:
            status = '500 Internal Server Error: There has been a KEY MISSING!'
            output = {"message": "MISSING-KEY: There was no action-attribute defined, upload aborted!"}
    else:
        status = '500 Internal Server Error: Wrong request type!'
        output = {"message": "Expected POST-request!"}

    # aaaaaand respond to client
    if isinstance(output, str):
        if 'status' in data:
            output = data
        else:
            output = data[0]
    
    start_response(status, [('Content-type', 'application/json')])
    output_dump = json.dumps(output)
    return [output_dump.encode('utf-8')]
