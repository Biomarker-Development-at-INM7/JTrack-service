import os
import json
from datetime import datetime

ROOT_FOLDER = "/mnt/jutrack_data/studies"
OUTPUT_FILE = "/var/www/jdash.inm7.de/service/folder_info.json"


def get_json_content(file_path):
    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, encoding="utf-8") as json_file:
            return json.load(json_file)
    except Exception:
        print(f"ERROR: The file {file_path} is not a valid json file.")
        return {}


def transform_time(mytime):
    return datetime.fromtimestamp(int(mytime)).strftime("%Y-%m-%d %H:%M:%S")


def get_folder_info(root_folder):
    folder_info = {}
    transferred_dict = get_json_content(OUTPUT_FILE)

    for root, dirs, files in os.walk(root_folder):
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        if not dirs:
            folder_path = os.path.relpath(root, root_folder)

            if any(part.startswith(".") for part in folder_path.split(os.sep)):
                continue

            previous = transferred_dict.get(folder_path, {})
            previous_count = previous.get("number_of_files", 0)

            folder_info[folder_path] = {
                "number_of_files": len(files) + previous_count
            }

            if "last_file_received" in previous:
                folder_info[folder_path]["last_file_received"] = previous["last_file_received"]

            if files:
                latest_file = max(
                    files,
                    key=lambda f: os.path.getmtime(os.path.join(root, f))
                )
                folder_info[folder_path]["last_file_received"] = transform_time(
                    os.path.getmtime(os.path.join(root, latest_file))
                )

    return folder_info


def main():
    folder_info = get_folder_info(ROOT_FOLDER)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(folder_info, f, indent=4)


if __name__ == "__main__":
    main()
