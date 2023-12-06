#!/bin/zsh

# Create a file in home dir
FILE=~/hello.txt
if [[ -f "$FILE" ]]; then
    echo "$FILE exists."
    exit 1
fi

touch ~/hello.txt

chown -R www-data /mnt/jutrack_data/junk/
chown -R www-data /mnt/jutrack_data/image_resources/
chown -R www-data /mnt/jutrack_data/users/
chown -R www-data /mnt/jutrack_data/archive/
chown -R www-data /mnt/jutrack_data/studies/

chmod -R 775 /mnt/jutrack_data/studies/
rm -rf ~/hello.txt
