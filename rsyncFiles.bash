#!/bin/bash
echo Running an rsync to ASTROUBU20V.ing.iac.es
files=`find /home/skywatch/share/no-text -type f -mmin -15`
yesterday=`date -d "1 day ago" '+%Y%m%d' -u`
for f in $files 
do
	echo $f
	filename=$(basename "$f")
	dateString=${filename:0:8}
	echo File date: $dateString
	echo Yesterday was: $yesterday
	morningFlag=${filename:9:1}
	if [[ $morningFlag == "0" ]]; then
		echo this is a morning exposure
		rsync -av $f astrosw@astroubu20v.ing.iac.es:/data/allsky/skywatch/$yesterday
	else
		echo this is an evening exposure
		rsync -av $f astrosw@astroubu20v.ing.iac.es:/data/allsky/skywatch/$dateString
	fi
done
#find /home/skywatch/share/no-text -type f -mmin -15 | rsync -rcvh /home/skywatch/share/no-text astrosw@astroubu20v.ing.iac.es:/data/allsky/skywatch/ 
