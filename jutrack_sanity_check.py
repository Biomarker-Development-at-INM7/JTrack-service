import os
import json
import argparse

# define folder locations
from json import JSONDecodeError

storage_folder = '/mnt/jutrack_data'


def define_environment():
    parser = argparse.ArgumentParser(description="Description for my parser")
    parser.add_argument("-v", "--verbose", help="Print extended log to stdout", action='store_true')

    p = parser.parse_args()
    return p.verbose


# check json in folders recursively
def check_json_in_folder(folder_to_check, verbose):
    for data_folder, subfolders, files in os.walk(folder_to_check):
        for folder in subfolders:
            check_json_in_folder(os.path.join(data_folder, folder), verbose)

        for file in files:
            file_path = os.path.join(data_folder, file)
            if not file_path.endswith(".json"):
                print("ERROR: The file " + file_path + " is not a json file.")
            else:
                with open(file_path) as json_file:
                    try:
                        json.load(json_file)
                        if verbose:
                            print("NOTICE: The file " + file_path + " is a valid json file.")
                    except JSONDecodeError as e:
                        print("ERROR: The file " + file_path + " is not a valid json file. \tERROR-Message: " + e.msg)


if __name__ == "__main__":
    check_json_in_folder(storage_folder, define_environment())
