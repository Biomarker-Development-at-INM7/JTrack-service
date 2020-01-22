import os
import time
from datetime import datetime
import csv
import glob
import json

# -------------------- CONFIGRATION -----------------------
storage_folder = '/mnt/jutrack_data'
studys_folder = storage_folder
users_folder = storage_folder + '/users'
devices_folder = ""

sensor_names = ['accelerometer', 'activity', 'application_usage', 'barometer', 'gravity_sensor', 'gyroscope',
                'location', 'magnetic_sensor', 'rotation_vector', 'linear_acceleration']


def prepare_csv(study_id):
    study_folder = storage_folder + '/' + study_id

    csv_data = []

    for users in os.listdir(study_folder):
        print(users)
        user_data = examine_user(study_folder, study_id, users)
        csv_data = csv_data + user_data

    write_csv(study_id, csv_data)


def examine_user(study_folder, study_id, users):
    user_data = []
    user_file = get_json_content(users_folder + "/" + study_id + "_" + users + ".json")
    user_status = user_file["status"]
    user_joined = user_file["time_joined"]/1000.0
    user_left = user_file["time_left"]/1000.0
    if user_left == "":
        time_in_study = time.time() - user_joined
    else:
        time_in_study = user_left - user_joined

    days_in_study = int(time_in_study/86400.0)

    user_folder = study_folder + '/' + users
    for devices in os.listdir(user_folder):
        row_data = examine_device(user_folder, users, devices, user_joined, days_in_study, user_status)
        user_data.append(row_data)

    return user_data


def examine_device(user_folder, users, devices, user_joined, days_in_study, user_status):
    device_folder = user_folder + '/' + devices
    device_data = {"subject_name": users, "device_id": devices, "date_registered": datetime.fromtimestamp(user_joined),
                   "time_in_study": str(days_in_study) + "days", "status_code": user_status}

    for sensors in os.listdir(device_folder):
        sensor_folder = device_folder + '/' + sensors
        sensor_files = get_files_in_folder(sensor_folder)
        number_of_files = len(sensor_files)

        last_file_path = sensor_files[number_of_files - 1]
        last_file_data = get_json_content(last_file_path)
        last_timestamp = last_file_data[len(last_file_data)-1]["timestamp"]/1000.0

        device_data[sensors + " n_batches"] = number_of_files
        last_date = datetime.fromtimestamp(last_timestamp)
        device_data[sensors + " last_time_received"] = str(last_date.year) + "-" + str(last_date.month) + "-" + \
            str(last_date.day) + " " + str(last_date.hour) + ":" + str(
            last_date.minute)

    return device_data


# write content
def write_csv(study_id, csv_data):
    with open(storage_folder + '/jutrack_dashboard_' + study_id + '.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        data_keys = ["subject_name", "device_id", "date_registered", "time_in_study", "status_code",
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
            writer.writerow([csv_row[data_keys[0]], csv_row[data_keys[1]], csv_row[data_keys[2]], csv_row[data_keys[3]],
                             csv_row[data_keys[4]], csv_row[data_keys[5]], csv_row[data_keys[6]], csv_row[data_keys[7]],
                             csv_row[data_keys[8]], csv_row[data_keys[9]], csv_row[data_keys[10]],
                             csv_row[data_keys[11]], csv_row[data_keys[12]], csv_row[data_keys[13]],
                             csv_row[data_keys[14]], csv_row[data_keys[15]], csv_row[data_keys[16]],
                             csv_row[data_keys[17]], csv_row[data_keys[18]], csv_row[data_keys[19]],
                             csv_row[data_keys[20]], csv_row[data_keys[21]], csv_row[data_keys[22]],
                             csv_row[data_keys[23]], csv_row[data_keys[24]]])


# check json in folders recursively
def get_files_in_folder(folder_to_check):
    all_files = []
    for name in sorted(glob.glob(folder_to_check + '/*.*', recursive=True)):
        all_files.append(name)
    return all_files


def get_json_content(file_path):
    content = None

    with open(file_path) as json_file:
        try:
            content = json.load(json_file)
        except:
            print("ERROR: The file " + file_path + " is not a valid json file.")
        json_file.close()

    return content


def invoke_csv_for_all_studys():
    for studys in os.listdir(storage_folder):
        if studys != "users":
            prepare_csv(studys)


if __name__ == "__main__":
    invoke_csv_for_all_studys()  # */30 * * * * /usr/bin/python /var/www/jutrack.inm7.de/service/jutrack_csv_cronjob.py
