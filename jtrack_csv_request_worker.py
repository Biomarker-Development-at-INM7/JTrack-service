#!/usr/bin/env python3

import argparse
import os
import time
from datetime import datetime
import csv
import fcntl
import glob
import json
import grp
import sys
import tempfile

gid = grp.getgrnam("jtrack").gr_gid

# -------------------- CONFIGURATION -----------------------
storage_folder = os.environ.get('JTRACK_STORAGE_FOLDER', '/mnt/jtrack_data')
csv_output_folder = os.environ.get('JTRACK_CSV_OUTPUT_FOLDER', storage_folder)
studys_folder = storage_folder + '/studies'
users_folder = storage_folder + '/users'
devices_folder = ""
csv_request_folder = os.environ.get(
    'JTRACK_CSV_REQUEST_FOLDER',
    storage_folder + '/csv_requests'
)
csv_max_age_seconds = 30
log_path = os.environ.get('JTRACK_CSV_LOG_PATH', storage_folder + '/jutrack_csv.log')

sensor_names = ['accelerometer', 'activity', 'application_usage', 'barometer', 'gravity_sensor', 'gyroscope',
                'location', 'magnetic_sensor', 'rotation_vector',
                'linear_acceleration', 'ema', 'lockUnlock', 'voice', 'pedometer']

wearable_sensor_names = [
    "garmin_ACTIGRAPHY_1",
    "garmin_ACTIGRAPHY_2",
    "garmin_ACTIGRAPHY_3",
    "garmin_BBI",
    "garmin_CALORIES",
    "garmin_ENHANCED_BBI",
    "garmin_HEART_RATE",
    "garmin_HRV",
    "garmin_RESPIRATION",
    "garmin_SPO2",
    "garmin_STRESS",
    "garmin_STEPS",
    "garmin_WRIST_STATUS",
    "garmin_ZERO_CROSSING"
]


def prepare_csv(study_id):
    study_folder = studys_folder + '/' + study_id

    csv_data = []
    wearable_csv_data = []

    for users in os.listdir(users_folder):
        if not users.startswith('.') and users.endswith('.json') and users.startswith(study_id + "_" + study_id + "_"):
            user_data, wearable_data = examine_user(study_folder, study_id, users)
            csv_data += user_data
            wearable_csv_data += wearable_data

    write_csv(study_id, csv_data)
    write_wearables_csv(study_id, wearable_csv_data)


