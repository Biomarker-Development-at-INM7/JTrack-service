#!/usr/bin/env python3

import argparse
import os
import time
from datetime import datetime
import csv
import glob
import json
import pwd
import grp
import sys

try:
    uid = pwd.getpwnam("jtrack").pw_uid
except KeyError:
    uid = os.getuid()

try:
    gid = grp.getgrnam("jtrack").gr_gid
except KeyError:
    gid = os.getgid()

# -------------------- CONFIGURATION -----------------------
storage_folder = '/mnt/jtrack_data'
studys_folder = storage_folder + '/studies'
users_folder = storage_folder + '/users'
devices_folder = ""

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
    "garmin_SLEEP",
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
    if len(wearable_csv_data) > 0:
        write_wearables_csv(study_id, wearable_csv_data)


def normalize_device_brand(value):
    value = str(value or "").strip().lower()

    if any(name in value for name in ("ios", "iphone", "ipad", "apple")):
        return "iOS"

    if any(name in value for name in (
        "android", "samsung", "google", "pixel", "xiaomi",
        "redmi", "poco", "oneplus", "oppo", "vivo", "motorola",
        "huawei", "honor", "realme", "nokia", "sony", "fairphone",
    )):
        return "Android"

    return "unknown"


def latest_file_modification_time(file_paths):
    """Return the newest local batch mtime in the dashboard timestamp format."""
    timestamps = []
    for path in file_paths:
        try:
            timestamps.append(os.path.getmtime(path))
        except OSError:
            # A nightly move may remove a file while the CSV is being built.
            continue

    if not timestamps:
        return "none"

    return datetime.fromtimestamp(max(timestamps)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def newest_received_time(local_timestamp, inventoried_timestamp):
    """Return the newest valid dashboard timestamp from both data sources."""
    parsed = []
    for value in (local_timestamp, inventoried_timestamp):
        if not value or value == "none":
            continue
        try:
            parsed.append((datetime.strptime(value, "%Y-%m-%d %H:%M:%S"), value))
        except (TypeError, ValueError):
            continue

    if parsed:
        return max(parsed, key=lambda item: item[0])[1]
    if local_timestamp and local_timestamp != "none":
        return local_timestamp
    if inventoried_timestamp and inventoried_timestamp != "none":
        return inventoried_timestamp
    return "none"


def combined_batch_count(sensor_files, inventory_entry):
    """Combine local and inventoried batches without counting a file twice."""
    if not isinstance(inventory_entry, dict):
        return len(sensor_files)

    inventoried_count = inventory_entry.get("number_of_files", 0)
    if not isinstance(inventoried_count, int) or isinstance(inventoried_count, bool):
        inventoried_count = 0

    source_files = inventory_entry.get("source_files")
    if not isinstance(source_files, list):
        # Compatibility with the old inventory format, whose count represented
        # only files that had already been moved away.
        return inventoried_count + len(sensor_files)

    inventoried_names = {
        name for name in source_files if isinstance(name, str)
    }
    local_names = {os.path.basename(path) for path in sensor_files}
    return inventoried_count + len(local_names - inventoried_names)


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
            with open("/mnt/jtrack_data/jutrack_csv.log", "a") as log_file:
                log_file.write(
                    "INFO: Different time_format (String) in " + users_folder + "/" + users + " - " + user_file[
                        "time_joined"] + "\n")
        else:
            user_joined = user_file["time_joined"] / 1000.0
    if "time_joined_ema" in user_file:
        if isinstance(user_file["time_joined_ema"], str):
            with open("/mnt/jtrack_data/jutrack_csv.log", "a") as log_file:
                log_file.write(
                    "INFO: Different time_format (String) in " + users_folder + "/" + users + " - " + user_file[
                        "time_joined_ema"] + "\n")
        else:
            user_joined_ema = user_file["time_joined_ema"] / 1000.0

    user_left = 0.0
    user_left_ema = 0.0

    if "time_left" in user_file:
        if isinstance(user_file["time_left"], str):
            with open("/mnt/jtrack_data/jutrack_csv.log", "a") as log_file:
                log_file.write(
                    "INFO: Different time_format (String) in " + users_folder + "/" + users + " - " + user_file[
                        "time_left"] + "\n")
        else:
            user_left = user_file["time_left"] / 1000.0
    if "time_left_ema" in user_file:
        if isinstance(user_file["time_left_ema"], str):
            with open("/mnt/jtrack_data/jutrack_csv.log", "a") as log_file:
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

    device_brand = normalize_device_brand(user_file.get("deviceBrand"))
    device_brand_ema = normalize_device_brand(user_file.get("deviceBrand_ema"))

    user_folder = study_folder + '/' + user_id
    if os.path.isdir(user_folder):
        if len(os.listdir(user_folder)) == 1:
            devices = os.listdir(user_folder)[0]
            if "deviceid" in user_file and devices == user_file["deviceid"]:
                row = examine_device("main", user_folder, study_id, user_id, devices, device_brand, user_joined, user_left, days_in_study, user_status, False)
                user_data.append(row)
                if has_wearable_data(study_id, user_id, row["device_id"]):
                    wearable_data.append(
                        examine_wearable_device(row, study_id, user_id, row["device_id"])
                    )
                if "deviceid_ema" in user_file:
                    row = examine_device("ema", user_folder, study_id, user_id, user_file["deviceid_ema"], device_brand_ema, user_joined_ema, user_left_ema, days_in_study_ema, user_status_ema, True)
                    user_data.append(row)
                    if has_wearable_data(study_id, user_id, row["device_id"]):
                        wearable_data.append(
                            examine_wearable_device(row, study_id, user_id, row["device_id"])
                        )
            elif "deviceid_ema" in user_file and devices == user_file["deviceid_ema"]:
                row = examine_device("ema", user_folder, study_id, user_id, devices, device_brand_ema, user_joined_ema, user_left_ema, days_in_study_ema, user_status_ema, False)
                user_data.append(row)
                if has_wearable_data(study_id, user_id, row["device_id"]):
                    wearable_data.append(
                        examine_wearable_device(row, study_id, user_id, row["device_id"])
                    )
                if "deviceid" in user_file:
                    row = examine_device("main", user_folder, study_id, user_id, user_file["deviceid"], device_brand, user_joined, user_left, days_in_study, user_status, True)
                    user_data.append(row)
                    if has_wearable_data(study_id, user_id, row["device_id"]):
                        wearable_data.append(
                            examine_wearable_device(row, study_id, user_id, row["device_id"])
                        )
        else:
            for devices in os.listdir(user_folder):
                if "deviceid" in user_file and devices == user_file["deviceid"]:
                    row = examine_device("main", user_folder, study_id, user_id, devices, device_brand, user_joined, user_left, days_in_study, user_status, False)
                    user_data.append(row)
                    if has_wearable_data(study_id, user_id, row["device_id"]):
                        wearable_data.append(
                            examine_wearable_device(row, study_id, user_id, row["device_id"])
                        )
                elif "deviceid_ema" in user_file and devices == user_file["deviceid_ema"]:
                    row = examine_device("ema", user_folder, study_id, user_id, devices, device_brand_ema, user_joined_ema, user_left_ema, days_in_study_ema, user_status_ema, False)
                    user_data.append(row)
                    if has_wearable_data(study_id, user_id, row["device_id"]):
                        wearable_data.append(
                            examine_wearable_device(row, study_id, user_id, row["device_id"])
                        )
    else:
        if "deviceid" in user_file:
            row = examine_device("main", user_folder, study_id, user_id, user_file["deviceid"], device_brand, user_joined, user_left,
                                      days_in_study,
                                      user_status, True)
            user_data.append(row)
            if has_wearable_data(study_id, user_id, row["device_id"]):
                wearable_data.append(
                    examine_wearable_device(row, study_id, user_id, row["device_id"])
                )
        if "deviceid_ema" in user_file:
            row = examine_device("ema", user_folder, study_id, user_id, user_file["deviceid_ema"], device_brand_ema, user_joined_ema,
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
            inventory_key = studyid+"/"+users+"/"+devices+"/"+sensors
            transferred = transferred_dict.get(inventory_key, {})
            number_of_files = combined_batch_count(sensor_files, transferred)
            with open("/mnt/jtrack_data/jutrack_csv.log", "a") as log_file:
                log_file.write(str(users)+"\n")
                log_file.write(str(len(sensor_files))+"\n")
            timestamp = newest_received_time(
                latest_file_modification_time(sensor_files),
                transferred.get("last_file_received")
                if isinstance(transferred, dict) else None,
            )

            if number_of_files == 0:
                device_data[sensors + " n_batches"] = number_of_files
                device_data[sensors + " last_time_received"] = timestamp
                continue
            with open("/mnt/jtrack_data/jutrack_csv.log", "a") as log_file:
                log_file.write(str(number_of_files)+"\n")
            device_data[sensors + " n_batches"] = number_of_files
            if timestamp == "":
                timestamp = None
            device_data[sensors + " last_time_received"] = timestamp
    device_data["device_id"] = device_data["device_id"] if device_data["device_id"] else "none"

    brand = normalize_device_brand(device_brand)

    if brand == "unknown" and app_desc == "main":
        device_id = str(devices or "").strip()
        letters = [char for char in device_id if char.isalpha()]

        if letters and all(char.isupper() for char in letters):
            brand = "iOS"
        elif letters and all(char.islower() for char in letters):
            brand = "Android"

    device_data["device_brand"] = brand

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
        transferred = {}

        possible_transfer_keys = [
            f"{study_id}/{user_id}/{device_id}/{found_sensor}",
            f"{study_id}/{user_id}/{device_id}/{canonical_sensor}",
            f"{study_id}/{user_id}/{device_id}/{canonical_sensor.lower()}",
            f"{study_id}/{user_id}/{device_id}/{canonical_sensor.upper()}"
        ]

        for k in possible_transfer_keys:
            if k in transferred_dict:
                transferred = transferred_dict[k]
                break

        number_of_files = combined_batch_count(sensor_files, transferred)
        timestamp = newest_received_time(
            latest_file_modification_time(sensor_files),
            transferred.get("last_file_received")
            if isinstance(transferred, dict) else None,
        )

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

def get_old_sensor_info(path):
    old_res = {}
    csv_content = []
    with open(path, newline='') as f:
        reader = csv.reader(f)
        csv_content = list(reader)
    for row in range(1, len(csv_content)):
        row_content = csv_content[row]

        if len(row_content) < 31:
            with open("/mnt/jtrack_data/jutrack_csv.log", "a") as log_file:
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
    old_sensor_info = None
    if os.path.isfile(storage_folder + '/jutrack_dashboard_' + study_id + '.csv'):
        old_sensor_info = get_old_sensor_info(storage_folder + '/jutrack_dashboard_' + study_id + '.csv')
        os.remove(storage_folder + '/jutrack_dashboard_' + study_id + '.csv')
    with open(storage_folder + '/jutrack_dashboard_' + study_id + '.csv', 'w', newline='') as csvfile:
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
        for row_number in range(len(csv_data)):
            csv_row = csv_data[row_number]
            # csv_row = overwrite_csv_nbatches(study_id, csv_row, old_sensor_info)
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
                             check_key(data_keys[24], csv_row), check_key(data_keys[25], csv_row),
                             check_key(data_keys[26], csv_row), check_key(data_keys[27], csv_row),
                             check_key(data_keys[28], csv_row), check_key(data_keys[29], csv_row),
                             check_key(data_keys[30], csv_row), check_key(data_keys[31], csv_row),
                             check_key(data_keys[32], csv_row), check_key(data_keys[33], csv_row),
                             check_key(data_keys[34], csv_row), check_key(data_keys[35], csv_row)])

    if os.path.isfile(storage_folder + '/jutrack_dashboard_' + study_id + '.csv'):
        os.chown(storage_folder + '/jutrack_dashboard_' + study_id + '.csv', uid, gid)
        os.chmod(storage_folder + '/jutrack_dashboard_' + study_id + '.csv', 0o664)

