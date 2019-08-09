import os

import hashlib
import json
import datetime
import ast

# server version
__version__ = 0

valid_data = [
    'accelerometer',
    'activity',
    'application usage',
    'barometer',
    'gravity sensor',
    'gyroscope',
    'location',
    'magnetic sensor',
    'rotation vector'
]

storage_folder = '/mnt/jutrack_data'


# add uploaded files in folders according to BIDS format
def store_file(data):
    i = datetime.datetime.now()

    timestamp = str(i.year) + '-' + str(i.month) + '-' + str(i.day) + 'T' + str(i.hour) + '-' + str(i.minute) + '-' \
        + str(i.second)
    # check for folders and create if nessessary

    study_id = data[0]['studyId']
    user_id = data[0]['username']
    device_id = data[0]['deviceid']
    data_name = data[0]['sensorname']

    data_folder = storage_folder + '/' + study_id + '/' + user_id + '/' + device_id + '/' + data_name
    if not os.path.isdir(data_folder):
        os.makedirs(data_folder)

    file_name = data_folder + '/' + study_id + '_' + user_id + '_' + device_id + '_' + data_name + '_' + timestamp

    # Write to file and return the file name for logging
    return write_file(file_name, data)


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


def is_valid_data(d):
    """Perform all possible tests and return a flag"""

    if len(d) == 0:
        return False

    if 'sensorname' in d[0]:
        if d[0]['sensorname'] not in valid_data:
            # we only play with stuff we know...
            return False
    else:
        return False

    return True


def dict_to_ascii(d):
    for data_entry in range(0, len(d)):
        d[data_entry] = ast.literal_eval(json.dumps(d[data_entry]))
    return d


def is_md5_matching(md5, calc_md5):
    if calc_md5 == md5:
        return True
    else:
        return False


def application(environ, start_response):
    output = ''

    if environ['REQUEST_METHOD'] == 'POST':
        request_body = environ['wsgi.input'].read()
        md5 = environ['HTTP_MD5']

        calc_md5 = hashlib.md5(request_body).hexdigest()
        data = json.loads(request_body)  # form content as decoded JSON

        data = dict_to_ascii(data)

        if is_md5_matching(md5, calc_md5):
            if is_valid_data(data):
                output_file = store_file(data)

                if output_file == "":
                    print('No changes made')
                else:
                    print(output_file + " written to disc.")

                output = 'Data successfully uploaded'

            else:
                output = 'Invalid data!'
        else:
            output = 'There has been a mismatch between the uploaded data and the received data, upload aborted!'

    # aaaaaand respond to client
    start_response('200 OK', [('Content-type', 'text/plain'),
                              ('Content-Length', str(len(output)))])
    return [output]
