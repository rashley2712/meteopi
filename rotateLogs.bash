#!/bin/bash
logPath=/var/log/
logName=skywatch.log
logTemp=temp.log
archivePath=/home/pi/share/logs/

sudo systemctl stop skywatch.service
cp $logPath$logName $logPath$logTemp
today=$(date +'%Y%m%d')
archive=skywatch$today.log
echo Archiving log file to: $archivePath$archive
mv $logPath$logTemp $archivePath$archive
gzip $archivePath$archive

rm $logPath$logName
touch $logPath$logName
sudo systemctl start skywatch.service
