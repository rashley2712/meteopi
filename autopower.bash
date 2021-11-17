#!/bin/bash
# /etc/init.d/GSMonoff
### BEGIN INIT INFO
# Provides:          powerGSM.py
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Starts GSM HAT
# Description:       Enable service provided by daemon.
### END INIT INFO
echo $1
sleep 10
case $1 in 
    start)
        echo powering on GSM
        /home/pi/code/meteopi/powerGSM.py
        sleep 40
        echo starting GPRS
        sudo pon >> /home/pi/GPRS.log 2>&1
        ;;
    stop)
        echo stopping GPRS
        sudo poff >> /home/pi/GPRS.log 2>&1
        echo powering off GSM
        /home/pi/code/meteopi/powerGSM.py
        ;;
    esac

