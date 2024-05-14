#!/bin/bash
logPath=/var/log/
logName=skywatch.log
logTemp=temp.log
archivePath=/home/skywatch/share/logs/

echo `date`
sudo systemctl stop skywatch.service
sudo chmod a+w $logPath
sudo cp $logPath$logName $logPath$logTemp
today=$(date +'%Y%m%d')
archive=skywatch$today.log
echo Archiving log file to: $archivePath$archive
sudo mv $logPath$logTemp $archivePath$archive
sudo chown skywatch $archivePath$archive
gzip $archivePath$archive

sudo rm $logPath$logName
sudo touch $logPath$logName
sudo chown skywatch $logPath$logName
sudo systemctl start skywatch.service
