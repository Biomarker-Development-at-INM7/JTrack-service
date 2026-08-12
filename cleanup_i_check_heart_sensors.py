#!/usr/bin/env python3

import argparse
import fcntl
import os
import sys
from pathlib import Path


STUDY_ID = "I_Check_Heart"
SENSOR_NAMES = ("accelerometer", "gyroscope")
DEFAULT_STORAGE_ROOT = Path("/mnt/jtrack_data")


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually remove data. Without this option, only report what would be removed.",
    )
    parser.add_argument(
        "--storage-root",
        type=Path,
        default=Path(os.environ.get("JTRACK_STORAGE_FOLDER", DEFAULT_STORAGE_ROOT)),
        help="JTrack storage root (default: /mnt/jtrack_data).",
    )
    return parser.parse_args()


def iter_sensor_directories(study_path):
    """Yield sensor directories at exactly user/device/sensor depth."""
    for user_path in study_path.iterdir():
        if user_path.is_symlink() or not user_path.is_dir():
            continue
        for device_path in user_path.iterdir():
            if device_path.is_symlink() or not device_path.is_dir():
                continue
            for sensor_name in SENSOR_NAMES:
                sensor_path = device_path / sensor_name
                if sensor_path.is_symlink() or not sensor_path.is_dir():
                    continue
                yield sensor_path


def entry_size(path):
    try:
        return path.lstat().st_size
    except FileNotFoundError:
        return 0


def clean_sensor_directory(sensor_path, delete):
    """Process all descendants without following directory symlinks."""
    files_removed = 0
    bytes_removed = 0
    errors = []

    for root, directories, files in os.walk(sensor_path, topdown=False, followlinks=False):
        root_path = Path(root)

        # os.walk puts symlinks to directories in `directories`; unlink them
        # rather than following or attempting to remove their targets.
        for name in files + directories:
            path = root_path / name
            if path.is_dir() and not path.is_symlink():
                if delete:
                    try:
                        path.rmdir()
                    except FileNotFoundError:
                        pass
                    except OSError as error:
                        errors.append((path, error))
                continue

            size = entry_size(path)
            if delete:
                try:
                    path.unlink()
                except FileNotFoundError:
                    continue
                except OSError as error:
                    errors.append((path, error))
                    continue
            files_removed += 1
            bytes_removed += size

    return files_removed, bytes_removed, errors


def format_bytes(byte_count):
    value = float(byte_count)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024


def main():
    arguments = parse_arguments()
    storage_root = arguments.storage_root.resolve()
    study_path = storage_root / "studies" / STUDY_ID

    if not study_path.is_dir() or study_path.is_symlink():
        print(f"Study directory not found or unsafe: {study_path}", file=sys.stderr)
        return 2

    lock_path = storage_root / ".i_check_heart_sensor_cleanup.lock"
    with lock_path.open("a") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another cleanup run is already active; exiting.")
            return 0

        total_files = 0
        total_bytes = 0
        all_errors = []
        sensor_directories = 0

        for sensor_path in iter_sensor_directories(study_path):
            sensor_directories += 1
            files, byte_count, errors = clean_sensor_directory(
                sensor_path, arguments.delete
            )
            total_files += files
            total_bytes += byte_count
            all_errors.extend(errors)

        action = "Removed" if arguments.delete else "Would remove"
        print(
            f"{action} {total_files} entries ({format_bytes(total_bytes)}) "
            f"from {sensor_directories} sensor directories."
        )

        for path, error in all_errors:
            print(f"Could not remove {path}: {error}", file=sys.stderr)

        return 1 if all_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