def examine_user(study_folder, study_id, users):
    user_data = []
    wearable_data = []
    user_file = get_json_content(users_folder + "/" + users)
    user_id = user_file["username"]
    user_status = 0
    user_status_ema = 0

    if "status" in user_file:
        user_status = user_file["status"]
    if "status_ema" in user_file:
        user_status_ema = user_file["status_ema"]

    user_joined = time.time()
    user_joined_ema = time.time()

    if "time_joined" in user_file:
        if isinstance(user_file["time_joined"], str):
            with open(log_path, "a") as log_file:
                log_file.write(
                    "INFO: Different time_format (String) in " + users_folder + "/" + users + " - " + user_file[
                        "time_joined"] + "\n")
        else:
            user_joined = user_file["time_joined"] / 1000.0
    if "time_joined_ema" in user_file:
        if isinstance(user_file["time_joined_ema"], str):
            with open(log_path, "a") as log_file:
                log_file.write(
                    "INFO: Different time_format (String) in " + users_folder + "/" + users + " - " + user_file[
                        "time_joined_ema"] + "\n")
        else:
            user_joined_ema = user_file["time_joined_ema"] / 1000.0

    user_left = 0.0
    user_left_ema = 0.0

    if "time_left" in user_file:
        if isinstance(user_file["time_left"], str):
            with open(log_path, "a") as log_file:
                log_file.write(
                    "INFO: Different time_format (String) in " + users_folder + "/" + users + " - " + user_file[
                        "time_left"] + "\n")
        else:
            user_left = user_file["time_left"] / 1000.0
    if "time_left_ema" in user_file:
        if isinstance(user_file["time_left_ema"], str):
            with open(log_path, "a") as log_file:
                log_file.write(
                    "INFO: Different time_format (String) in " + users_folder + "/" + users + " - " + user_file[
                        "time_left_ema"] + "\n")
        else:
            user_left_ema = user_file["time_left_ema"] / 1000.0

    if user_left == 0.0:
        time_in_study = time.time() - user_joined
    else:
        time_in_study = user_left - user_joined

    if user_left_ema == 0.0:
        time_in_study_ema = time.time() - user_joined_ema
    else:
        time_in_study_ema = user_left_ema - user_joined_ema

    days_in_study = int(time_in_study / 86400.0)
    days_in_study_ema = int(time_in_study_ema / 86400.0)

    user_folder = study_folder + '/' + user_id
    if os.path.isdir(user_folder):
        if len(os.listdir(user_folder)) == 1:
            devices = os.listdir(user_folder)[0]
            if "deviceid" in user_file and devices == user_file["deviceid"]:
                row = examine_device("main", user_folder, study_id, user_id, devices, user_file.get("deviceBrand", "unknown"), user_joined, user_left, days_in_study, user_status, False)
                user_data.append(row)
                if has_wearable_data(study_id, user_id, row["device_id"]):
                    wearable_data.append(
                        examine_wearable_device(row, study_id, user_id, row["device_id"])
                    )
                if "deviceid_ema" in user_file:
                    row = examine_device("ema", user_folder, study_id, user_id, user_file["deviceid_ema"], user_file.get("deviceBrand_ema", "unknown"), user_joined_ema, user_left_ema, days_in_study_ema, user_status_ema, True)
                    user_data.append(row)
                    if has_wearable_data(study_id, user_id, row["device_id"]):
                        wearable_data.append(
                            examine_wearable_device(row, study_id, user_id, row["device_id"])
                        )
            elif "deviceid_ema" in user_file and devices == user_file["deviceid_ema"]:
                row = examine_device("ema", user_folder, study_id, user_id, devices, user_file.get("deviceBrand_ema", "unknown"), user_joined_ema, user_left_ema, days_in_study_ema, user_status_ema, False)
                user_data.append(row)
                if has_wearable_data(study_id, user_id, row["device_id"]):
                    wearable_data.append(
                        examine_wearable_device(row, study_id, user_id, row["device_id"])
                    )
                if "deviceid" in user_file:
                    row = examine_device("main", user_folder, study_id, user_id, user_file["deviceid"], user_file.get("deviceBrand", "unknown"), user_joined, user_left, days_in_study, user_status, True)
                    user_data.append(row)
                    if has_wearable_data(study_id, user_id, row["device_id"]):
                        wearable_data.append(
                            examine_wearable_device(row, study_id, user_id, row["device_id"])
                        )
        else:
            for devices in os.listdir(user_folder):
                if "deviceid" in user_file and devices == user_file["deviceid"]:
                    row = examine_device("main", user_folder, study_id, user_id, devices, user_file.get("deviceBrand", "unknown"), user_joined, user_left, days_in_study, user_status, False)
                    user_data.append(row)
                    if has_wearable_data(study_id, user_id, row["device_id"]):
                        wearable_data.append(
                            examine_wearable_device(row, study_id, user_id, row["device_id"])
                        )
                elif "deviceid_ema" in user_file and devices == user_file["deviceid_ema"]:
                    row = examine_device("ema", user_folder, study_id, user_id, devices, user_file.get("deviceBrand_ema", "unknown"), user_joined_ema, user_left_ema, days_in_study_ema, user_status_ema, False)
                    user_data.append(row)
                    if has_wearable_data(study_id, user_id, row["device_id"]):
                        wearable_data.append(
                            examine_wearable_device(row, study_id, user_id, row["device_id"])
                        )
    else:
        if "deviceid" in user_file:
            row = examine_device("main", user_folder, study_id, user_id, user_file["deviceid"], user_file.get("deviceBrand", "unknown"), user_joined, user_left,
                                      days_in_study,
                                      user_status, True)
            user_data.append(row)
            if has_wearable_data(study_id, user_id, row["device_id"]):
                wearable_data.append(
                    examine_wearable_device(row, study_id, user_id, row["device_id"])
                )
        if "deviceid_ema" in user_file:
            row = examine_device("ema", user_folder, study_id, user_id, user_file["deviceid_ema"], user_file.get("deviceBrand_ema", "unknown"), user_joined_ema,
                                      user_left_ema, days_in_study_ema,
                                      user_status_ema, True)
            user_data.append(row)
            if has_wearable_data(study_id, user_id, row["device_id"]):
                wearable_data.append(
                    examine_wearable_device(row, study_id, user_id, row["device_id"])
                )
    return user_data, wearable_data


