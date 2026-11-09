#!/usr/bin/env python3
"""Create per-study CSV reports for sensor, permission, and pending-data status."""

import argparse
import csv
import grp
import json
import os
import pwd
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULT_STORAGE_ROOT = Path("/mnt/jtrack_data")
LOCAL_TIMEZONE = ZoneInfo("Europe/Berlin")

# Study sensor name -> UserDefaults stem used in sensorStates.
SENSOR_STATE_STEMS = {
    "accelerometer": "accelerometer",
    "activity": "activity",
    "application_usage": "appUsage",
    "barometer": "barometer",
    "gravity": "gravity",
    "gravity_sensor": "gravity",
    "gyroscope": "gyro",
    "health": "health",
    "linear_acceleration": "linearAcceleration",
    "location": "location",
    "lockUnlock": "lockstate",
    "magnetic_sensor": "magnet",
    "movement": "movement",
    "movement_derived": "movement",
    "pedometer": "pedometer",
    "rotation_vector": "rotationVector",
    "voice": "voice",
    "fitbit": "fitbit",
    "garmin": "garmin",
    "homeBeacon": "homeBeacon",
}

# Permissions required for useful background collection. An empty tuple means
# the platform exposes no separate permission relevant to that sensor.
SENSOR_PERMISSIONS = {
    "accelerometer": ("accelerometer",),
    "activity": ("activity",),
    "application_usage": ("appusage", "phoneusage", "wristusage"),
    "barometer": ("barometer",),
    "gravity": ("gravity",),
    "gravity_sensor": ("gravity",),
    "gyroscope": ("gyroscope",),
    "health": ("health",),
    "linear_acceleration": ("linear_acceleration",),
    "location": ("location", "locationBackground"),
    "pedometer": ("pedometer",),
    "rotation_vector": ("rotation_vector",),
    "voice": ("microphone",),
    "homeBeacon": ("bluetoothNearby",),
}

FIELDNAMES = [
    "study_id",
    "username",
    "device_id",
    "app_version",
    "os_version",
    "device_brand",
    "device_model",
    "subject_status",
    "currently_enrolled",
    "has_status_report",
    "expected_sensor",
    "expected_mode",
    "sensor_state_key",
    "actual_enabled",
    "sensor_match",
    "required_permissions",
    "permission_status",
    "permission_evidence",
    "granted_permissions",
    "denied_permissions",
    "missing_permissions",
    "unknown_permissions",
    "not_requested_permissions",
    "unreported_permissions",
    "sensor_pending_count",
    "total_pending_count",
    "permissions_checked_at",
    "pending_data_counted_at",
    "last_status_update",
    "user_json_updated_at",
    "wearable_device_state_status",
    "wearable_device_count",
    "wearable_device_ids",
    "wearable_models",
    "wearable_connection_states",
    "wearable_bluetooth_states",
    "wearable_last_connected_at",
    "wearable_last_sync_at",
    "wearable_last_send_at",
]


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--study",
        help="Only create the status CSV for this study ID.",
    )
    parser.add_argument(
        "--storage-root",
        type=Path,
        default=Path(os.environ.get("JTRACK_STORAGE_FOLDER", DEFAULT_STORAGE_ROOT)),
        help="JTrack storage root (default: /mnt/jtrack_data).",
    )
    parser.add_argument(
        "--output-folder",
        type=Path,
        help="CSV output folder (default: <storage-root>/study_status).",
    )
    return parser.parse_args()


def format_milliseconds(value):
    if value in (None, ""):
        return ""
    try:
        return datetime.fromtimestamp(
            float(value) / 1000.0,
            tz=LOCAL_TIMEZONE,
        ).isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError, OverflowError):
        return ""


def format_file_time(path):
    try:
        return datetime.fromtimestamp(
            path.stat().st_mtime,
            tz=LOCAL_TIMEZONE,
        ).isoformat(timespec="seconds")
    except OSError:
        return ""


def read_json(path):
    with path.open(encoding="utf-8") as json_file:
        return json.load(json_file)


def expected_sensors(study):
    # This matches jtrackService.wsgi: sensor_list overrides sensor-list.
    passive = study.get("sensor_list")
    if passive is None:
        passive = study.get("sensors", study.get("sensor-list", []))
    active = study.get("sensor_list_limited", [])
    wearables = study.get("wearables", [])

    result = []
    seen = set()
    for mode, values in (("passive", passive), ("active", active)):
        if not isinstance(values, list):
            continue
        for sensor in values:
            if not isinstance(sensor, str) or not sensor or (mode, sensor) in seen:
                continue
            seen.add((mode, sensor))
            result.append((sensor, mode))

    if isinstance(wearables, list):
        for wearable in wearables:
            if not isinstance(wearable, dict):
                continue
            sensor = wearable.get("sensorname")
            if not isinstance(sensor, str):
                continue
            sensor = sensor.strip().lower()
            if not sensor or ("wearable", sensor) in seen:
                continue
            seen.add(("wearable", sensor))
            result.append((sensor, "wearable"))
    return result


