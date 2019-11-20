#!/bin/bash
echo "Starting redeployment"
echo "Syncing files to server..."
rsync -avz --exclude-from='rsync-ignore.txt' -e 'ssh' "$PWD" pi@192.168.0.77:/home/pi
echo "Files synced!"
echo "Connecting to server via ssh..."
ssh pi@192.168.0.77 '
echo "Activating virtual environment and collecting staticfiles..."
cd ilmatar-http-wrapper/
source venv/bin/activate
python manage.py collectstatic --no-input
echo "Deactivating virtual environment"
deactivate
echo "Reloading daemon..."
sudo systemctl daemon-reload
echo "Restarting gunicorn..."
sudo systemctl restart gunicorn
echo "Completed! Ending ssh connection..."
'
echo "Finished"