def examine_device(app_desc, user_folder, studyid, users, devices, device_brand, user_joined, user_left, days_in_study, user_status, new_user):
    if new_user:
        if user_left == 0.0:
            date_left = "none"
        else:
            date_left = datetime.fromtimestamp(user_left).strftime("%Y-%m-%d %H:%M:%S")

        device_data = {"app": app_desc, "subject_name": users, "device_id": devices, "device_brand": device_brand,
                       "date_registered": datetime.fromtimestamp(user_joined).strftime("%Y-%m-%d %H:%M:%S"),
                       "date_left_study": date_left,
                       "time_in_study": str(days_in_study) + " days", "status_code": user_status}
    else:
        device_folder = user_folder + '/' + devices
        if user_left == 0.0:
            device_data = {"app": app_desc, "subject_name": users, "device_id": devices, "device_brand": device_brand,
                           "date_registered": datetime.fromtimestamp(user_joined).strftime("%Y-%m-%d %H:%M:%S"),
                           "date_left_study": "none",
                           "time_in_study": str(days_in_study) + " days", "status_code": user_status}
        else:
            device_data = {"app": app_desc, "subject_name": users, "device_id": devices,
                           "date_registered": datetime.fromtimestamp(user_joined).strftime("%Y-%m-%d %H:%M:%S"),
                           "date_left_study": datetime.fromtimestamp(user_left).strftime("%Y-%m-%d %H:%M:%S"),
                           "time_in_study": str(days_in_study) + " days", "status_code": user_status}

        transferred_dict = get_json_content("/var/www/jdash.inm7.de/service/folder_info.json")

        for sensors in os.listdir(device_folder):
            sensor_folder = device_folder + '/' + sensors
            sensor_files = get_files_in_folder(sensor_folder)
            number_of_files = len(sensor_files)
            timestamp = "none"

            if studyid+"/"+users+"/"+devices+"/"+sensors in transferred_dict:
                number_of_files += transferred_dict[studyid+"/"+users+"/"+devices+"/"+sensors]["number_of_files"]
                if "last_file_received" in transferred_dict[studyid+"/"+users+"/"+devices+"/"+sensors]:
                    timestamp = transferred_dict[studyid+"/"+users+"/"+devices+"/"+sensors]["last_file_received"]

            if number_of_files == 0:
                device_data[sensors + " n_batches"] = number_of_files
                device_data[sensors + " last_time_received"] = "none"
                continue

            if len(sensor_files) > 0:
                file_name = sensor_files[len(sensor_files) - 1]
                timestamp = file_name.split('_')[len(file_name.split('_')) - 1].split('.')[0]
                if len(timestamp) == 1:
                    timestamp = file_name.split('_')[len(file_name.split('_')) - 2]
                elif len(timestamp) == 6:
                    file_parts = file_name.split('_')
                    date_send = file_parts[len(file_parts) - 4]
                    timestamp = date_send + "-" + file_parts[len(file_parts) - 3] + "-" + file_parts[len(file_parts) - 2]
                if 'T' in timestamp:
                    date_send = timestamp.split('T')[0]
                    time_send = timestamp.split('T')[1]
                    if len(date_send.split('-')) == 3 and len(date_send.split('-')[0]) == 2:
                        res = date_send.split('-')[2] + "-" + date_send.split('-')[1] + "-" + date_send.split('-')[0]
                        date_send = res
                    timestamp = date_send + " " + time_send.replace('-', ':')
                else:
                    timestamp = datetime.fromtimestamp(int(timestamp) / 1000).strftime('%Y-%m-%d %H:%M:%S')
            device_data[sensors + " n_batches"] = number_of_files
            if timestamp == "":
                timestamp = None
            device_data[sensors + " last_time_received"] = timestamp
    device_data["device_id"] = device_data["device_id"] if device_data["device_id"] else "none"
    return device_data

