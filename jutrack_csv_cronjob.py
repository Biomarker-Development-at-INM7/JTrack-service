import os
import time
from datetime import datetime
import csv
import glob
import json
import pwd
import grp
import os
import numpy as np

uid = pwd.getpwnam("www-data").pw_uid
gid = grp.getgrnam("www-data").gr_gid

# -------------------- CONFIGRATION -----------------------
storage_folder = '/mnt/jutrack_data'
studys_folder = storage_folder + '/studies'
users_folder = storage_folder + '/users'
devices_folder = ""

sensor_names = ['accelerometer', 'activity', 'application_usage', 'barometer', 'gravity_sensor', 'gyroscope',
                'location', 'magnetic_sensor', 'rotation_vector', 'linear_acceleration']


def prepare_csv(study_id):
    study_folder = studys_folder + '/' + study_id

    csv_data = []

    for users in os.listdir(users_folder):
        if not users.startswith('.') and users.endswith('.json') and users.startswith(study_id):
            user_data = examine_user(study_folder, users)
            csv_data = csv_data + user_data

    write_csv(study_id, csv_data)


def examine_user(study_folder, users):
    user_data = []
    user_file = get_json_content(users_folder + "/" + users)
    user_id = user_file["username"]
    user_status = user_file["status"]
    user_joined = user_file["time_joined"] / 1000.0
    user_left = user_file["time_left"] / 1000.0
    if user_left == 0.0:
        time_in_study = time.time() - user_joined
    else:
        time_in_study = user_left - user_joined

    days_in_study = int(time_in_study / 86400.0)

    user_folder = study_folder + '/' + user_id
    if os.path.isdir(user_folder):
        for devices in os.listdir(user_folder):
            row_data = examine_device(user_folder, user_id, devices, user_joined, user_left, days_in_study, user_status,
                                      False)
            user_data.append(row_data)
    else:
        row_data = examine_device(user_folder, user_id, user_file["deviceid"], user_joined, user_left, days_in_study,
                                  user_status, True)
        user_data.append(row_data)

    return user_data


def examine_device(user_folder, users, devices, user_joined, user_left, days_in_study, user_status, new_user):
    if new_user:
        device_data = {"subject_name": users, "device_id": devices,
                       "date_registered": datetime.fromtimestamp(user_joined).strftime("%Y-%m-%d %H:%M:%S"), "date_left_study": "none",
                       "time_in_study": str(days_in_study) + " days", "status_code": user_status}
    else:
        device_folder = user_folder + '/' + devices
        if user_left == 0.0:
            device_data = {"subject_name": users, "device_id": devices,
                           "date_registered": datetime.fromtimestamp(user_joined).strftime("%Y-%m-%d %H:%M:%S"), "date_left_study": "none",
                           "time_in_study": str(days_in_study) + " days", "status_code": user_status}
        else:
            device_data = {"subject_name": users, "device_id": devices,
                           "date_registered": datetime.fromtimestamp(user_joined).strftime("%Y-%m-%d %H:%M:%S"),
                           "date_left_study": datetime.fromtimestamp(user_left).strftime("%Y-%m-%d %H:%M:%S"),
                           "time_in_study": str(days_in_study) + " days", "status_code": user_status}

        for sensors in os.listdir(device_folder):
            sensor_folder = device_folder + '/' + sensors
            sensor_files = get_files_in_folder(sensor_folder)
            number_of_files = len(sensor_files)

            file_name = sensor_files[number_of_files - 1]
            timestamp = file_name.split('_')[len(file_name.split('_'))-1].split('.')[0]
            if len(timestamp) == 1:
                timestamp = file_name.split('_')[len(file_name.split('_'))-2]
            elif len(timestamp) == 6:
                file_parts = file_name.split('_')
                date_send = file_parts[len(file_parts)-4]
                timestamp = date_send + "-" + file_parts[len(file_parts)-3] + "-" + file_parts[len(file_parts)-2]
            if 'T' in timestamp:
                date_send = timestamp.split('T')[0]
                time_send = timestamp.split('T')[1]
                timestamp = date_send + " " + time_send.replace('-', ':')
            #  print(timestamp)
            device_data[sensors + " n_batches"] = number_of_files
            device_data[sensors + " last_time_received"] = timestamp

    return device_data


