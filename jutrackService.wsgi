import os
from wsgiref.simple_server import make_server

import hashlib
import json
import datetime
import glob

# server version
__version__ = 0

opj = os.path.join

cwd = os.path.dirname(__file__)
private_dir = opj('/mnt/jutrack/records/private')
# public_dir = opj('/mnt/jutrack/records/public')
utc_now = datetime.datetime.now().strftime('%Y.%m.%d-%H.%M.%S')

valid_data = ['accelerometer', 'activity', 'application usage', 'barometer', 'gravity sensor', 'gyroscope', 'location',
              'magnetic sensor',  'rotation vector']
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


def add_accelerometer_data(data, studyID, userID, deviceID, timestamp):
    targetdir = studyID+'/'+userID+'/'+deviceID+'/accelerometer/'
    filename = targetdir + studyID+'_'+userID+'_'+deviceID+'_accelerometer_'+timestamp+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename


def add_activity_data(data, studyID, userID, deviceID, timestamp):
    targetdir = studyID + '/' + userID + '/' + deviceID + '/activity/'
    filename = targetdir + studyID+'_'+userID+'_'+deviceID+'_activity_'+timestamp+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename


def add_application_usage_data(data, studyID, userID, deviceID, timestamp):
    targetdir = studyID + '/' + userID + '/' + deviceID + '/application_usage/'
    filename = targetdir + studyID+'_'+userID+'_'+deviceID+'_application_usage_'+timestamp+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename


def add_barometer_data(data, studyID, userID, deviceID, timestamp):
    targetdir = studyID + '/' + userID + '/' + deviceID + '/barometer/'
    filename = targetdir + studyID+'_'+userID+'_'+deviceID+'_barometer_'+timestamp+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename


def add_gravity_sensor_data(data, studyID, userID, deviceID, timestamp):
    targetdir = studyID + '/' + userID + '/' + deviceID + '/gravity_sensor/'
    filename = targetdir + studyID+'_'+userID+'_'+deviceID+'_gravity_sensor_'+timestamp+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename


def add_gyroscope_data(data, studyID, userID, deviceID, timestamp):
    targetdir = studyID + '/' + userID + '/' + deviceID + '/gyroscope/'
    filename = targetdir + studyID+'_'+userID+'_'+deviceID+'_gyroscope_'+timestamp+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename


def add_location_data(data, studyID, userID, deviceID, timestamp):
    targetdir = studyID + '/' + userID + '/' + deviceID + '/location/'
    filename = targetdir + studyID+'_'+userID+'_'+deviceID+'_location_'+timestamp+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename


def add_magnetic_sensor_data(data, studyID, userID, deviceID, timestamp):
    targetdir = studyID + '/' + userID + '/' + deviceID + '/magnetic_sensor/'
    filename = targetdir + studyID+'_'+userID+'_'+deviceID+'_magnetic_sensor_'+timestamp+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename


def add_rotation_vector_data(data, studyID, userID, deviceID, timestamp):
    targetdir = studyID + '/' + userID + '/' + deviceID + '/rotation_vector/'
    filename = targetdir + studyID+'_'+userID+'_'+deviceID+'_rotation_vector_'+timestamp+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename


# Device Handling
def add_device(data, deviceID):
    filename = 'device_'+deviceID+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename


def deactivate_device(deviceID):
    filename = 'device_' + deviceID + '.json'
    if os.path.isfile(filename):
        os.rename(filename, 'device_' + deviceID + '_inactive.json')
        print('Device '+deviceID+' set to inactive!')


def reactivate_device(deviceID):
    filename = 'device_' + deviceID + '_inactive.json'
    if os.path.isfile(filename):
        os.rename(filename, 'device_' + deviceID + '.json')
        print('Device '+deviceID+' set back to active!')


# User Handling
def add_user(data, userID):
    filename = 'user_'+userID+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename


def deactivate_user(userID):
    filename = 'user_' + userID + '.json'
    if os.path.isfile(filename):
        os.rename(filename, 'user_' + userID + '_inactive.json')
        print('User '+userID+' set to inactive!')