def examine_wearable_device(base_row, study_id, user_id, device_id):
    row = {
        "subject_name": user_id,
        "device_id": device_id,
        "date_registered": base_row.get("date_registered", "none"),
        "date_left_study": base_row.get("date_left_study", "none"),
        "time_in_study": base_row.get("time_in_study", "none"),
        "status_code": base_row.get("status_code", "none"),
        "app": base_row.get("app", "none")
    }

    device_folder = f"{studys_folder}/{study_id}/{user_id}/{device_id}"
    transferred_dict = get_json_content("/var/www/jdash.inm7.de/service/folder_info.json")

    for canonical_sensor in wearable_sensor_names:
        found_sensor = canonical_sensor
        sensor_folder = None

        for possible in [canonical_sensor, canonical_sensor.lower(), canonical_sensor.upper()]:
            candidate = f"{device_folder}/{possible}"
            if os.path.isdir(candidate):
                sensor_folder = candidate
                found_sensor = possible
                break

        sensor_files = get_files_in_folder(sensor_folder) if sensor_folder else []
        number_of_files = len(sensor_files)
        timestamp = "none"

        possible_transfer_keys = [
            f"{study_id}/{user_id}/{device_id}/{found_sensor}",
            f"{study_id}/{user_id}/{device_id}/{canonical_sensor}",
            f"{study_id}/{user_id}/{device_id}/{canonical_sensor.lower()}",
            f"{study_id}/{user_id}/{device_id}/{canonical_sensor.upper()}"
        ]

        for k in possible_transfer_keys:
            if k in transferred_dict:
                number_of_files += transferred_dict[k].get("number_of_files", 0)
                timestamp = transferred_dict[k].get("last_file_received", timestamp)
                break

        if sensor_files:
            timestamp = extract_timestamp_from_filename(sensor_files[-1])

        row[canonical_sensor + " n_batches"] = number_of_files
        row[canonical_sensor + " last_time_received"] = timestamp if timestamp else "none"

    return row

def has_wearable_data(study_id, user_id, device_id):
    device_folder = f"{studys_folder}/{study_id}/{user_id}/{device_id}"

    if not os.path.isdir(device_folder):
        return False

    for sensor in wearable_sensor_names:
        for possible in [sensor, sensor.lower(), sensor.upper()]:
            if os.path.isdir(f"{device_folder}/{possible}"):
                return True

    return False

def extract_timestamp_from_filename(file_name):
    timestamp = file_name.split('_')[-1].split('.')[0]

    if len(timestamp) == 1:
        timestamp = file_name.split('_')[-2]
    elif len(timestamp) == 6:
        file_parts = file_name.split('_')
        date_send = file_parts[-4]
        timestamp = date_send + "-" + file_parts[-3] + "-" + file_parts[-2]

    if 'T' in timestamp:
        date_send = timestamp.split('T')[0]
        time_send = timestamp.split('T')[1]

        if len(date_send.split('-')) == 3 and len(date_send.split('-')[0]) == 2:
            date_send = date_send.split('-')[2] + "-" + date_send.split('-')[1] + "-" + date_send.split('-')[0]

        return date_send + " " + time_send.replace('-', ':')

    try:
        return datetime.fromtimestamp(int(timestamp) / 1000).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp

