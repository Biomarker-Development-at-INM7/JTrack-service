import os
import json
from datetime import datetime

def get_folder_info(root_folder):
    folder_info = {}
    transferred_dict = get_json_content("/var/www/jdash.inm7.de/service/folder_info.json")

    for root, dirs, files in os.walk(root_folder):
        if not dirs:  # Only consider leaf directories
            folder_path = os.path.relpath(root, root_folder)
            if not any(folder.startswith('.') for folder in folder_path.split(os.sep)):
                folder_info[folder_path] = {}
                if folder_path in transferred_dict:
                    folder_info[folder_path]['number_of_files'] = len(files) + transferred_dict[folder_path]["number_of_files"]
                    if "last_file_received" in transferred_dict[folder_path]:
                        folder_info[folder_path]['last_file_received'] = transferred_dict[folder_path]["last_file_received"]
                else:
                    folder_info[folder_path]['number_of_files'] = len(files)

                if files:
                    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(root, f)))
                    folder_info[folder_path]['last_file_received'] = transform_time(os.path.getmtime(os.path.join(root,latest_file)))

    return folder_info


def transform_time(mytime):
    return datetime.fromtimestamp(int(mytime)).strftime('%Y-%m-%d %H:%M:%S')


def get_json_content(file_path):
    with open(file_path) as json_file:
        try:
            content = json.load(json_file)
        except:
            print("ERROR: The file " + file_path + " is not a valid json file.")
            content = {}
        json_file.close()
    return content


def main():
    root_folder = '/mnt/jutrack_data/studies'
    output_file = '/var/www/jdash.inm7.de/service/folder_info.json'

    folder_info = get_folder_info(root_folder)

    with open(output_file, 'w') as f:
        json.dump(folder_info, f, indent=4)

if __name__ == "__main__":
    main()