def load_users(users_folder):
    users_by_study = {}
    errors = []
    for path in users_folder.glob("*.json"):
        try:
            user = read_json(path)
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"Could not read {path}: {error}")
            continue
        study_id = user.get("studyId")
        username = user.get("username")
        if not isinstance(study_id, str) or not isinstance(username, str):
            continue
        user["_source_path"] = path
        users_by_study.setdefault(study_id, {})[username] = user
    return users_by_study, errors


def enrollment_set(study):
    enrolled = study.get("enrolled_subjects")
    if not isinstance(enrolled, list) or not enrolled:
        enrolled = study.get("enrolled-subjects")
    if isinstance(enrolled, list) and enrolled:
        return {value for value in enrolled if isinstance(value, str)}
    return None


def state_key(sensor, mode):
    stem = SENSOR_STATE_STEMS.get(sensor)
    if not stem:
        return ""
    if sensor == "homeBeacon":
        return "homeBeaconEnabled"
    suffix = "ActiveEnabled" if mode == "active" else "Enabled"
    return f"JTrack_{stem}{suffix}"


def pending_key(sensor):
    return f"{sensor}PendingData"


def bool_csv(value):
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def permission_names(permission_states, key):
    if not isinstance(permission_states, dict):
        return set()
    values = permission_states.get(key, [])
    if not isinstance(values, list):
        return set()
    return {value for value in values if isinstance(value, str)}


def permission_result(
    sensor,
    permission_states,
    mode="passive",
    active_data_measured=False,
    sensor_data_received=False,
    pending_value=None,
):
    required = SENSOR_PERMISSIONS.get(sensor, ())
    result = {
        "status": "not_required",
        "evidence": [],
        "granted": [],
        "denied": [],
        "unknown": [],
        "not_requested": [],
        "unreported": [],
    }
    if not required:
        return result

    has_pending_data = (
        isinstance(pending_value, (int, float))
        and not isinstance(pending_value, bool)
        and pending_value > 0
    )
    if sensor_data_received:
        result["evidence"].append("sensor_folder")
    if has_pending_data:
        result["evidence"].append("pending_data")

    has_permission_report = isinstance(permission_states, dict)
    if has_permission_report:
        granted = permission_names(permission_states, "permissionGranted")
        denied = permission_names(permission_states, "permissionDenied")
        unknown = permission_names(permission_states, "permissionUnknown")
        not_requested = permission_names(
            permission_states,
            "permissionNotRequested",
        )
    else:
        granted = set()
        denied = set()
        unknown = set()
        not_requested = set()

    result["granted"] = [name for name in required if name in granted]
    result["denied"] = [name for name in required if name in denied]
    result["unknown"] = [name for name in required if name in unknown]
    result["not_requested"] = [name for name in required if name in not_requested]
    result["unreported"] = [
        name
        for name in required
        if name not in granted
        and name not in denied
        and name not in unknown
        and name not in not_requested
    ]

    if any((result["granted"], result["denied"], result["unknown"], result["not_requested"])):
        result["evidence"].insert(0, "current_report")

    if result["denied"]:
        result["status"] = "revoked" if sensor_data_received or has_pending_data else "denied"
    elif len(result["granted"]) == len(required):
        result["status"] = "granted"
    elif result["unknown"]:
        result["status"] = "unknown"
    elif result["not_requested"]:
        result["status"] = "not_required_yet"
    elif sensor_data_received or has_pending_data:
        result["status"] = "previously_granted"
    elif mode == "active" and not active_data_measured:
        result["status"] = "not_required_yet"
    elif not has_permission_report:
        result["status"] = "no_report"
    else:
        result["status"] = "unverified"

    return result


def pending_total_for_sensors(pending_data, sensors):
    if not isinstance(pending_data, dict):
        return ""

    total = 0
    for key in {pending_key(sensor) for sensor, _mode in sensors}:
        value = pending_data.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            total += value
    return total