def get_old_sensor_info(path):
    old_res = {}
    csv_content = []
    with open(path, newline='') as f:
        reader = csv.reader(f)
        csv_content = list(reader)
    for row in range(1, len(csv_content)):
        row_content = csv_content[row]
        tmp = {sensor_names[0] + " n_batches": row_content[6],
               sensor_names[1] + " n_batches": row_content[8],
               sensor_names[2] + " n_batches": row_content[10],
               sensor_names[3] + " n_batches": row_content[12],
               sensor_names[4] + " n_batches": row_content[14],
               sensor_names[5] + " n_batches": row_content[16],
               sensor_names[6] + " n_batches": row_content[18],
               sensor_names[7] + " n_batches": row_content[20],
               sensor_names[8] + " n_batches": row_content[22],
               sensor_names[9] + " n_batches": row_content[24],
               sensor_names[0] + " last_time_received": row_content[7],
               sensor_names[1] + " last_time_received": row_content[9],
               sensor_names[2] + " last_time_received": row_content[11],
               sensor_names[3] + " last_time_received": row_content[13],
               sensor_names[4] + " last_time_received": row_content[15],
               sensor_names[5] + " last_time_received": row_content[17],
               sensor_names[6] + " last_time_received": row_content[19],
               sensor_names[7] + " last_time_received": row_content[21],
               sensor_names[8] + " last_time_received": row_content[23],
               sensor_names[9] + " last_time_received": row_content[25]}
        old_res[row_content[0]] = tmp

    return old_res


def count_new_sensor_files(study_id, user_id, device_id, sensor_name, old_timestamp, old_n_batches):
    folder_name = studys_folder + "/" + study_id + "/" + user_id + "/" + device_id + "/" + sensor_name
    if not os.path.isdir(folder_name):
        return 0

    count = 0

    for file_name in get_files_in_folder(
            studys_folder + "/" + study_id + "/" + user_id + "/" + device_id + "/" + sensor_name):
        timestamp = file_name.split('_')[len(file_name.split('_'))-1].split('.')[0]
        if len(timestamp.split('T')) == 2:
            timestamp = timestamp.split('T')[0] + " " + timestamp.split('T')[1]
        if timestamp == old_timestamp and count < int(old_n_batches):
            count = int(old_n_batches)
        else:
            count = count+1

    return count


def overwrite_csv_nbatches(study_id, csv_row, old_content):
    if old_content is not None and csv_row["subject_name"] in old_content:
        csv_row[sensor_names[0] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"], csv_row["device_id"], sensor_names[0],
                                            old_content[csv_row["subject_name"]][
                                                sensor_names[0] + " last_time_received"],
                                            old_content[csv_row["subject_name"]][sensor_names[0] + " n_batches"])
        csv_row[sensor_names[1] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"], csv_row["device_id"], sensor_names[1],
                                            old_content[csv_row["subject_name"]][
                                                sensor_names[1] + " last_time_received"],
                                            old_content[csv_row["subject_name"]][sensor_names[1] + " n_batches"])
        csv_row[sensor_names[2] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"], csv_row["device_id"], sensor_names[2],
                                             old_content[csv_row["subject_name"]][
                                                 sensor_names[2] + " last_time_received"],
                                             old_content[csv_row["subject_name"]][sensor_names[2] + " n_batches"])
        csv_row[sensor_names[3] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"], csv_row["device_id"], sensor_names[3],
                                             old_content[csv_row["subject_name"]][
                                                 sensor_names[3] + " last_time_received"],
                                             old_content[csv_row["subject_name"]][sensor_names[3] + " n_batches"])
        csv_row[sensor_names[4] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"], csv_row["device_id"], sensor_names[4],
                                             old_content[csv_row["subject_name"]][
                                                 sensor_names[4] + " last_time_received"],
                                             old_content[csv_row["subject_name"]][sensor_names[4] + " n_batches"])
        csv_row[sensor_names[5] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"], csv_row["device_id"], sensor_names[5],
                                             old_content[csv_row["subject_name"]][
                                                 sensor_names[5] + " last_time_received"],
                                             old_content[csv_row["subject_name"]][sensor_names[5] + " n_batches"])
        csv_row[sensor_names[6] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"], csv_row["device_id"], sensor_names[6],
                                             old_content[csv_row["subject_name"]][
                                                 sensor_names[6] + " last_time_received"],
                                             old_content[csv_row["subject_name"]][sensor_names[6] + " n_batches"])
        csv_row[sensor_names[7] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"], csv_row["device_id"], sensor_names[7],
                                             old_content[csv_row["subject_name"]][
                                                 sensor_names[7] + " last_time_received"],
                                             old_content[csv_row["subject_name"]][sensor_names[7] + " n_batches"])
        csv_row[sensor_names[8] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"], csv_row["device_id"], sensor_names[8],
                                             old_content[csv_row["subject_name"]][
                                                 sensor_names[8] + " last_time_received"],
                                             old_content[csv_row["subject_name"]][sensor_names[8] + " n_batches"])
        csv_row[sensor_names[9] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"], csv_row["device_id"], sensor_names[9],
                                             old_content[csv_row["subject_name"]][
                                                 sensor_names[9] + " last_time_received"],
                                             old_content[csv_row["subject_name"]][sensor_names[9] + " n_batches"])

    return csv_row


