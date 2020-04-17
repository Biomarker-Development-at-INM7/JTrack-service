import os
import hashlib
import json
from json import JSONDecodeError

# -------------------- CONFIGRATION -----------------------
storage_folder = '/mnt/jutrack_data'
studies_folder = storage_folder + "/studies"
users_folder = storage_folder + '/users'

sensor_names = ['accelerometer', 'activity', 'application_usage', 'barometer', 'gravity_sensor', 'gyroscope',
                'location', 'magnetic_sensor', 'rotation_vector', 'linear_acceleration']


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
def is_valid_data(body, verbose=0):
    """Perform all possible tests and return a flag"""
    data = is_valid_json(body, verbose)

    if len(data) == 0:
        raise JutrackValidationError("ERROR: The uploaded content was empty.")

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
    if not os.path.isdir(studies_folder + "/" + study_id):
        raise JutrackValidationError("Invalid study detected: " + str(study_id))


def is_valid_user(study_id, username):
    if not os.path.isfile(users_folder + "/" + study_id + "_" + username + '.json'):
        raise JutrackValidationError("Invalid user for study " + study_id + " detected: " + str(username))


# -------------------------- FUNCTIONALITY ------------------------------


def get_study_csv(json_data):
    study_id = json_data["study"]
    csv_path = storage_folder + '/jutrack_dashboard_' + study_id + '.csv'
    file = open(csv_path, "r")
    content = file.read()
    file.close()
    return content


def list_studies():
    study_list = []
    for studies in os.listdir(storage_folder):
        if studies != "users" and studies != "lost+found" and os.path.isdir(storage_folder + '/' + studies):
            study_list.append(studies)

    return study_list


from datalad.api import Dataset


def create_study(json_data):
    study_id = json_data["name"]
    folder_name = studies_folder + "/" + study_id

    if not os.path.isdir(folder_name):
        os.makedirs(folder_name)
        datalad_dataset = Dataset(folder_name)
        file_name = studies_folder + "/" + study_id + "/" + study_id + ".json"
        with open(file_name, 'w') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        datalad_dataset.save(file_name, message="new file " + file_name + " for study")


# ----------------------------------------APPLICATION------------------------------------------------


# This method is called by the main endpoint
def application(environ, start_response):
    # We only accept POST-requests
    if environ['REQUEST_METHOD'] == 'POST':
        if 'HTTP_ACTION' in environ:
            action = environ['HTTP_ACTION']

            # read request body
            try:
                request_body = environ['wsgi.input'].read()
            except ValueError:
                start_response('500 Internal Server Error: ValueError occured during JSON parsing!',
                               [('Content-type', 'application/json')])
                return json.dumps({"message": "The wsgi service was not able to parse the json content."})

            # read passed MD5 value
            if 'HTTP_MD5' in environ:
                md5 = environ['HTTP_MD5']
            else:
                md5 = environ['HTTP_CONTENT-MD5']

            calc_md5 = hashlib.md5(request_body).hexdigest()

            # Check MD5 and content. If both is good perform actions
            if is_md5_matching(md5, calc_md5):
                try:
                    data = is_valid_data(request_body, 0)
                    output = "NONE"
                    if action == "get_study":
                        output = get_study_csv(data)
                    elif action == "get_study_list":
                        output = list_studies()
                    if output == "NONE":
                        start_response('404 File Not Found', [('Content-type', 'application/json')])
                        return json.dumps({"message": "DATA-ERROR: The content for the selected study was not found!"})
                except JutrackValidationError as e:
                    output = e.message
            else:
                print('expected MD5: ' + str(calc_md5) + ', received MD5: ' + str(md5))
                start_response('500 Internal Server Error: There has been an MD5-MISMATCH!',
                               [('Content-type', 'application/json')])
                return json.dumps({"message": "MD5-MISMATCH: There has been a mismatch between the uploaded data "
                                              "+and the received data, fetching aborted!"})
        else:
            start_response('500 Internal Server Error: There has been a KEY MISSING!',
                           [('Content-type', 'application/json')])
            return json.dumps({"message": "MISSING-KEY: There was no action-attribute defined, "
                                          "+fetching aborted!"})
    else:
        start_response('500 Internal Server Error: Wrong request type!',
                       [('Content-type', 'application/json')])
        return json.dumps({"message": "Expected POST-request!"})

    # aaaaaand respond to client
    start_response('200 OK', [('Content-type', 'application/json')])  # ,('Content-Length', str(len(output)))])
    output_dict = {"content": output}
    print(output)
    return json.dumps(output_dict)