def subject_data_folder_exists(
    studies_folder,
    study_id,
    username,
    device_id,
    folder_name,
):
    """Return whether a named data folder exists for any subject device."""
    subject_folder = studies_folder / study_id / username
    if not subject_folder.is_dir():
        return False

    if isinstance(device_id, str) and device_id:
        if (subject_folder / device_id / folder_name).is_dir():
            return True

    try:
        return any(
            path.is_dir()
            for path in subject_folder.glob(f"*/{folder_name}")
        )
    except OSError:
        return False


def wearable_device_summary(user, sensor, mode):
    """Return aligned, semicolon-separated device details for a wearable row."""
    empty = {
        "wearable_device_state_status": "",
        "wearable_device_count": "",
        "wearable_device_ids": "",
        "wearable_models": "",
        "wearable_connection_states": "",
        "wearable_bluetooth_states": "",
        "wearable_last_connected_at": "",
        "wearable_last_sync_at": "",
        "wearable_last_send_at": "",
    }
    if mode != "wearable":
        return empty

    device_states = user.get("deviceStates")
    if not isinstance(device_states, dict) or sensor not in device_states:
        report_status = "not_reported"
        devices = []
    elif device_states[sensor] is None:
        report_status = "sdk_not_ready"
        devices = []
    elif isinstance(device_states[sensor], list):
        devices = device_states[sensor]
        report_status = "reported" if devices else "no_devices"
    else:
        report_status = "not_reported"
        devices = []
    devices = [device for device in devices if isinstance(device, dict)]

    def joined_value(key):
        return ";".join(
            str(device.get(key, "")) if device.get(key) is not None else ""
            for device in devices
        )

    def joined_time(key):
        return ";".join(format_milliseconds(device.get(key)) for device in devices)

    return {
        "wearable_device_state_status": report_status,
        "wearable_device_count": len(devices),
        "wearable_device_ids": joined_value("deviceId"),
        "wearable_models": joined_value("model"),
        "wearable_connection_states": joined_value("connectionState"),
        "wearable_bluetooth_states": joined_value("bluetoothState"),
        "wearable_last_connected_at": joined_time("lastConnectedAt"),
        "wearable_last_sync_at": joined_time("lastSyncAt"),
        "wearable_last_send_at": joined_time("lastSendAt"),
    }


def row_for_sensor(
    study_id,
    username,
    user,
    enrolled,
    sensor,
    mode,
    total_pending,
    active_data_measured=False,
    sensor_data_received=False,
):
    sensor_states = user.get("sensorStates")
    permissions = user.get("permissionStates")
    pending = user.get("pendingData")
    has_report = all(isinstance(value, dict) for value in (sensor_states, permissions, pending))

    key = state_key(sensor, mode)
    enabled = sensor_states.get(key) if isinstance(sensor_states, dict) and key else None
    pending_value = pending.get(pending_key(sensor)) if isinstance(pending, dict) else None
    permission = permission_result(
        sensor,
        permissions,
        mode,
        active_data_measured,
        sensor_data_received,
        pending_value,
    )

    permission_time = permissions.get("permissionsCheckedAt") if isinstance(permissions, dict) else None
    pending_time = pending.get("pendingDataCountedAt") if isinstance(pending, dict) else None
    timestamps = [value for value in (permission_time, pending_time) if isinstance(value, (int, float))]
    last_update = max(timestamps) if timestamps else None

    required_permissions = SENSOR_PERMISSIONS.get(sensor, ())
    source_path = user.get("_source_path")
    row = {
        "study_id": study_id,
        "username": username,
        "device_id": user.get("deviceid", ""),
        "app_version": user.get("appVersion", ""),
        "os_version": user.get("osVersion", ""),
        "device_brand": user.get("deviceBrand", ""),
        "device_model": user.get("deviceModel", ""),
        "subject_status": user.get("status", ""),
        "currently_enrolled": "yes" if enrolled else "no",
        "has_status_report": "yes" if has_report else "no",
        "expected_sensor": sensor,
        "expected_mode": mode,
        "sensor_state_key": key,
        "actual_enabled": bool_csv(enabled),
        "sensor_match": "yes" if enabled is True else ("no" if enabled is False else "unknown"),
        "required_permissions": ";".join(required_permissions),
        "permission_status": permission["status"],
        "permission_evidence": ";".join(permission["evidence"]),
        "granted_permissions": ";".join(permission["granted"]),
        "denied_permissions": ";".join(permission["denied"]),
        # Keep this legacy column for existing JDash consumers. It now only
        # contains explicitly denied permissions, never merely absent ones.
        "missing_permissions": ";".join(permission["denied"]),
        "unknown_permissions": ";".join(permission["unknown"]),
        "not_requested_permissions": ";".join(permission["not_requested"]),
        "unreported_permissions": ";".join(permission["unreported"]),
        "sensor_pending_count": pending_value if isinstance(pending_value, (int, float)) and not isinstance(pending_value, bool) else "",
        "total_pending_count": total_pending,
        "permissions_checked_at": format_milliseconds(permission_time),
        "pending_data_counted_at": format_milliseconds(pending_time),
        "last_status_update": format_milliseconds(last_update),
        "user_json_updated_at": format_file_time(source_path) if isinstance(source_path, Path) else "",
    }
    row.update(wearable_device_summary(user, sensor, mode))
    return row


