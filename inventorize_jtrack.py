import os
import json
from datetime import datetime

def get_folder_info(root_folder):
    folder_info = {}

    for root, dirs, files in os.walk(root_folder):
        if not dirs:  # Only consider leaf directories
            folder_path = os.path.relpath(root, root_folder)
            if not any(folder.startswith('.') for folder in folder_path.split(os.sep)):
                folder_info[folder_path] = {}
                folder_info[folder_path]['number_of_files'] = len(files)
                if files:
                    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(root, f)))
                    folder_info[folder_path]['last_file_received'] = transform_time(os.path.getmtime(os.path.join(root,latest_file)))

    return folder_info


def transform_time(mytime):
    return datetime.fromtimestamp(int(mytime)).strftime('%Y-%m-%d %H:%M:%S')


def main():
    root_folder = '/mnt/jutrack_data/studies'
    output_file = '/var/www/jdash.inm7.de/service/folder_info.json'

    folder_info = get_folder_info(root_folder)

    with open(output_file, 'w') as f:
        json.dump(folder_info, f, indent=4)

if __name__ == "__main__":
    main()
