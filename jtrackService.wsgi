import os

import hashlib
import json
import datetime
import sys
import time
import smtplib
import pwd

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
    'linear_acceleration',
    'ema',
    'active_labeling',
    'lockUnlock'
]

storage_folder = '/mnt/jutrack_data'
studies_folder = storage_folder + '/studies'
junk_folder = storage_folder + '/junk'
user_folder = storage_folder + '/users'
content = {}

uid = pwd.getpwnam("www-data").pw_uid
s_uid = pwd.getpwnam("jfischer").pw_uid
gid = 3619

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


class JutrackLeftUserError(JutrackError):
    """Exception raised for send data of an already left user.

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

    if 'status' in data or 'status_ema' in data:
        return data

    study_id = data[0]['studyId']
    user_id = data[0]['username']
    device_id = ""
    if 'deviceid' in data[0]:
        device_id = data[0]['deviceid']
    elif 'deviceid_ema' in data[0]:
        device_id = data[0]['deviceid_ema']

    is_valid_study(study_id, data)

    if action == "write_data":
        sensorname = data[0]['sensorname']
        is_valid_user(study_id, user_id, sensorname)
        data = is_valid_device(study_id, user_id, device_id, data)
        is_valid_sensor(sensorname)
    else:
        is_valid_user(study_id, user_id, "")
        data = is_valid_device(study_id, user_id, device_id, data)
    return data


def is_valid_json(body, verbose):
    try:
        data = json.loads(body.decode('utf-8'))
        if verbose:
            print("NOTICE: The uploaded content is valid json.")
    except Exception:
        raise JutrackValidationError("ERROR: The uploaded content is not valid json.")

    return data


def is_valid_study(study_id, data):
    if not os.path.isdir(studies_folder + "/" + study_id):
        if not os.path.isdir(junk_folder + "/" + study_id):
            os.makedirs(junk_folder + "/" + study_id)
        i = datetime.datetime.now()
        timestamp = i.strftime("%Y-%m-%dT%H-%M-%S")

        study_id = data[0]['studyId']
        user_id = data[0]['username']
        device_id = ""
        if 'deviceid' in data[0]:
            device_id = data[0]['deviceid']
        elif 'deviceid_ema' in data[0]:
            device_id = data[0]['deviceid_ema']

        data_name = "no_sensor"
        if 'sensorname' in data[0]:
            data_name = data[0]['sensorname']

        if study_id.strip() == "":
            study_id = "nonameStudy"
        if user_id.strip() == "":
            user_id = "noname"
        if device_id.strip() == "":
            device_id = "nodevice"

        filename = junk_folder + "/" + study_id + '/' + study_id + '_' + user_id + '_' + device_id + '_' \
            + data_name + '_' + timestamp
        data_folder = junk_folder + "/" + study_id
        if not os.path.isdir(data_folder):
            os.makedirs(data_folder)
        target_file = filename + '.json'
        counter = 1

        while os.path.isfile(target_file):
            sys.stderr.write(target_file + " was already existing, therefore " + filename + '_' + str(counter) + '.json'
                             + " will be created.\r\n")
            target_file = filename + '_' + str(counter) + '.json'
            counter += 1

        with open(target_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        # alert via mail
        write_output_message("(Invalid Study)Following file was written to Junk folder: " + target_file)

        raise JutrackValidationError(
            "Invalid study detected: " + str(study_id) + ", UserID:" + str(data[0]['username']))


def is_valid_user(study_id, username, sensorname):
    if not os.path.isfile(user_folder + "/" + study_id + "_" + username + '.json'):
        # alert via mail
        write_output_message("(Invalid user) Following user_id tried to send data: " + username)

        raise JutrackValidationError("Invalid user for study " + study_id + " detected: " + str(username))
    else:
        with open(user_folder + "/" + study_id + "_" + username + '.json', encoding='utf-8') as f:
            user_data = json.load(f)

        if sensorname == "ema":
            if 'status_ema' in user_data and user_data['status_ema'] == 2:
                left_day = int((time.time() - int(user_data["time_left_ema"]) / 1000.0) / 86400.0)
                if left_day > 1:
                    # alert via mail
                    write_output_message("(Left user) Following user_id tried to send data but already left ema: "
                                         + username)

                    raise JutrackLeftUserError("User " + str(username) + " already left study: " + study_id)

        else:
            if 'status' in user_data and user_data['status'] == 2:
                left_day = int((time.time() - int(user_data["time_left"]) / 1000.0) / 86400.0)
                if left_day > 1:
                    # alert via mail
                    write_output_message("(Left user) Following user_id tried to send data but already left the study: "
                                         + username)

                    raise JutrackLeftUserError("User " + str(username) + " already left study: " + study_id)


def is_valid_device(study_id, user_id, device_id, data):
    with open(user_folder + "/" + study_id + "_" + user_id + '.json', encoding='utf-8') as f:
        user_data = json.load(f)
    if not ("deviceid" in user_data and user_data["deviceid"] == device_id) and not (
            "deviceid_ema" in user_data and user_data["deviceid_ema"] == device_id):
        # alert via mail
        if isinstance(data, list):
            data[0]["deviceid_lastSend"] = device_id
        else:
            data["deviceid_lastSend"] = device_id
        # user_data["deviceid_lastSend"] = device_id
        write_output_message("(Unknown device) Following deviceID tried to send data for user " + str(user_id) + ": "
                             + str(device_id))
        print(device_id + " not recognized.")
    return data


def is_valid_sensor(sensorname):
    if sensorname not in valid_data:
        # we only play with stuff we know...
        # alert via mail
        write_output_message("(Unknown device) Following sensor tried to send data : " + str(sensorname))
        raise JutrackValidationError("Unaccepted sensorname detected: " + str(sensorname))


def is_valid_userdata(data):
    if not ('studyId' in data and 'username' in data and ('status' in data or 'status_ema' in data)):
        raise JutrackValidationError("ERROR: The uploaded json does not include "
                                     "the required user content to update the user.")


def is_valid_admin(data):
    study_id = data["studyId"]
    username = data["username"]
    if not os.path.isfile(studies_folder + "/" + study_id + "/" + study_id + ".json"):
        # alert via mail
        write_output_message("(Invalid study_id) request from admin  ")

        raise JutrackValidationError(
            "Invalid request for study " + study_id + " detected: "
        )

    if not username == "inm7":
        # alert via mail
        write_output_message(
            "(Invalid admin user) Following user tried to access study: " + username
        )

        raise JutrackValidationError(
            "Invalid admin user  request for" + study_id + " detected: " + str(username)
        )


# ----------------------------------------PREPARATION------------------------------------------------


def chgrp(filepath, group_id):
    user_id = os.stat(filepath).st_uid
    os.chown(filepath, user_id, group_id)


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
        elif output_file == "user is already enrolled":
            print("USER ALREADY ENROLLED: No changes made to enrolled subjects!")
            return "user already enrolled"
        else:
            print(output_file + " written to disc.")

        return 'SUCCESS: User successfully added'
    elif action == "update_user":
        is_valid_userdata(data)

        if "status_ema" in data:
            output_file = update_ema(data)
        else:
            output_file = update_user(data)
        if output_file == "":
            print('No changes made')
        else:
            print(output_file + " written to disc.")

        return 'SUCCESS: User successfully updated'

    elif action == "admin_user":
        is_valid_admin(data)
        output_file = admin_user(data)
        if not bool(output_file):
            print('No study JSON found!')
        else:
            print("Study JSON successfully retrieved.")

        return output_file


# add uploaded files in folders according to BIDS format
def get_filename(data):
    i = datetime.datetime.now()
    timestamp = i.strftime("%Y-%m-%dT%H-%M-%S")

    study_id = data[0]['studyId']
    user_id = data[0]['username']
    device_id = data[0]['deviceid']
    data_name = data[0]['sensorname']

    # choose the first non-empty values to name the file properly
    chunk_x = 1
    while study_id == "" and len(data) > chunk_x:
        study_id = data[chunk_x]['studyId']
        chunk_x += 1

    chunk_x = 1
    while user_id == "" and len(data) > chunk_x:
        user_id = data[chunk_x]['username']
        chunk_x += 1

    chunk_x = 1
    while device_id == "" and len(data) > chunk_x:
        device_id = data[chunk_x]['deviceid']
        chunk_x += 1

    chunk_x = 1
    while data_name == "" and len(data) > chunk_x:
        data_name = data[chunk_x]['sensorname']
        chunk_x += 1

    # check for folder and create if a (sub-)folder does not exist
    data_folder = studies_folder + '/' + study_id + '/' + user_id + '/' + device_id + '/' + data_name
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
    # if data[0]["sensorname"] == "application_usage":
    #     sys.stderr.write(''.join(str(x) for x in data))
    with open(target_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    os.chmod(target_file, 0o664)
    chgrp(target_file, gid)

    return target_file


def send_mail(sender, receivers, subject, text):
    mail_to = ",".join(receivers)
    message = 'To: {}\nFrom: {}\nSubject: {}\n\n{}'.format(mail_to, sender, subject, text)
    try:
        smtp_obj = smtplib.SMTP('mail.fz-juelich.de', port=25)
        smtp_obj.sendmail(sender, receivers, message)
        print("Successfully sent email")
        smtp_obj.quit()
    except smtplib.SMTPException:
        print("Error: unable to send email")


# ----------------------------------------EXECUTION--------------------------------------------------


def exec_file(data):
    file_name, study_id = get_filename(data)
    return write_file(file_name, data)


def admin_user(data):
    study_id = data['studyId']
    study_json = {}
    target_file = studies_folder + '/' + study_id + '/' + study_id + '.json'
    with open(target_file, encoding='utf-8') as f:
        study_json = json.load(f)
    os.chmod(target_file, 0o775)
    chgrp(target_file, gid)
    return study_json


# stores user data (no personal data) in a new file
def add_user(data):
    study_id = data['studyId']
    user_id = data['username']

    # apply study duration
    app_type = ""
    if "applicationType" in data:
        app_type = data['applicationType']
    data["study_duration"], data["initial_join"] = get_remaining_days_in_study(study_id, user_id, app_type)
    # data["study_duration"] = res[0]
    # data["initial_join"] = res[1]
    data["active_labeling"] = get_active_labeling(study_id)
    # check for folder and create if a (sub-)folder does not exist
    if not os.path.isdir(user_folder):
        os.makedirs(user_folder)
    file_name = user_folder + '/' + study_id + '_' + user_id
    study_json = studies_folder + '/' + study_id + '/' + study_id + '.json'

    # Write to file and return the file name for logging
    target_file = file_name + '.json'
    if os.path.isfile(target_file):
        with open(study_json, encoding='utf-8') as s:
            study_data = json.load(s)

        with open(target_file, encoding='utf-8') as f:
            user_data = json.load(f)

        if 'status_ema' in user_data and 'status' in user_data:
            print(user_data)
            return "user exists"
        elif 'status' in user_data and 'status' in data:
            print(user_data)
            return "user is already enrolled"
        elif 'status_ema' not in user_data and 'status_ema' in data and 'survey' in study_data:
            for key in data:
                if key not in user_data:
                    user_data[key] = data[key]
            user_data["time_joined_ema"] = int(user_data["time_joined_ema"])
            user_data["time_left_ema"] = int(user_data["time_left_ema"])
            with open(target_file, 'w', encoding='utf8') as f:
                json.dump(user_data, f, ensure_ascii=False, indent=4)
            return "EMA registered, " + target_file + " written to disc."
        elif 'status' not in user_data and 'status' in data and 'frequency' in study_data:
            for key in data:
                if key not in user_data:
                    user_data[key] = data[key]
            user_data["time_joined"] = int(user_data["time_joined"])
            user_data["time_left"] = int(user_data["time_left"])
            with open(target_file, 'w', encoding='utf8') as f:
                json.dump(user_data, f, ensure_ascii=False, indent=4)
            return "Main App registered, " + target_file + " written to disc."
        else:
            # alert via mail
            write_output_message("(ERROR)Insufficient status value given for user " + str(user_id) +
                                 " in study " + str(study_id) + ", user could not be added to use the app!\n"+json.dumps(data))
            raise JutrackValidationError("Unaccepted status value detected")
    else:
        with open(study_json, encoding='utf-8') as s:
            study_data = json.load(s)
        if ('status_ema' in data and 'survey' in study_data) or ('status' in data and 'frequency' in study_data):
            if 'status_ema' in data:
                data["time_joined_ema"] = int(data["time_joined_ema"])
                data["time_left_ema"] = int(data["time_left_ema"])
            with open(target_file, 'w', encoding='utf8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            os.chmod(target_file, 0o664)
            chgrp(target_file, gid)
        else:
            write_output_message("(ERROR)User " + str(user_id) +
                                 " can not be added to study " + str(
                study_id) + ", the study is not eligible to use this application type!")
            raise JutrackValidationError("Unaccepted status value detected")
        # add user to enrolled subjects
        if ('enrolled_subjects' in study_data and user_id in study_data['enrolled_subjects']) or ('enrolled-subjects' in study_data and user_id in study_data['enrolled-subjects']):
            print("tmp")#"user is already enrolled"
        if 'enrolled_subjects' in study_data:
            study_data['enrolled_subjects'].append(user_id)
            study_data['number_of_enrolled_subjects'] = calc_enrolled(study_data['enrolled_subjects'])
        else:
            study_data['enrolled-subjects'].append(user_id)
            study_data['number_of_enrolled_subjects'] = calc_enrolled(study_data['enrolled_subjects'])

        # Write to file and return the file name for logging
        with open(study_json, 'w', encoding='utf8') as s:
            json.dump(study_data, s, ensure_ascii=False, indent=4)
        os.chmod(study_json, 0o775)
        chgrp(study_json, gid)
        return target_file

# calculate the number_of_enrolled_subjects
def calc_enrolled(list_enrolled):
    res = 0
    for qr_id in list_enrolled:
        if qr_id.endswith("_1"):
            res = res + 1
        else:
            continue
    return res

# update an already existent user. If the user is somehow not found, add him
def update_user(data):
    study_id = data['studyId']
    user_id = data['username']
    status = data['status']

    file_name = user_folder + '/' + study_id + '_' + user_id + '.json'

    if os.path.isfile(file_name):
        with open(file_name, encoding='utf-8') as f:
            user_data = json.load(f)
    else:
        return add_user(data)

    for key in data:
        if key not in user_data:
            user_data[key] = data[key]

    # append status and if status is left from client or unknown add time_left for study leave
    user_data['status'] = status
    if status == 1:
        user_data['time_left'] = int(data['time_left'])
    elif status == 3 or status == 2:
        user_data['time_left'] = int(time.time() * 1000.0)
    elif status == 0:
        user_data['time_left'] = ''
        # Write to file and return the file name for logging
    with open(file_name, 'w', encoding='utf8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)

    return file_name


# update the ema state of a user
def update_ema(data):
    study_id = data['studyId']
    user_id = data['username']
    status_ema = data['status_ema']

    file_name = user_folder + '/' + study_id + '_' + user_id + '.json'

    if os.path.isfile(file_name):
        with open(file_name, encoding='utf-8') as f:
            user_data = json.load(f)
    else:
        return add_user(data)

    for key in data:
        if key not in user_data:
            user_data[key] = data[key]

    # append status and if status is left from client or unknown add time_left for study leave
    user_data['status_ema'] = status_ema
    user_data['time_joined_ema'] = int(user_data['time_joined_ema'])

    if status_ema == 1:
        user_data['time_left_ema'] = int(data['time_left_ema'])
    elif status_ema == 3 or status_ema == 2:
        user_data['time_left_ema'] = int(time.time() * 1000.0)
    elif status_ema == 0:
        user_data['time_left_ema'] = ''

    # Write to file and return the file name for logging
    with open(file_name, 'w', encoding='utf8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)

    return file_name


def get_remaining_days_in_study(study_id, user_id, app_type):
    iteration = int(user_id.split("_")[-1])
    user = '_'.join(user_id.split("_")[:-1])

    study_json = studies_folder + '/' + study_id + '/' + study_id + '.json'
    with open(study_json, encoding='utf-8') as s:
        study_data = json.load(s)

    total_duration = int(study_data["duration"])
    print("Total duration:" + str(total_duration))

    if iteration == 1:
        return total_duration, 0
    else:
        user_json = user_folder + '/' + study_id + '_' + user + '_' + str(iteration-1) + '.json'
        with open(user_json, encoding='utf-8') as s:
            user_data = json.load(s)

        if app_type == "ema" and "time_left_ema" in user_data:
            if int(user_data["time_left_ema"]) == 0:
                remaining_duration = total_duration - 1
            else:
                remaining_duration = total_duration - int((int(user_data["time_left_ema"]) / 1000.0 - int(user_data["time_joined_ema"]) / 1000.0) / 86400.0)
        elif app_type != "ema" and "time_left" in user_data:
            if int(user_data["time_left"]) == 0:
                remaining_duration = total_duration - 1
            else:
                remaining_duration = total_duration - int((int(user_data["time_left"]) / 1000.0 - int(user_data["time_joined"]) / 1000.0) / 86400.0)
        else:
            remaining_duration = total_duration

        print("Remaining: " + str(remaining_duration))
        if os.path.isfile(user_folder + '/' + study_id + '_' + user + '_1.json'):
            user_json = user_folder + '/' + study_id + '_' + user + '_1.json'
            with open(user_json, encoding='utf-8') as s:
                user_data = json.load(s)
            if app_type == "ema":
                return remaining_duration, user_data["time_joined_ema"]
            else:
                return remaining_duration, user_data["time_joined"]
        else:
            return remaining_duration, 0


def get_active_labeling(study_id):
    study_json = studies_folder + '/' + study_id + '/' + study_id + '.json'
    with open(study_json, encoding='utf-8') as s:
        study_data = json.load(s)
    if "active_labeling" in study_data:
        return study_data["active_labeling"]
    else:
        return 0


# write daily error summary
def write_output_message(message):
    # get date
    i = datetime.datetime.now()
    date = i.strftime("%Y-%m-%d")
    timestamp = i.strftime("%Y-%m-%dT%H-%M-%S")

    file_name = "/var/www/jutrack.inm7.de/service/daily_mail.txt"
    # write first line
    if not os.path.isfile(file_name):
        with open(file_name, 'w+') as f:
            f.write(date + '\n' + timestamp + ', ' + message + '\n')

        os.chmod(file_name, 0o664)
        chgrp(file_name, gid)
    else:
        with open(file_name, 'r') as f:
            first_line = f.readline().strip()
        if first_line == date:
            with open(file_name, 'a+') as f:
                f.write(timestamp + ', ' + message + '\n')
        else:
            with open(file_name, 'r+') as f:
                mail_text = """
                             {}
                             """.format("\n".join(f.readlines()))
            sender = 'www-data@jutrack.inm7.de'
            receivers = ['j.fischer@fz-juelich.de', 'j.dukart@fz-juelich.de', 'mehran.sahandi@yahoo.com']
            send_mail(sender, receivers, "JuTrack Daily Error Report", mail_text)
            with open(file_name, 'w') as f:
                f.write(date + '\n' + timestamp + ', ' + message + '\n')


# ----------------------------------------APPLICATION------------------------------------------------


# This method is called by the main endpoint
def application(environ, start_response):
    status = "200 OK"
    # We only accept POST-requests
    # environ['CONTENT_LENGTH'] = '10000000'
    # environ['CONTENT_TYPE'] = 'application/json; charset=utf-8'
    if environ['REQUEST_METHOD'] == 'POST':
        if 'HTTP_ACTION' in environ:
            action = environ['HTTP_ACTION']

            # read request body
            try:
                request_body = environ['wsgi.input'].read()
                print("Body:")
                print(request_body)
                # read passed MD5 value
                if 'HTTP_MD5' in environ:
                    md5 = environ['HTTP_MD5']
                else:
                    md5 = environ['HTTP_CONTENT-MD5']

                # calc_md5 = hashlib.md5(request_body).hexdigest()
                calc_md5 = hashlib.md5()
                calc_md5.update(request_body)

                # Check MD5 and content. If both is good perform actions
                # if is_md5_matching(md5, calc_md5.hexdigest()):
                try:
                    data = is_valid_data(request_body, action, 0)
                    output = perform_action(action, data)
                    if action == "admin_user":
                        data = output
                    else:
                        print(action)
                        print(output)
                        if output == "user exists":
                            status = '422 Existing Data Error'
                            output = {"message": "The user you tried to add already exists!"}
                        elif output == "user already enrolled":
                            status = '422 Existing Data Error'
                            output = {"message": "The user you tried to enroll has already been enrolled!"}
                except JutrackValidationError as e:
                    status = '409 Conflict'
                    output = {"message": e.message}
                except JutrackLeftUserError as e:
                    status = '403 Forbidden'
                    output = {"message": e.message}

                # else:
                print('expected MD5: ' + str(calc_md5.hexdigest()) + ', received MD5: ' + str(md5))
                # status = '500 Internal Server Error: There has been an MD5-MISMATCH!'
                # output = {"message": "MD5-MISMATCH: There has been a mismatch between
                # the uploaded data and the received data, upload aborted!"}
            except ValueError as e:
                status = '500 Internal Server Error: ValueError occured during JSON parsing!'
                output = {"message": "The wsgi service was not able to parse the json content."}

        else:
            status = '500 Internal Server Error: There has been a KEY MISSING!'
            print("Joker!")
            output = {"message": "MISSING-KEY: There was no action-attribute defined, upload aborted!"}
    else:
        print("Princess")
        status = '500 Internal Server Error: Wrong request type!'
        print("Request method:")
        print(environ['REQUEST_METHOD'])
        request_body = environ['wsgi.input'].read()
        print("Body:")
        print(request_body)
        output = {"message": "Expected POST-request!"}

    # aaaaaand respond to client
    if isinstance(output, str) and data is not None:
        if 'status' in data:
            output = data
            study_json = studies_folder + '/' + data['studyId'] + '/' + data['studyId'] + '.json'
            with open(study_json, encoding='utf-8') as json_file:
                study_content = json.load(json_file)
            if 'sensor-list' in study_content:
                output['sensors'] = study_content['sensor-list']
            if 'sensor_list' in study_content:
                output['sensors'] = study_content['sensor_list']
            if 'task_list' in study_content:
                output['task_list'] = study_content['task_list']
            if 'sensor_list_limited' in study_content:
                output['sensor_list_limited'] = study_content['sensor_list_limited']
            if 'duration' in study_content:
                output['study_duration'] = study_content['duration']
            if 'frequency' in study_content:
                output['freq'] = study_content['frequency']
        elif 'status_ema' in data:
            output = data
            study_json = studies_folder + '/' + data['studyId'] + '/' + data['studyId'] + '.json'
            with open(study_json, encoding='utf-8') as json_file:
                study_content = json.load(json_file)
            if 'sensor-list' in study_content:
                output['sensors'] = study_content['sensor-list']
            if 'sensor_list' in study_content:
                output['sensors'] = study_content['sensor_list']
            if 'task_list' in study_content:
                output['task_list'] = study_content['task_list']
            if 'sensor_list_limited' in study_content:
                output['sensor_list_limited'] = study_content['sensor_list_limited']
            if 'duration' in study_content:
                output['study_duration'] = study_content['duration']
            if 'survey' in study_content:
                output['survey'] = study_content['survey']
            if 'survey_ios' in study_content:
                output['survey_ios'] = study_content['survey_ios']
            if 'images' in study_content:
                output['images'] = study_content['images']
        else:
            output = data[0]

    start_response(status, [('Content-type', 'application/json')])
    output_dump = json.dumps(output)
    return [output_dump.encode('utf-8')]

# Logging WSGI middleware.

import threading
import pprint

class LoggingInstance:
    def __init__(self, start_response, oheaders, ocontent):
        self.__start_response = start_response
        self.__oheaders = oheaders
        self.__ocontent = ocontent

    def __call__(self, status, headers, *args):
        pprint.pprint((status, headers)+args, stream=self.__oheaders)
        self.__oheaders.close()

        self.__write = self.__start_response(status, headers, *args)
        return self.write

    def __iter__(self):
        return self

    def write(self, data):
        self.__ocontent.write(data)
        self.__ocontent.flush()
        return self.__write(data)

    def next(self):
        data = self.__iterable.next()
        self.__ocontent.write(data)
        self.__ocontent.flush()
        return data

    def close(self):
        if hasattr(self.__iterable, 'close'):
            self.__iterable.close()
        self.__ocontent.close()

    def link(self, iterable):
        self.__iterable = iter(iterable)

class LoggingMiddleware:

    def __init__(self, application, savedir):
        self.__application = application
        self.__savedir = savedir
        self.__lock = threading.Lock()
        self.__pid = os.getpid()
        self.__count = 0

    def __call__(self, environ, start_response):
        self.__lock.acquire()
        self.__count += 1
        count = self.__count
        self.__lock.release()

        key = "%s-%s-%s" % (time.time(), self.__pid, count)

        iheaders = os.path.join(self.__savedir, key + ".iheaders")
        iheaders_fp = open(iheaders, 'w')

        icontent = os.path.join(self.__savedir, key + ".icontent")
        icontent_fp = open(icontent, 'w+b')

        oheaders = os.path.join(self.__savedir, key + ".oheaders")
        oheaders_fp = open(oheaders, 'w')

        ocontent = os.path.join(self.__savedir, key + ".ocontent")
        ocontent_fp = open(ocontent, 'w+b')

        errors = environ['wsgi.errors']
        pprint.pprint(environ, stream=iheaders_fp)
        iheaders_fp.close()

        length = int(environ.get('CONTENT_LENGTH', '0'))
        input = environ['wsgi.input']
        while length != 0:
            data = input.read(min(4096, length))
            if data:
                icontent_fp.write(data)
                length -= len(data)
            else:
                length = 0
        icontent_fp.flush()
        icontent_fp.seek(0, os.SEEK_SET)
        environ['wsgi.input'] = icontent_fp

        iterable = LoggingInstance(start_response, oheaders_fp, ocontent_fp)
        iterable.link(self.__application(environ, iterable))
        return iterable

# application = LoggingMiddleware(application, '/mnt/jutrack_data/wsgi')