def reactivate_user(userID):
    filename = 'user_' + userID + '_inactive.json'
    if os.path.isfile(filename):
        os.rename(filename, 'user_' + userID + '.json')
        print('User '+userID+' set back to active!')


# Study Handling
def add_study(data, studyID):
    filename = 'study_'+studyID+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
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
    filename = 'user' + userID + '_study' + studyID + '_joined_'+timestamp+'.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print('Study ' + studyID + ' set for user ' + userID + '!')


def remove_study_from_user(userID, studyID, timestamp):
    for filename in glob.glob('user' + userID + '_study' + studyID + '_joined_*.json'):
        os.rename(filename, filename[:-5]+'_inactive_left_'+timestamp+'.json')
        print('Study ' + studyID + ' set to inactive for user '+userID+'!')


# User <-> Device
def add_device_to_user(userID, deviceID, timestamp, data):
    filename = 'user' + userID + '_device' + deviceID + '_lend_' + timestamp + '.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def remove_device_from_user(userID, deviceID, timestamp):
    for filename in glob.glob('user' + userID + '_device' + deviceID + '_lend_*.json'):
        os.rename(filename, filename[:-5]+'_given_back_'+timestamp+'.json')
        print('Device ' + deviceID + ' was given back by user '+userID+'!')


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


def processData(d):
    timestamp = datetime.date.today().isoformat()
    if d['data_name'] == 'accelerometer':
        return add_accelerometer_data(d['content'], d['studyID'], d['userID'], d['deviceID'], timestamp)
    elif d['data_name'] == 'activity':
        return add_activity_data(d['content'], d['studyID'], d['userID'], d['deviceID'], timestamp)
    elif d['data_name'] == 'application usage':
        return add_application_usage_data(d['content'], d['studyID'], d['userID'], d['deviceID'], timestamp)
    elif d['data_name'] == 'barometer':
        return add_barometer_data(d['content'], d['studyID'], d['userID'], d['deviceID'], timestamp)
    elif d['data_name'] == 'gravity sensor':
        return add_gravity_sensor_data(d['content'], d['studyID'], d['userID'], d['deviceID'], timestamp)
    elif d['data_name'] == 'gyroscope':
        return add_gyroscope_data(d['content'], d['studyID'], d['userID'], d['deviceID'], timestamp)
    elif d['data_name'] == 'location':
        return add_location_data(d['content'], d['studyID'], d['userID'], d['deviceID'], timestamp)
    elif d['data_name'] == 'magnetic sensor':
        return add_magnetic_sensor_data(d['content'], d['studyID'], d['userID'], d['deviceID'], timestamp)
    elif d['data_name'] == 'rotation vector':
        return add_rotation_vector_data(d['content'], d['studyID'], d['userID'], d['deviceID'], timestamp)


def is_valid_data(d):
    """Perform all possible tests and return flag"""
    if 'content' not in d:
        return False
    else:
        calcMD5 = hashlib.md5(d["content"].encode('utf-8')).hexdigest()
        md5 = d["md5"]
        if calcMD5 != md5:
            return False

    if 'data_name' in d:
        if d['data_name'] not in valid_data:
            # we only play with stuff we know...
            return False

    return True


def application(environ, start_response):
    status = '404 Not Found'
    output = ''

    if environ['REQUEST_METHOD'] == 'POST':
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            request_body_size = 0

        request_body = environ['wsgi.input'].read(request_body_size)

        try:
            data = json.loads(request_body)  # form content as decoded JSON
        except:
            data = {}
            status = '400 Bad Request'

        if is_valid_data(data):
            if 'data_name' in data:
                outputFile = processData(data)
                print(outputFile + " written to disc.")
            # elif 'query_type' in data:

            # get/generate the needed info to save
            client_ip = get_client_ip(environ)
            client_agent = get_client_agent(environ)
            record_id = generate_record_id(data, client_ip)

            # record = json.dumps(data)
            # save private file (ip and date/time)
            # with open(opj(survey_priv_dir, record_id), 'w') as _file:
            #     _file.write(json.dumps({'ip': client_ip, 'agent': client_agent, 'dt': utc_now}))

            output = 'success.html'
        else:
            status = '400 Bad Request'
            # TODO: should be an error of some kind
            output = 'Not like that my friend'

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