#!/bin/zsh

echo $(date -u) "Executing syncing script ..."

SOURCE_BASE_PATH="/mnt/jutrack_data/"
BASE_PATH="/data/project/JTrack/Studies/"
rsync_remote="jfischer@juseless.inm7.de:/data/project/JTrack/Studies/"
studies_directory="studies/"
user_directory="users/"
resources_folder="image_resources"
input_folder="inputs/"
output_folder="outputs/"
metadata_folder="metadata/"
code_folder="code/"
processed_folder="processed/"
raw_folder="raw/"
pipeline_folder="pipeline/"
processing_folder="processing/"
qc_folder="qc/"
download_folder="download/"
upload_folder="upload/"
image_folder="image/"
audio_folder="audio/"
other_folder="other/"
device_ios_folder="ios/"
device_android_folder="android/"
discard_directories="https: junk users archive studies image_resources .datalad .git .gitattributes .gitmodules"

# Check if a list contains a certain string
function containsDir(){
    echo "$1" | tr ' ' '\n' | grep -F -x -q "$2"
    # [[ $1 =~ (^|[[:space:]])$2($|[[:space:]]) ]] && exit(0) || exit(1)
}

# Create the bare structure on the remote
function make_directories_for_study_folder(){
    study=$1
    ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${input_folder}"
    ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${output_folder}"
    ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${metadata_folder}"
    ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${code_folder}"

    ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${code_folder}${pipeline_folder}"
    ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${code_folder}${processing_folder}"
    ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${code_folder}${qc_folder}"
    ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${metadata_folder}${download_folder}"
    ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${metadata_folder}${upload_folder}"

    audio_contents="${SOURCE_BASE_PATH}${resources_folder}/${upload_folder}${audio_folder}"
    if [[ "$audio_contents" == *"${study}"* ]]; then
        ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${metadata_folder}${upload_folder}${audio_folder}"
        ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${metadata_folder}${upload_folder}${image_folder}"
        ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${metadata_folder}${upload_folder}${other_folder}"
    fi
}

# Sync resources with remote
function copy_resources_for_study(){
    study=$1
    image_files_contents=($(ls -1r "${SOURCE_BASE_PATH}${resources_folder}"))
    for my_file in ${image_files_contents}
    do
        file_path="${SOURCE_BASE_PATH}${resources_folder}/${my_file}"
        if test -f "$file_path"; then
            if [[ "$my_file" == *"${study}"* ]]; then
                rsync -rO --checksum  "${file_path}" "${rsync_remote}${study}/${metadata_folder}${download_folder}${my_file}"
            fi
        fi
    done
}

# Sync sensor data
function copy_directories_of_sensor_folders(){
    study=$1
    user=$2
    unique_user=${user:0:-2}
    sensor=$3
    device_id=$4

    if ! containsDir ${discard_directories} ${sensor[0]}; then
        ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${input_folder}/${unique_user}/${raw_folder}${sensor}"
        #echo ${study} ${user} ${device_id} ${sensor} # LOGGING
        sensor_files=($(ls -1r "${SOURCE_BASE_PATH}${studies_directory}${study}/${user}/${device_id}/${sensor}"))
        rsync -rO --remove-source-files --progress --checksum "${SOURCE_BASE_PATH}${studies_directory}${study}/${user}/${device_id}/${sensor}/" "${rsync_remote}${study}/${input_folder}${unique_user}/${raw_folder}${sensor}"
    fi
}

# Create bare structure for a unique user
function make_directories_for_user_folder(){
    study=$1
    user=$2

    unique_user=${user:0:-2}

    ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${input_folder}${unique_user}"
    ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${input_folder}${unique_user}/${processed_folder}"
    ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}${study}/${input_folder}${unique_user}/${raw_folder}"
    #ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}$1/${input_folder}${unique_user}/${raw_folder}${device_ios_folder}"
    #ssh jfischer@juseless.inm7.de "mkdir -p ${BASE_PATH}$1/${input_folder}${unique_user}/${raw_folder}${device_android_folder}"
    device_id_folder=($(ls -1 "${SOURCE_BASE_PATH}${studies_directory}${study}/${user}/"))
    #device_brand_folder=device_android_folder
    key="deviceBrand"

    user_file_names=()
    cd "${SOURCE_BASE_PATH}${user_directory}"
    user_contents=($(ls -1r))
    for my_file in ${user_contents}
    do
        if [[ "$my_file" == *"${study}"* ]]; then
            user_file_names+=("${my_file}")
        fi
    done

    for device in ${device_id_folder}
    do
        if ! containsDir ${discard_directories} ${device}; then
            for my_file in ${user_file_names}
            do
                if [[ "${my_file}" == *"${user}"* ]]; then
                    rsync -O --checksum "${SOURCE_BASE_PATH}${user_directory}${my_file}" "${rsync_remote}${study}/${input_folder}${unique_user}/${user}.json"
                fi
            done
            sensor_folders=($(ls -1r "${SOURCE_BASE_PATH}${studies_directory}${study}/${user}/${device}"))
            for sensor_folder in ${sensor_folders}
            do
                copy_directories_of_sensor_folders ${study} ${user} ${sensor_folder} ${device}
            done
        fi
    done
    #copy_upload_folder_user_folder(study_folder,source_users_folder)
}

python3 /var/www/jdash.inm7.de/service/inventorize_jtrack.py

cd "${SOURCE_BASE_PATH}${studies_directory}"
studies=($(ls -1r))
for study in ${studies}
do
    if containsDir ${discard_directories} ${study}; then
        continue
    else
        is_test=0
        cd "${SOURCE_BASE_PATH}${studies_directory}${study}"
        input="${study}.json"
        while IFS= read -r line
        do
            if [[ "$line" == *"is_test"* ]] && [[ "$line" == *"true"* ]]; then
                echo "Skipping Study ${study}: It is a test-study!"
                is_test=1
                continue
            fi
        done < "$input"
        if [[ ${is_test} == 1 ]]; then
            continue
        fi
    fi
    echo ${study} # LOGGING
    cd "${SOURCE_BASE_PATH}${studies_directory}${study}"

    make_directories_for_study_folder ${study}
    copy_resources_for_study ${study}

    users=($(ls -1))
    for user in ${users}
    do
        if [[ ${user} == *".json"* ]]; then
            rsync -O --checksum ${user} "${rsync_remote}${study}/${metadata_folder}"
            continue
        fi
        #echo ${user}
        unique_user=${user:0:-2}
        #echo ${unique_user} # LOGGING
        make_directories_for_user_folder ${study} ${user}
        cd "${SOURCE_BASE_PATH}${studies_directory}${study}"
    done
done

# Sync CSV files
cd "${SOURCE_BASE_PATH}"
files=($(ls -1r))
for file in ${files}
do
    if [[ ${file} == *".csv"* ]]; then
        studyname=${file:18:-4}
        rsync -O --checksum ${file} "${rsync_remote}${studyname}/${metadata_folder}"
        continue
    fi
done

# Update Datalad
cd ~
echo $(date -u) "Executing datalad script on juseless ..."
ssh jfischer@juseless.inm7.de "/data/project/JTrack/Scripts/datalad_inventorize.zsh > /data/project/JTrack/Scripts/datalad_cron.log"
chmod 755 /var/www/jdash.inm7.de/service/folder_info.json
chgrp jtrack /var/www/jdash.inm7.de/service/folder_info.json