def get_old_sensor_info(path):
    old_res = {}
    csv_content = []
    with open(path, newline='') as f:
        reader = csv.reader(f)
        csv_content = list(reader)
    for row in range(1, len(csv_content)):
        row_content = csv_content[row]

        if len(row_content) < 31:
            with open(log_path, "a") as log_file:
                log_file.write("ERROR: " + path + " is not working " + str(len(row_content)) + "\n")
        else:
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
                   sensor_names[10] + " n_batches": row_content[26],
                   sensor_names[11] + " n_batches": row_content[28],
                   sensor_names[12] + " n_batches": row_content[30],
                   sensor_names[13] + " n_batches": row_content[32],
                   sensor_names[0] + " last_time_received": row_content[7],
                   sensor_names[1] + " last_time_received": row_content[9],
                   sensor_names[2] + " last_time_received": row_content[11],
                   sensor_names[3] + " last_time_received": row_content[13],
                   sensor_names[4] + " last_time_received": row_content[15],
                   sensor_names[5] + " last_time_received": row_content[17],
                   sensor_names[6] + " last_time_received": row_content[19],
                   sensor_names[7] + " last_time_received": row_content[21],
                   sensor_names[8] + " last_time_received": row_content[23],
                   sensor_names[9] + " last_time_received": row_content[25],
                   sensor_names[10] + " last_time_received": row_content[27],
                   sensor_names[11] + " last_time_received": row_content[29],
                   sensor_names[12] + " last_time_received": row_content[31],
                   sensor_names[13] + " last_time_received": 0 if len(row_content) < 34 else row_content[33]}
            old_res[row_content[0]] = tmp

    return old_res


def count_new_sensor_files(study_id, user_id, device_id, sensor_name, old_timestamp, old_n_batches):
    folder_name = studys_folder + "/" + study_id + "/" + user_id + "/" + device_id + "/" + sensor_name
    if not os.path.isdir(folder_name):
        return 0

    count = 0

    for file_name in get_files_in_folder(
            studys_folder + "/" + study_id + "/" + user_id + "/" + device_id + "/" + sensor_name):
        timestamp = file_name.split('_')[len(file_name.split('_')) - 1].split('.')[0]
        if len(timestamp.split('T')) == 2:
            timestamp = timestamp.split('T')[0] + " " + timestamp.split('T')[1]
        if timestamp == old_timestamp and count < int(old_n_batches):
            count = int(old_n_batches)
        else:
            count = count + 1

    return count


def overwrite_csv_nbatches(study_id, csv_row, old_content):
    if old_content is not None and csv_row["subject_name"] in old_content:
        csv_row[sensor_names[0] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                         csv_row["device_id"], sensor_names[0],
                                                                         old_content[csv_row["subject_name"]][sensor_names[0] + " last_time_received"],
                                                                         old_content[csv_row["subject_name"]][sensor_names[0] + " n_batches"])
        csv_row[sensor_names[1] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                         csv_row["device_id"], sensor_names[1],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[1] + " last_time_received"],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[1] + " n_batches"])
        csv_row[sensor_names[2] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                         csv_row["device_id"], sensor_names[2],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[2] + " last_time_received"],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[2] + " n_batches"])
        csv_row[sensor_names[3] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                         csv_row["device_id"], sensor_names[3],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[3] + " last_time_received"],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[3] + " n_batches"])
        csv_row[sensor_names[4] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                         csv_row["device_id"], sensor_names[4],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[4] + " last_time_received"],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[4] + " n_batches"])
        csv_row[sensor_names[5] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                         csv_row["device_id"], sensor_names[5],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[5] + " last_time_received"],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[5] + " n_batches"])
        csv_row[sensor_names[6] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                         csv_row["device_id"], sensor_names[6],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[6] + " last_time_received"],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[6] + " n_batches"])
        csv_row[sensor_names[7] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                         csv_row["device_id"], sensor_names[7],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[7] + " last_time_received"],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[7] + " n_batches"])
        csv_row[sensor_names[8] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                         csv_row["device_id"], sensor_names[8],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[8] + " last_time_received"],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[8] + " n_batches"])
        csv_row[sensor_names[9] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                         csv_row["device_id"], sensor_names[9],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[9] + " last_time_received"],
                                                                         old_content[csv_row["subject_name"]][
                                                                             sensor_names[9] + " n_batches"])
        csv_row[sensor_names[10] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                          csv_row["device_id"], sensor_names[10],
                                                                          old_content[csv_row["subject_name"]]
                                                                          [sensor_names[10] + " last_time_received"],
                                                                          old_content[csv_row["subject_name"]]
                                                                          [sensor_names[10] + " n_batches"])
        csv_row[sensor_names[11] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                          csv_row["device_id"], sensor_names[11],
                                                                          old_content[csv_row["subject_name"]][
                                                                              sensor_names[11] + " last_time_received"],
                                                                          old_content[csv_row["subject_name"]][
                                                                              sensor_names[11] + " n_batches"])
        csv_row[sensor_names[12] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                          csv_row["device_id"], sensor_names[12],
                                                                          old_content[csv_row["subject_name"]][
                                                                              sensor_names[12] + " last_time_received"],
                                                                           old_content[csv_row["subject_name"]][
                                                                              sensor_names[12] + " n_batches"])
        csv_row[sensor_names[13] + " n_batches"] = count_new_sensor_files(study_id, csv_row["subject_name"],
                                                                          csv_row["device_id"], sensor_names[13],
                                                                          old_content[csv_row["subject_name"]][
                                                                              sensor_names[13] + " last_time_received"],
                                                                           old_content[csv_row["subject_name"]][
                                                                              sensor_names[13] + " n_batches"])
    return csv_row


