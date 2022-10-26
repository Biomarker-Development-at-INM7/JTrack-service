#!/bin/zsh
# TODO: add publish(file, to="inm7") and drop(file) later on

# check studys for datalad status and save if necessary
# export GIT_CONFIG_SYSTEM=/var/www/jutrack.inm7.de/service/dataladgitconfig
echo $(date -u) "Executing script ..."

cd /mnt/jutrack_data/studies
studies=($(ls -1r))
for study in ${studies}
do
    echo ${study}
    cd /mnt/jutrack_data/studies/${study}
    # check datalad status of a study
    if [[ -d "/mnt/jutrack_data/studies/${study}/.datalad" ]] 
    then
        echo "${study} is datalad dataset."
    else
        echo "${study} will become a datalad dataset."
        # create dataset
        datalad create --force -D "Add JuTrack dataset ${study}" -c text2git /mnt/jutrack_data/studies/${study}/
        git config user.email "j.fischer@fz-juelich.de"
        git config user.name "Jona Fischer"
    fi

    if [ "$study" = "Social_iOS_SRKit" ]; then
        continue
    elif [ "$study" = "Social_iOS_SRKit2" ]; then
        echo "adding files to study ${study}"
        git config user.email "j.fischer@fz-juelich.de"
        git config user.name "Jona Fischer"
        users=($(ls -1))
        for user in ${users}
        do
            if [[ ${user} == *".json"* ]]; then
                continue
            fi
            cd /mnt/jutrack_data/studies/${study}/${user}
            devices=($(ls -1))
            for device in ${devices}
            do
                cd /mnt/jutrack_data/studies/${study}/${user}/${device}
                sensors=($(ls -1))
                for sensor in ${sensors}
                do
                    cd /mnt/jutrack_data/studies/${study}/${user}/${device}/${sensor}
                    pwd
                    files=($(ls -1))
                    for file in ${files}
                    do
                        file_state=($(datalad status ${file}))
                        if [[ ${file_state} =~ untracked.* ]]; then
                            datalad copy-file ${file} -d jutrack.inm7.de:/data/project/JTrack/Data/Studies_new/${study}/${user}/${device}/${sensor}/
                        fi
                    done
                    echo "Copied files to juseless"
                done
            done
        done
        continue
    elif [ "$study" = "Smart_SZ_MDD" ]; then
	continue
    fi
    # save study files
    echo "adding files to study ${study}"
    git config user.email "j.fischer@fz-juelich.de"
    git config user.name "Jona Fischer"
    datalad save -m "adding files to study ${study}"
done

echo "Adding studies and users ..."
cd /mnt/jutrack_data/studies
datalad save -m "Add new studies to dataset"

cd /mnt/jutrack_data/users
users=($(ls -1))

datalad_state=($(datalad status))
if [[ ${datalad_state} =~ untracked.* ]]; then
    echo "Saving added users to dataset at `/usr/bin/date +%Y_%m_%d-%H_%M`."
    datalad save -m "Saving added users to dataset at `/usr/bin/date +%Y_%m_%d-%H_%M`."
elif [[ ${datalad_state} =~ modified.* ]]; then
    echo "Updating existing users in dataset at `/usr/bin/date +%Y_%m_%d-%H_%M`."
    datalad save -m "Updating existing users in dataset at `/usr/bin/date +%Y_%m_%d-%H_%M`."
fi
