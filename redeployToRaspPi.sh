#!/bin/bash
echo ""
echo "Run this file with ubuntu bash only from the project folder!"
echo "This script copies all files from its folder that are not ignored in rsync-ignore.txt"
echo "Starting redeployment"
echo "Syncing files to server..."
rsync -avz --exclude-from='rsync-ignore.txt' -e 'ssh' "$PWD" pi@192.168.0.77:/home/pi
#echo "Connecting to server via ssh for service restart..."
#ssh pi@192.168.0.77 '
#docker container rm
#echo "Reloading daemon..."
#sudo systemctl daemon-reload
#echo "Completed! Ending ssh connection..."
#'
echo "Finished"
