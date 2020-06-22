#!/usr/bin/python3
import os
import json
import argparse
import glob
import time

# define folder locations
from json import JSONDecodeError

storage_folder = '/mnt/jutrack_data'


def define_environment():
    parser = argparse.ArgumentParser(description="Description for my parser")
    parser.add_argument("-v", "--verbose", help="Print extended log to stdout", action='store_true')

    p = parser.parse_args()
    return p.verbose


# check json in folders recursively
def get_files_in_folder(folder_to_check):
    files = []
    for name in glob.glob(folder_to_check + '/**/*.*', recursive=True):
        files.append(name)
    return files


def go_through_detected_files(files, verbose):
    for file in files:
        if not file.endswith(".json"):
            print("ERROR: The file " + file + " is not a json file.")
        else:
            content = None
            with open(file, "r") as json_file:
                try:
                    content = json.load(json_file)
                    if verbose:
                        print("NOTICE: The file " + file + " is a valid json file.")
                except JSONDecodeError as e:
                    print("ERROR: The file " + file + " is not a valid json file. \tERROR-Message: " + e.msg)
                json_file.close()
            if "users" in file and content is not None and 'status' in content and content['time_left'] == 0:
                with open(file, "w") as json_file:
                    if 'status' in content and (content['status'] == 3 or content['status'] == 2):
                        print("Timestamp set in file " + file)
                        content['time_left'] = int(time.time() * 1000.0)
                        json.dump(content, json_file, ensure_ascii=False, indent=4)
                json_file.close()


if __name__ == "__main__":
    file_paths = get_files_in_folder(storage_folder)
    #  Test-Environment:
    #  file_paths = get_files_in_folder("/Users/jfischer/GIT/JUGIT/JuTrackWSGI_Service/Test_dir/")
    go_through_detected_files(file_paths, define_environment())
    print("Check finished!")
