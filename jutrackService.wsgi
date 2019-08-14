import os

import hashlib
import json
import datetime

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
user_folder = storage_folder + '/users'


# add uploaded files in folders according to BIDS format
def store_file(data):
    i = datetime.datetime.now()
    timestamp = str(i.year) + '-' + str(i.month) + '-' + str(i.day) + 'T' + str(i.hour) + '-' + str(i.minute) + '-' \
        + str(i.second)

    study_id = data[0]['studyId']
    user_id = data[0]['username']
    device_id = data[0]['deviceid']
    data_name = data[0]['sensorname']

    # check for folder and create if a (sub-)folder does not exist
    data_folder = storage_folder + '/' + study_id + '/' + user_id + '/' + device_id + '/' + data_name
    if not os.path.isdir(data_folder):
        os.makedirs(data_folder)

    file_name = data_folder + '/' + study_id + '_' + user_id + '_' + device_id + '_' + data_name + '_' + timestamp

    # Write to file and return the file name for logging
    return write_file(file_name, data)


# stores user data (no personal data) in a new file
def add_user(data):
    i = datetime.datetime.now()
    timestamp = str(i.year) + '-' + str(i.month) + '-' + str(i.day) + 'T' + str(i.hour) + '-' + str(i.minute) + '-' \
        + str(i.second)

    study_id = data['studyId']
    user_id = data['username']

    data['time_joined'] = timestamp

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


# if a file already exists we do not want to loose data, so we store under a name with a counter as suffix
def write_file(filename, data):
    target_file = filename + '.json'
    counter = 1

    while os.path.isfile(target_file):
        target_file = filename + '_' + str(counter) + '.json'
        counter += 1

    with open(target_file, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return target_file


def perform_action(action, data):
    if action == "write_data":
        output_file = store_file(data)
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


def is_valid_data(d):
    """Perform all possible tests and return a flag"""

    if len(d) == 0:
        return False

    if 'status' in d:
        return True
    elif 'sensorname' in d[0]:
        if d[0]['sensorname'] not in valid_data:
            # we only play with stuff we know...
            return False
    else:
        return False

    return True


def is_md5_matching(md5, calc_md5):
    if calc_md5 == md5:
        return True
    else:
        return False


def application(environ, start_response):
    if environ['REQUEST_METHOD'] == 'POST':
        if 'HTTP_ACTION' in environ:
            action = environ['HTTP_ACTION']

            try:
                request_body = environ['wsgi.input'].read()
            except ValueError:
                start_response('500 Internal Server Error: ValueError occured during JSON parsing!',
                               [('Content-type', 'application/json')])
                return json.dumps({"message": "The wsgi service was not able to parse the json content."})

            if 'HTTP_MD5' in environ:
                md5 = environ['HTTP_MD5']
            else:
                md5 = environ['HTTP_CONTENT-MD5']

            calc_md5 = hashlib.md5(request_body).hexdigest()
            data = json.loads(request_body)  # form content as decoded JSON

            if is_md5_matching(md5, calc_md5):
                if is_valid_data(data):
                    output = perform_action(action, data)
                    if output == "user exists":
                        start_response('422 Existing Data Error', [('Content-type', 'application/json')])
                        return json.dumps({"message": "DATA-ERROR: The user you tried to add already exists!"})
                else:
                    output = 'INVALID DATA: The Data might be empty or the sensorname key is not allowed!'
            else:
                print('expected MD5: ' + str(calc_md5) + ', received MD5: ' + str(md5))
                start_response('500 Internal Server Error: There has been an MD5-MISMATCH!',
                               [('Content-type', 'application/json')])
                return json.dumps({"message": "MD5-MISMATCH: There has been a mismatch between the uploaded data "
                                              "+and the received data, upload aborted!"})
        else:
            start_response('500 Internal Server Error: There has been a KEY MISSING!',
                           [('Content-type', 'application/json')])
            return json.dumps({"message": "MISSING-KEY: There was no action-attribute defined, "
                                          "+upload aborted!"})
    else:
        start_response('500 Internal Server Error: Wrong request type!',
                       [('Content-type', 'application/json')])
        return json.dumps({"message": "Expected POST-request!"})

    # aaaaaand respond to client
    start_response('200 OK', [('Content-type', 'application/json')])  # ,('Content-Length', str(len(output)))])
    if 'status' in data:
        output_dict = data
    else:
        output_dict = data[0]
    print(output)
    return json.dumps(output_dict)