# write content
def write_csv(study_id, csv_data):
    old_sensor_info = None
    if os.path.isfile(storage_folder + '/jutrack_dashboard_' + study_id + '.csv'):
        old_sensor_info = get_old_sensor_info(storage_folder + '/jutrack_dashboard_' + study_id + '.csv')
        os.remove(storage_folder + '/jutrack_dashboard_' + study_id + '.csv')
    with open(storage_folder + '/jutrack_dashboard_' + study_id + '.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        data_keys = ["subject_name", "device_id", "date_registered", "date_left_study", "time_in_study", "status_code",
                     sensor_names[0] + " n_batches", sensor_names[0] + " last_time_received",
                     sensor_names[1] + " n_batches", sensor_names[1] + " last_time_received",
                     sensor_names[2] + " n_batches", sensor_names[2] + " last_time_received",
                     sensor_names[3] + " n_batches", sensor_names[3] + " last_time_received",
                     sensor_names[4] + " n_batches", sensor_names[4] + " last_time_received",
                     sensor_names[5] + " n_batches", sensor_names[5] + " last_time_received",
                     sensor_names[6] + " n_batches", sensor_names[6] + " last_time_received",
                     sensor_names[7] + " n_batches", sensor_names[7] + " last_time_received",
                     sensor_names[8] + " n_batches", sensor_names[8] + " last_time_received",
                     sensor_names[9] + " n_batches", sensor_names[9] + " last_time_received"]

        writer.writerow(data_keys)
        for row_number in range(len(csv_data)):
            csv_row = csv_data[row_number]
            csv_row = overwrite_csv_nbatches(study_id, csv_row, old_sensor_info)
            writer.writerow([check_key(data_keys[0], csv_row), check_key(data_keys[1], csv_row),
                             check_key(data_keys[2], csv_row), check_key(data_keys[3], csv_row),
                             check_key(data_keys[4], csv_row), check_key(data_keys[5], csv_row),
                             check_key(data_keys[6], csv_row), check_key(data_keys[7], csv_row),
                             check_key(data_keys[8], csv_row), check_key(data_keys[9], csv_row),
                             check_key(data_keys[10], csv_row), check_key(data_keys[11], csv_row),
                             check_key(data_keys[12], csv_row), check_key(data_keys[13], csv_row),
                             check_key(data_keys[14], csv_row), check_key(data_keys[15], csv_row),
                             check_key(data_keys[16], csv_row), check_key(data_keys[17], csv_row),
                             check_key(data_keys[18], csv_row), check_key(data_keys[19], csv_row),
                             check_key(data_keys[20], csv_row), check_key(data_keys[21], csv_row),
                             check_key(data_keys[22], csv_row), check_key(data_keys[23], csv_row),
                             check_key(data_keys[24], csv_row), check_key(data_keys[25], csv_row)])

    if os.path.isfile(storage_folder + '/jutrack_dashboard_' + study_id + '.csv'):
        os.chown(storage_folder + '/jutrack_dashboard_' + study_id + '.csv', uid, gid)
        os.chmod(storage_folder + '/jutrack_dashboard_' + study_id + '.csv', 0o755)


def check_key(key, data):
    if key in data.keys():
        return data[key]
    else:
        return "none"


# check json in folders recursively
def get_files_in_folder(folder_to_check):
    all_files = []
    for name in sorted(glob.glob(folder_to_check + '/*.*', recursive=True)):
        all_files.append(name)
    return all_files


def get_json_content(file_path):
    with open(file_path) as json_file:
        try:
            content = json.load(json_file)
        except:
            print("ERROR: The file " + file_path + " is not a valid json file.")
            content = {}
        json_file.close()

    return content


def invoke_csv_for_all_studys():
    for studys in os.listdir(studys_folder):
        if os.path.isdir(studys_folder + '/' + studys):
            prepare_csv(studys)


if __name__ == "__main__":
    invoke_csv_for_all_studys()
    with open("/mnt/jutrack_data/jutrack_csv.log", "w") as log_file:
        log_file.write("Cron last successful on: " + str(datetime.now()) + "\n")
