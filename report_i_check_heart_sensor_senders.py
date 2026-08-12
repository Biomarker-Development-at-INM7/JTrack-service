#!/usr/bin/env python3
"""Report I_Check_Heart users with unwanted sensor directories.

This script is read-only. It inventories accelerometer and gyroscope directory
presence, matches device IDs against the non-EMA ``deviceid`` in user JSON
files, and writes OS/app/device information to CSV.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


STUDY_FOLDER_NAME = "I_Check_Heart"
SENSOR_NAMES = ("accelerometer", "gyroscope")
DEFAULT_STORAGE_ROOT = Path("/mnt/jtrack_data")
DEFAULT_OUTPUT_NAME = "i_check_heart_sensor_senders.csv"
LOCAL_TIMEZONE = ZoneInfo("Europe/Berlin")


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--storage-root",
        type=Path,
        default=Path(os.environ.get("JTRACK_STORAGE_FOLDER", DEFAULT_STORAGE_ROOT)),
        help="JTrack storage root (default: /mnt/jtrack_data).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Output CSV path. Defaults to "
            "/mnt/jtrack_data/i_check_heart_sensor_senders.csv."
        ),
    )
    parser.add_argument(
        "--joined-since",
        type=str,
        help=(
            "Include every enrolled user joined on or after this local date "
            "(YYYY-MM-DD), including users without either sensor folder."
        ),
    )
    return parser.parse_args()


def load_users(users_folder):
    """Index valid user JSON objects by their username."""
    users = {}
    errors = []

    for json_path in users_folder.glob("I_Check_Heart_*.json"):
        try:
            with json_path.open(encoding="utf-8") as json_file:
                data = json.load(json_file)
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"Could not read {json_path}: {error}")
            continue

        username = data.get("username")
        if not username:
            errors.append(f"Missing username in {json_path}")
            continue
        # Filename selection is authoritative. Keep studyId inconsistencies
        # visible in the report rather than silently dropping the user.
        data["_source_file"] = json_path.name
        users[username] = data

    return users, errors


def format_time_joined(value):
    """Convert the non-EMA millisecond timestamp to Europe/Berlin time."""
    if value in (None, ""):
        return ""
    try:
        return datetime.fromtimestamp(
            float(value) / 1000.0,
            tz=LOCAL_TIMEZONE,
        ).isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError, OverflowError):
        return "invalid: " + str(value)


def parse_joined_since(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(
            tzinfo=LOCAL_TIMEZONE
        ).timestamp() * 1000.0
    except ValueError as error:
        raise ValueError("--joined-since must use YYYY-MM-DD") from error


def build_row(username, device_id, user_data, accelerometer, gyroscope):
    device_matches = bool(user_data and str(user_data.get("deviceid", "")) == device_id)
    return {
        "username": username,
        "source_file": user_data.get("_source_file", "") if user_data else "",
        "study_id": user_data.get("studyId", "") if user_data else "",
        "device_id": device_id,
        "accelerometer_present": "yes" if accelerometer else "no",
        "gyroscope_present": "yes" if gyroscope else "no",
        "user_json_found": "yes" if user_data else "no",
        "non_ema_device_match": "yes" if device_matches else "no",
        "app_version": user_data.get("appVersion", "") if device_matches else "",
        "os_version": user_data.get("osVersion", "") if device_matches else "",
        "device_brand": user_data.get("deviceBrand", "") if device_matches else "",
        "device_model": user_data.get("deviceModel", "") if device_matches else "",
        "time_joined": format_time_joined(user_data.get("time_joined")) if device_matches else "",
    }


def build_rows(study_path, users, joined_since=None):
    rows = []
    reported_main_users = set()

    for user_path in sorted(study_path.iterdir()):
        if user_path.is_symlink() or not user_path.is_dir():
            continue

        user_data = users.get(user_path.name)
        expected_device_id = str(user_data.get("deviceid", "")) if user_data else ""
        if joined_since is not None:
            try:
                if float(user_data.get("time_joined", 0)) < joined_since:
                    continue
            except (AttributeError, TypeError, ValueError):
                continue

        for device_path in sorted(user_path.iterdir()):
            if device_path.is_symlink() or not device_path.is_dir():
                continue

            sensor_presence = {}
            for sensor_name in SENSOR_NAMES:
                sensor_path = device_path / sensor_name
                sensor_presence[sensor_name] = (
                    sensor_path.is_dir() and not sensor_path.is_symlink()
                )

            if not any(sensor_presence.values()):
                continue

            rows.append(build_row(
                user_path.name,
                device_path.name,
                user_data,
                sensor_presence["accelerometer"],
                sensor_presence["gyroscope"],
            ))
            if user_data and expected_device_id == device_path.name:
                reported_main_users.add(user_path.name)

    for username, user_data in users.items():
        if username in reported_main_users:
            continue
        if joined_since is not None:
            try:
                time_joined = float(user_data.get("time_joined", 0))
            except (TypeError, ValueError):
                continue
            if time_joined < joined_since:
                continue
        rows.append(build_row(
            username,
            str(user_data.get("deviceid", "")),
            user_data,
            False,
            False,
        ))

    return sorted(rows, key=lambda row: (row["time_joined"], row["username"], row["device_id"]))


def write_report(output_path, rows):
    fieldnames = [
        "username",
        "source_file",
        "study_id",
        "device_id",
        "accelerometer_present",
        "gyroscope_present",
        "user_json_found",
        "non_ema_device_match",
        "app_version",
        "os_version",
        "device_brand",
        "device_model",
        "time_joined",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f".{output_path.name}.{os.getpid()}.tmp")
    try:
        with temporary_path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main():
    arguments = parse_arguments()
    storage_root = arguments.storage_root.resolve()
    study_path = storage_root / "studies" / STUDY_FOLDER_NAME
    users_folder = storage_root / "users"
    output_path = arguments.output or storage_root / DEFAULT_OUTPUT_NAME

    if not study_path.is_dir() or study_path.is_symlink():
        print(f"Study directory not found or unsafe: {study_path}", file=sys.stderr)
        return 2
    if not users_folder.is_dir():
        print(f"Users directory not found: {users_folder}", file=sys.stderr)
        return 2

    users, errors = load_users(users_folder)
    try:
        joined_since = parse_joined_since(arguments.joined_since)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    rows = build_rows(study_path, users, joined_since)
    write_report(output_path, rows)

    for error in errors:
        print(error, file=sys.stderr)

    matched = sum(row["non_ema_device_match"] == "yes" for row in rows)
    print(
        f"Wrote {len(rows)} user/device rows ({matched} matched to non-EMA devices) "
        f"to {output_path}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