# write content
def write_csv(study_id, csv_data):
    path = csv_output_folder + '/jutrack_dashboard_' + study_id + '.csv'
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
                mode='w', newline='', dir=csv_output_folder,
                prefix='.jutrack_dashboard_' + study_id + '.', suffix='.tmp',
                delete=False) as csvfile:
            temporary_path = csvfile.name
            writer = csv.writer(csvfile)
            data_keys = ["subject_name", "device_id", "device_brand", "date_registered", "date_left_study", "time_in_study", "status_code",
                         sensor_names[0] + " n_batches", sensor_names[0] + " last_time_received",
                         sensor_names[1] + " n_batches", sensor_names[1] + " last_time_received",
                         sensor_names[2] + " n_batches", sensor_names[2] + " last_time_received",
                         sensor_names[3] + " n_batches", sensor_names[3] + " last_time_received",
                         sensor_names[4] + " n_batches", sensor_names[4] + " last_time_received",
                         sensor_names[5] + " n_batches", sensor_names[5] + " last_time_received",
                         sensor_names[6] + " n_batches", sensor_names[6] + " last_time_received",
                         sensor_names[7] + " n_batches", sensor_names[7] + " last_time_received",
                         sensor_names[8] + " n_batches", sensor_names[8] + " last_time_received",
                         sensor_names[9] + " n_batches", sensor_names[9] + " last_time_received",
                         sensor_names[10] + " n_batches", sensor_names[10] + " last_time_received",
                         sensor_names[11] + " n_batches", sensor_names[11] + " last_time_received",
                         sensor_names[12] + " n_batches", sensor_names[12] + " last_time_received",
                         sensor_names[13] + " n_batches", sensor_names[13] + " last_time_received", "app"]

            writer.writerow(data_keys)
            for csv_row in csv_data:
                writer.writerow([check_key(key, csv_row) for key in data_keys])

        # Keep the executing user as owner and share the CSV with the jtrack group.
        os.chown(temporary_path, -1, gid)
        os.chmod(temporary_path, 0o664)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)

