#!/bin/zsh
# TODO: add publish(file, to="inm7") and drop(file) later on

# check studys for datalad status and save if necessary
cd /mnt/jutrack_data/studys
studys=($(ls -1))
for study in ${studys}
do
    echo ${study}
    cd /mnt/jutrack_data/studys/${study}
    # check datalad status of a study
    if [[ -d "/mnt/jutrack_data/studys/${study}/.datalad" ]] 
    then
    	echo "${study} is datalad dataset."
    else
      echo "${study} will become a datalad dataset."
      # create dataset
      datalad create --force -D "Add JuTrack dataset ${study}" -c text2git /mnt/jutrack_data/studys/${study}/
    fi
    # save study files
    echo "adding files to study ${study}"
    datalad save -m "adding files to study ${study}"
done

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
