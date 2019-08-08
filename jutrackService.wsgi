import os

import hashlib
import json
import datetime
import glob
import ast

# server version
__version__ = 0

opj = os.path.join

cwd = os.path.dirname(__file__)

utc_now = datetime.datetime.now().strftime('%Y.%m.%d-%H.%M.%S')

valid_data = ['accelerometer', 'activity', 'application usage', 'barometer', 'gravity sensor', 'gyroscope', 'location',
              'magnetic sensor',  'rotation vector', 'K6DS3TR Acceleration Sensor']
valid_accelerometer = ['ID', 'name', 'timestamp', 'deviceID', 'userID', 'X', 'Y', 'Z']
valid_activity = ['ID', 'name', 'timestamp', 'deviceID', 'userID', 'activity type', 'confidence']
valid_activity_type = ['in vehicle', 'on bicycle', 'on foot', 'still', 'unknown', 'tilting', 'walking', 'running']
valid_application_usage = ['ID', 'name', 'timestamp', 'deviceID', 'userID', 'beginTime', 'endTime', 'lastTimeUsed',
                           'totalTimeInForeground']
valid_barometer = ['ID', 'name', 'timestamp', 'deviceID', 'userID', 'height']
valid_gravity_sensor = ['ID', 'name', 'timestamp', 'deviceID', 'userID', 'X', 'Y', 'Z']
valid_gyroscope = ['ID', 'name', 'timestamp', 'deviceID', 'userID', 'X', 'Y', 'Z']
valid_location = ['ID', 'name', 'timestamp', 'deviceID', 'userID', 'alt.', 'long.', '.lat', 'accuracy']
valid_magnetic_sensor = ['ID', 'name', 'timestamp', 'deviceID', 'userID', 'X', 'Y', 'Z', 'tetha', 'beta']
valid_rotation_vector = ['ID', 'name', 'timestamp', 'deviceID', 'userID', 'X', 'Y', 'Z']

valid_device = ['ID', 'type', 'model', 'OS version', 'API level']
valid_user = ['ID', 'email']
valid_study = ['ID', 'name', 'description']

valid_user_study = ['userID', 'studyID', 'joinedTimeStamp', 'isActive', 'leftTimestamp']
valid_user_device = ['userID', 'deviceID', 'startTimeStamp', 'endTimeStamp', 'status']


# Device Handling
def add_device(data, deviceID):
    filename = 'device_' + deviceID + '.json'
    with open(filename, 'w', encoding = 'utf-8') as f:
        json.dump(data, f, ensure_ascii = False, indent = 4)
    return filename


def deactivate_device(deviceID):
    filename = 'device_' + deviceID + '.json'
    if os.path.isfile(filename):
        os.rename(filename, 'device_' + deviceID + '_inactive.json')
        print('Device ' + deviceID + ' set to inactive!')


def reactivate_device(deviceID):
    filename = 'device_' + deviceID + '_inactive.json'
    if os.path.isfile(filename):
        os.rename(filename, 'device_' + deviceID + '.json')
        print('Device ' + deviceID + ' set back to active!')


# User Handling
def add_user(data, userID):
    filename = 'user_' + userID + '.json'
    with open(filename, 'w', encoding = 'utf-8') as f:
        json.dump(data, f, ensure_ascii = False, indent = 4)
    return filename


def deactivate_user(userID):
    filename = 'user_' + userID + '.json'
    if os.path.isfile(filename):
        os.rename(filename, 'user_' + userID + '_inactive.json')
        print('User ' + userID + ' set to inactive!')


def reactivate_user(userID):
    filename = 'user_' + userID + '_inactive.json'
    if os.path.isfile(filename):
        os.rename(filename, 'user_' + userID + '.json')
        print('User ' + userID + ' set back to active!')


# Study Handling
def add_study(data, studyID):
    filename = 'study_' + studyID + '.json'
    with open(filename, 'w', encoding = 'utf-8') as f:
        json.dump(data, f, ensure_ascii = False, indent = 4)
    return filename


def deactivate_study(studyID):
    filename = 'study_' + studyID + '.json'
    if os.path.isfile(filename):
        os.rename(filename, 'study_' + studyID + '_inactive.json')
        print('Study '+studyID+' set to inactive!')


def reactivate_study(studyID):
    filename = 'study_' + studyID + '_inactive.json'
    if os.path.isfile(filename):
        os.rename(filename, 'study_' + studyID + '.json')
        print('Study '+studyID+' set back to active!')


# User <-> Study
def add_study_to_user(userID, studyID, timestamp, data):
    filename = 'user' + userID + '_study' + studyID + '_joined_' + timestamp + '.json'
    with open(filename, 'w', encoding = 'utf-8') as f:
        json.dump(data, f, ensure_ascii = False, indent = 4)
    print('Study ' + studyID + ' set for user ' + userID + '!')


def remove_study_from_user(userID, studyID, timestamp):
    for filename in glob.glob('user' + userID + '_study' + studyID + '_joined_*.json'):
        os.rename(filename, filename[:-5] + '_inactive_left_' + timestamp+'.json')
        print('Study ' + studyID + ' set to inactive for user ' + userID + '!')


