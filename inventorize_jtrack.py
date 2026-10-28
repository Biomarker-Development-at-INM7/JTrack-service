import argparse
import fcntl
import grp
import json
import os
import pwd
import tempfile
from datetime import datetime
from pathlib import Path

ROOT_FOLDER = Path("/mnt/jtrack_data/studies")
OUTPUT_FILE = Path("/var/www/jdash.inm7.de/service/folder_info.json")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Update the temporary JTrack sensor inventory."
    )
    parser.add_argument(
        "--base-inventory",
        type=Path,
        help=(
            "Optional permanent-storage inventory. Matching counts and "
            "timestamps replace the existing historical baseline before "
            "current temporary files are added."
        ),
    )
    return parser.parse_args()


def get_json_content(file_path):
    file_path = Path(file_path)
    if not file_path.exists():
        return {}

    with file_path.open(encoding="utf-8") as json_file:
        content = json.load(json_file)
    if not isinstance(content, dict):
        raise ValueError(f"Inventory is not a JSON object: {file_path}")
    return content


def format_time(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def parse_time(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").timestamp()
    except ValueError:
        return None


def newest_time(previous_value, candidate_timestamp):
    previous_timestamp = parse_time(previous_value)
    timestamps = [
        value
        for value in (previous_timestamp, candidate_timestamp)
        if value is not None
    ]
    return format_time(max(timestamps)) if timestamps else None


def current_files(sensor_folder, file_names):
    files = []
    for name in file_names:
        if name.startswith("."):
            continue
        path = sensor_folder / name
        try:
            stat_result = path.stat()
        except OSError:
            # The nightly move may remove a file while inventory is running.
            continue
        if path.is_file():
            files.append((name, stat_result.st_size, stat_result.st_mtime_ns))
    return files


def is_sensor_path(relative_path):
    return (
        len(relative_path.parts) == 4
        and not any(part.startswith(".") for part in relative_path.parts)
    )


def apply_base_inventory(previous_inventory, base_inventory):
    merged = dict(previous_inventory)
    for key, value in base_inventory.items():
        if (
            not isinstance(key, str)
            or not isinstance(value, dict)
            or not is_sensor_path(Path(key))
        ):
            continue

        count = value.get("number_of_files")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError(f"Invalid number_of_files for {key}: {count!r}")

        entry = {
            "number_of_files": count,
            # All files represented by the baseline are already permanent.
            # Current temporary files must therefore be added once.
            "source_files": [],
        }
        last_received = value.get("last_file_received")
        if last_received is not None:
            if parse_time(last_received) is None:
                raise ValueError(
                    f"Invalid last_file_received for {key}: {last_received!r}"
                )
            entry["last_file_received"] = last_received
        merged[key] = entry
    return merged


def get_folder_info(root_folder, previous_inventory=None):
    root_folder = Path(root_folder)
    if previous_inventory is None:
        previous_inventory = get_json_content(OUTPUT_FILE)

    # Keep valid historical sensor entries if an empty directory is removed.
    folder_info = {
        key: dict(value)
        for key, value in previous_inventory.items()
        if isinstance(key, str)
        and isinstance(value, dict)
        and is_sensor_path(Path(key))
    }
    for entry in folder_info.values():
        # A path not encountered in this run has no current source batch.
        entry["source_files"] = []
        entry.pop("source_signature", None)

    for root, dirs, file_names in os.walk(root_folder):
        dirs[:] = [name for name in dirs if not name.startswith(".")]
        sensor_folder = Path(root)
        relative_path = sensor_folder.relative_to(root_folder)

        if len(relative_path.parts) < 4:
            continue
        if not is_sensor_path(relative_path):
            dirs[:] = []
            continue

        # Sensor files are stored directly in study/user/device/sensor.
        dirs[:] = []
        key = str(relative_path)
        previous = previous_inventory.get(key, {})
        previous_count = previous.get("number_of_files", 0)
        if not isinstance(previous_count, int) or isinstance(previous_count, bool):
            previous_count = 0

        files = current_files(sensor_folder, file_names)
        current_names = {name for name, _, _ in files}
        previous_names = previous.get("source_files", [])
        if not isinstance(previous_names, list):
            previous_names = []
        previous_names = {
            name for name in previous_names if isinstance(name, str)
        }
        added_count = len(current_names - previous_names)

        if files:
            candidate_timestamp = max(mtime_ns for _, _, mtime_ns in files) / 1e9
        else:
            # Moving files away changes the folder mtime, but does not mean
            # that new sensor data was received.
            candidate_timestamp = None

        entry = {
            "number_of_files": previous_count + added_count,
            # Only the current source batch is retained. Historical filenames
            # are unnecessary once the nightly move empties the directory.
            "source_files": sorted(current_names),
        }
        last_received = newest_time(
            previous.get("last_file_received"), candidate_timestamp
        )
        if last_received is not None:
            entry["last_file_received"] = last_received
        folder_info[key] = entry

    return folder_info


def write_json_atomic(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        owner = (path.stat().st_uid, path.stat().st_gid)
    except OSError:
        try:
            owner = (
                pwd.getpwnam("jtrack").pw_uid,
                grp.getgrnam("jtrack").gr_gid,
            )
        except KeyError:
            owner = None

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(content, temporary_file, indent=4)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.chmod(temporary_path, 0o664)
        if owner is not None:
            try:
                os.chown(temporary_path, owner[0], owner[1])
            except PermissionError:
                # A non-root jtrack process already creates the file itself.
                pass
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def main():
    arguments = parse_arguments()
    lock_path = OUTPUT_FILE.with_suffix(OUTPUT_FILE.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        previous_inventory = get_json_content(OUTPUT_FILE)
        if arguments.base_inventory is not None:
            base_inventory = get_json_content(arguments.base_inventory.resolve())
            previous_inventory = apply_base_inventory(
                previous_inventory, base_inventory
            )
        folder_info = get_folder_info(ROOT_FOLDER, previous_inventory)
        write_json_atomic(OUTPUT_FILE, folder_info)


if __name__ == "__main__":
    main()
