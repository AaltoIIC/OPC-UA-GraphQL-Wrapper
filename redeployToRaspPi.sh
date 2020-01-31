#!/bin/bash
echo ""
echo "Run this file with ubuntu bash only from the project folder!"
echo "This script copies all files from its folder that are not ignored in rsync-ignore.txt"
echo "Syncing files to server..."
rsync -avz --exclude-from='rsync-ignore.txt' -e 'ssh' "$PWD" pi@192.168.0.77:/home/pi
echo "Finished"
