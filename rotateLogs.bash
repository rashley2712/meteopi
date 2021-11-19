#!/bin/bash
logPath=/var/log/
logName=skywatch.log
logTemp=temp.log
archivePath=/home/pi/share/logs/

echo `date`
sudo systemctl stop skywatch.service

sudo cp $logPath$logName $logPath$logTemp
today=$(date +'%Y%m%d')
archive=skywatch$today.log
echo Archiving log file to: $archivePath$archive
sudo mv $logPath$logTemp $archivePath$archive
sudo chown pi $archivePath$archive
gzip $archivePath$archive

sudo rm $logPath$logName
sudo touch $logPath$logName
sudo chown pi $logPath$logName
sudo systemctl start skywatch.service