def rows_for_study(study_id, study, users, studies_folder):
    sensors = expected_sensors(study)
    enrolled = enrollment_set(study)
    rows = []

    for username, user in sorted(users.items()):
        is_enrolled = enrolled is None or username in enrolled
        if not is_enrolled:
            continue
        total_pending = pending_total_for_sensors(user.get("pendingData"), sensors)
        device_id = user.get("deviceid")
        active_data_measured = subject_data_folder_exists(
            studies_folder,
            study_id,
            username,
            device_id,
            "active_labeling",
        )
        for sensor, mode in sensors:
            sensor_data_received = subject_data_folder_exists(
                studies_folder,
                study_id,
                username,
                device_id,
                sensor,
            )
            rows.append(row_for_sensor(
                study_id,
                username,
                user,
                is_enrolled,
                sensor,
                mode,
                total_pending,
                active_data_measured,
                sensor_data_received,
            ))
    return rows


def write_csv_atomic(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    identity = jtrack_identity()
    os.chmod(path.parent, 0o2775)
    if identity:
        os.chown(path.parent, identity[0], identity[1])

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as csv_file:
            temporary_path = Path(csv_file.name)
            writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        os.chmod(temporary_path, 0o664)
        if identity:
            os.chown(temporary_path, identity[0], identity[1])
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def jtrack_identity():
    """Return the jtrack UID/GID used for generated status artifacts."""
    try:
        return pwd.getpwnam("jtrack").pw_uid, grp.getgrnam("jtrack").gr_gid
    except KeyError as error:
        # Developer machines need not have the production service account.
        # On the production host, a root-run cron must not silently create
        # artifacts with the wrong ownership.
        if os.geteuid() == 0:
            raise RuntimeError(
                "The required jtrack user or group does not exist"
            ) from error
        return None


def discover_studies(studies_folder, requested_study):
    if requested_study:
        if Path(requested_study).name != requested_study:
            raise ValueError(f"Invalid study ID: {requested_study}")
        nested_json = studies_folder / requested_study / f"{requested_study}.json"
        if nested_json.is_file() and not nested_json.is_symlink():
            result = [(requested_study, nested_json)]
        else:
            result = []
    else:
        result = []
        for study_folder in studies_folder.iterdir():
            if study_folder.is_symlink() or not study_folder.is_dir():
                continue
            nested_json = study_folder / f"{study_folder.name}.json"
            if nested_json.is_file() and not nested_json.is_symlink():
                result.append((study_folder.name, nested_json))
        result.sort()

    if requested_study and not result:
        raise ValueError(f"Study does not exist: {requested_study}")
    return result


def main():
    arguments = parse_arguments()
    storage_root = arguments.storage_root.resolve()
    studies_folder = storage_root / "studies"
    users_folder = storage_root / "users"
    output_folder = (
        arguments.output_folder or storage_root / "study_status"
    ).resolve()

    if not studies_folder.is_dir() or not users_folder.is_dir():
        print(f"Invalid JTrack storage root: {storage_root}", file=sys.stderr)
        return 2

    users_by_study, errors = load_users(users_folder)
    for error in errors:
        print(error, file=sys.stderr)

    try:
        studies = discover_studies(studies_folder, arguments.study)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    failures = len(errors)
    for study_id, study_json in studies:
        try:
            study = read_json(study_json)
            rows = rows_for_study(
                study_id,
                study,
                users_by_study.get(study_id, {}),
                studies_folder,
            )
            output_path = output_folder / f"jtrack_{study_id}_status.csv"
            write_csv_atomic(output_path, rows)
            subjects = len({row["username"] for row in rows})
            print(f"Wrote {len(rows)} rows for {subjects} subjects to {output_path}")
        except (OSError, json.JSONDecodeError, ValueError) as error:
            failures += 1
            print(f"Could not create status CSV for {study_id}: {error}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
