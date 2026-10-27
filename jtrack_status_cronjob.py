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
    "missing_permissions",
    "unknown_permissions",
    "sensor_pending_count",
    "total_pending_count",
    "permissions_checked_at",
    "pending_data_counted_at",
    "last_status_update",
    "user_json_updated_at",
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


def permission_result(sensor, permission_states):
    required = SENSOR_PERMISSIONS.get(sensor, ())
    if not required:
        return "not_required", [], []
    if not isinstance(permission_states, dict):
        return "no_report", list(required), []

    granted = set(permission_states.get("permissionGranted", []))
    unknown = set(permission_states.get("permissionUnknown", []))
    unknown_required = [name for name in required if name in unknown]
    missing = [name for name in required if name not in granted and name not in unknown]

    if missing:
        return "missing", missing, unknown_required
    if unknown_required:
        return "unknown", [], unknown_required
    return "granted", [], []


def numeric_pending_values(pending_data):
    if not isinstance(pending_data, dict):
        return []
    values = []
    for key, value in pending_data.items():
        if key.endswith("PendingData") and isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(value)
    return values


def row_for_sensor(study_id, username, user, enrolled, sensor, mode):
    sensor_states = user.get("sensorStates")
    permissions = user.get("permissionStates")
    pending = user.get("pendingData")
    has_report = all(isinstance(value, dict) for value in (sensor_states, permissions, pending))

    key = state_key(sensor, mode)
    enabled = sensor_states.get(key) if isinstance(sensor_states, dict) and key else None
    permission_status, missing, unknown = permission_result(sensor, permissions)
    pending_value = pending.get(pending_key(sensor)) if isinstance(pending, dict) else None
    total_pending = sum(numeric_pending_values(pending)) if isinstance(pending, dict) else ""

    permission_time = permissions.get("permissionsCheckedAt") if isinstance(permissions, dict) else None
    pending_time = pending.get("pendingDataCountedAt") if isinstance(pending, dict) else None
    timestamps = [value for value in (permission_time, pending_time) if isinstance(value, (int, float))]
    last_update = max(timestamps) if timestamps else None

    required_permissions = SENSOR_PERMISSIONS.get(sensor, ())
    source_path = user.get("_source_path")
    return {
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
        "permission_status": permission_status,
        "missing_permissions": ";".join(missing),
        "unknown_permissions": ";".join(unknown),
        "sensor_pending_count": pending_value if isinstance(pending_value, (int, float)) and not isinstance(pending_value, bool) else "",
        "total_pending_count": total_pending,
        "permissions_checked_at": format_milliseconds(permission_time),
        "pending_data_counted_at": format_milliseconds(pending_time),
        "last_status_update": format_milliseconds(last_update),
        "user_json_updated_at": format_file_time(source_path) if isinstance(source_path, Path) else "",
    }


def rows_for_study(study_id, study, users):
    sensors = expected_sensors(study)
    enrolled = enrollment_set(study)
    rows = []

    for username, user in sorted(users.items()):
        is_enrolled = enrolled is None or username in enrolled
        if not is_enrolled:
            continue
        for sensor, mode in sensors:
            rows.append(row_for_sensor(
                study_id, username, user, is_enrolled, sensor, mode
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