# User <-> Device
def add_device_to_user(userID, deviceID, timestamp, data):
    filename = 'user' + userID + '_device' + deviceID + '_lend_' + timestamp + '.json'
    with open(filename, 'w', encoding = 'utf-8') as f:
        json.dump(data, f, ensure_ascii = False, indent = 4)


def remove_device_from_user(userID, deviceID, timestamp):
    for filename in glob.glob('user' + userID + '_device' + deviceID + '_lend_*.json'):
        os.rename(filename, filename[:-5] + '_given_back_' + timestamp + '.json')
        print('Device ' + deviceID + ' was given back by user ' + userID + '!')


# General methods
def get_client_ip(environ):
    try:
        return environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
    except KeyError:
        return environ['REMOTE_ADDR']


def get_client_agent(environ):
    try:
        return environ['HTTP_USER_AGENT']
    except KeyError:
        return 'unknown'


def generate_record_id(data, ip):
    rid = hashlib.md5('%s%s%s' % (data, utc_now, ip)).hexdigest()
    return rid


# add uploaded files in folders according to BIDS format
def processData(d):
    timestamp = datetime.date.today().isoformat()
# check for folders and create if nessessary
    storage_folder = '/mnt/jutrack_data'

    studyID = d[0]['studyId']
    userID = d[0]['username']
    deviceID = d[0]['deviceid']
    data_name = d[0]['sensorname']

    study_folder = storage_folder + '/' + studyID
    if not os.path.isdir(study_folder):
        os.mkdir(study_folder) 

    user_folder = study_folder + '/' + userID
    if not os.path.isdir(user_folder):
        os.mkdir(user_folder)

    device_folder = user_folder + '/' + deviceID
    if not os.path.isdir(device_folder):
        os.mkdir(device_folder)

    data_folder = device_folder + '/' + data_name
    if not os.path.isdir(data_folder):
        os.mkdir(data_folder)

    target_dir = data_folder +'/'
    target_file = studyID + '_' + userID + '_' + deviceID + '_' + data_name + '_' + timestamp + '.json'

    filename = target_dir + target_file
    print(filename)

    if os.path.isfile(filename):
        return ""

    with open(filename, 'w') as f:
        json.dump(d, f, ensure_ascii = False, indent = 4)
    return filename


def is_valid_data(d):
    """Perform all possible tests and return a flag"""
    print(str(d) + ' type:' + str(type(d)))
    print(str(d[0]) + ' type:' + str(type(d[0])))

    if len(d) == 0:
        return False

    if 'sensorname' in d[0]:
        print(d[0]['sensorname'])
        if d[0]['sensorname'] not in valid_data:
            # we only play with stuff we know...
            return False

    return True


def clean_up_dict(d):
    for data_entry in range(0, len(d)):
        d[data_entry] = ast.literal_eval(json.dumps(d[data_entry]))
    return d


def md5_matches(md5, calcMD5):
    print('received MD5:' + md5 + ', calculated MD5:' + calcMD5)
    if calcMD5 == md5:
        print("MD5 correct")
        return True
    else:
        print("MD5 mismatch")
        return False


def application(environ, start_response):
    status = '404 Not Found'
    output = ''
    print(str(environ))    

    if environ['REQUEST_METHOD'] == 'POST':
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            request_body_size = 0

        request_body = environ['wsgi.input'].read()
        print('BODY: ' + str(request_body))
        md5 = environ['HTTP_MD5']
        # headers = json.loads(request_headers) 
        # md5 = headers['md5']

        try:
            calcMD5 = hashlib.md5(request_body).hexdigest()
            data = json.loads(request_body)  # form content as decoded JSON
        except:
            data = {}
            status = '400 Bad Request'

        data = clean_up_dict(data)

        if md5_matches(md5, calcMD5):
            if is_valid_data(data):
                outputFile = processData(data)

                if outputFile == "":
                    status = '402 File already exists'
                    output = 'No changes made'
                else:
                    print(outputFile + " written to disc.")

            # get/generate the needed info to save
                client_ip = get_client_ip(environ)
                client_agent = get_client_agent(environ)
                record_id = generate_record_id(data, client_ip)

            # record = json.dumps(data)
            # save private file (ip and date/time)
            # with open(opj(survey_priv_dir, record_id), 'w') as _file:
            #     _file.write(json.dumps({'ip': client_ip, 'agent': client_agent, 'dt': utc_now}))
                output = 'Data successfully uploaded'
            
            else:
                status = '400 Bad Request'
                # TODO: should be an error of some kind
                output = 'Invalid data!'
        else:
            status = '402 Bad Data'
            output = 'There has been a mismatch between the uploaded data and the received data, upload aborted!'

    # aaaaaand respond to client
    start_response('200 OK', [('Content-type', 'text/plain'),
                              ('Content-Length', str(len(output)))])
    return [output]


# Instantiate the server
# httpd = make_server(
#    'localhost',  # The host name
#    port=8001,  # change to 443 on the server side
#    app=application  # The application object name, in this case a function
# )
# print("Running on port 8000 ...")
# Wait for a single request, serve it and quit
# httpd.serve_forever()