def write_wearables_csv(study_id, csv_data):
    path = storage_folder + '/jtrack_wearables_' + study_id + '.csv'

    if os.path.isfile(path):
        os.remove(path)

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

    with open(path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(data_keys)

        for csv_row in csv_data:
            writer.writerow([check_key(k, csv_row) for k in data_keys])

    if os.path.isfile(path):
        os.chown(path, uid, gid)
        os.chmod(path, 0o664)

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


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Create JTrack dashboard CSV files."
    )
    parser.add_argument(
        "--study",
        help=(
            "Only create CSV files for this study. Without this option, "
            "all study directories are processed."
        ),
    )
    return parser.parse_args()


def invoke_csv_for_study(study_id):
    if not study_id or os.path.basename(study_id) != study_id:
        raise ValueError("Invalid study ID: " + str(study_id))

    study_folder = os.path.join(studys_folder, study_id)
    if not os.path.isdir(study_folder):
        raise ValueError("Study directory does not exist: " + study_folder)

    prepare_csv(study_id)


def main():
    arguments = parse_arguments()
    try:
        with open("/mnt/jtrack_data/jutrack_csv.log", "w") as log_file:
            log_file.write("Cron executed on: " + str(datetime.now()) + "\n")
            if arguments.study:
                log_file.write("Creating CSV for study: " + arguments.study + "\n")

        if arguments.study:
            invoke_csv_for_study(arguments.study)
        else:
            invoke_csv_for_all_studys()

        with open("/mnt/jtrack_data/jutrack_csv.log", "a") as log_file:
            log_file.write("Cron last successful on: " + str(datetime.now()) + "\n")
    except Exception:
        with open("/mnt/jtrack_data/jutrack_csv.log", "a") as log_file:
            log_file.write("An error occured during CSV creation at " + str(datetime.now()) + ":\n")
            log_file.write(str(sys.exc_info()))
            #log_file.write("An exception occurred:" +  type(e).__name__ + "–" + e.message)


if __name__ == "__main__":
    main()