def write_wearables_csv(study_id, csv_data):
    path = csv_output_folder + '/jtrack_wearables_' + study_id + '.csv'
    temporary_path = None

    data_keys = [
        "subject_name",
        "device_id",
        "device_brand",
        "date_registered",
        "date_left_study",
        "time_in_study",
        "status_code",
        "app"
    ]

    for sensor in wearable_sensor_names:
        data_keys.append(sensor + " n_batches")
        data_keys.append(sensor + " last_time_received")

    try:
        with tempfile.NamedTemporaryFile(
                mode='w', newline='', dir=csv_output_folder,
                prefix='.jtrack_wearables_' + study_id + '.', suffix='.tmp',
                delete=False) as csvfile:
            temporary_path = csvfile.name
            writer = csv.writer(csvfile)
            writer.writerow(data_keys)

            for csv_row in csv_data:
                writer.writerow([check_key(k, csv_row) for k in data_keys])

        # Keep the executing user as owner and share the CSV with the jtrack group.
        os.chown(temporary_path, -1, gid)
        os.chmod(temporary_path, 0o664)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)

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


def csv_is_recent(study_id):
    path = csv_output_folder + '/jutrack_dashboard_' + study_id + '.csv'
    return (
        os.path.isfile(path)
        and time.time() - os.path.getmtime(path) <= csv_max_age_seconds
    )


def process_csv_request(request_name, log_file):
    if request_name.startswith('.') or os.path.basename(request_name) != request_name:
        return

    request_path = os.path.join(csv_request_folder, request_name)
    study_path = os.path.join(studys_folder, request_name)

    if not os.path.isfile(request_path):
        return

    # The worker only locks the marker; deletion is authorized by the directory.
    # Opening read-only also works when Django's umask removes group-write bits.
    with open(request_path, 'r') as request_file:
        try:
            fcntl.flock(request_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return

        if not os.path.isdir(study_path):
            log_file.write("Ignoring request for unknown study: " + request_name + "\n")
            os.unlink(request_path)
            return

        if csv_is_recent(request_name):
            log_file.write("Using recent CSV for study: " + request_name + "\n")
        else:
            log_file.write("Creating CSV for study: " + request_name + "\n")
            prepare_csv(request_name)

        # Removing the marker signals JDash that the final CSV is ready.
        os.unlink(request_path)


def process_csv_requests(log_file):
    os.makedirs(csv_request_folder, exist_ok=True)

    for request_name in sorted(os.listdir(csv_request_folder)):
        try:
            process_csv_request(request_name, log_file)
        except Exception:
            # Keep the request marker so the next cron run retries it.
            log_file.write("CSV request failed for " + request_name + ":\n")
            log_file.write(str(sys.exc_info()) + "\n")


def has_pending_csv_requests():
    os.makedirs(csv_request_folder, exist_ok=True)
    return any(
        not name.startswith('.')
        and os.path.isfile(os.path.join(csv_request_folder, name))
        for name in os.listdir(csv_request_folder)
    )


def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate requested JTrack dashboard CSV files.")
    parser.add_argument(
        '--study',
        help="Generate one study immediately instead of processing the request queue."
    )
    return parser.parse_args()


def run_single_study(study_id):
    if not study_id or os.path.basename(study_id) != study_id:
        raise ValueError("Invalid study ID: " + str(study_id))
    if not os.path.isdir(os.path.join(studys_folder, study_id)):
        raise ValueError("Unknown study ID: " + study_id)

    os.makedirs(csv_output_folder, exist_ok=True)
    started_at = time.monotonic()
    prepare_csv(study_id)
    elapsed = time.monotonic() - started_at
    print("Generated CSV for " + study_id + " in " + format(elapsed, '.3f') + " seconds")


def main():
    arguments = parse_arguments()

    if arguments.study:
        run_single_study(arguments.study)
        return

    # A frequent systemd timer can invoke the worker cheaply while idle.
    if not has_pending_csv_requests():
        return

    try:
        with open(log_path, "w") as log_file:
            log_file.write("Cron executed on: " + str(datetime.now()) + "\n")
            process_csv_requests(log_file)
            log_file.write("Cron last successful on: " + str(datetime.now()) + "\n")
    except Exception:
        with open(log_path, "a") as log_file:
            log_file.write("An error occured during CSV creation at " + str(datetime.now()) + ":\n")
            log_file.write(str(sys.exc_info()) + "\n")
            #log_file.write("An exception occurred:" +  type(e).__name__ + "–" + e.message)


if __name__ == "__main__":
    main()
