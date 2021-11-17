#!/bin/bash

echo turning off GPRS
sudo poff
sleep 20
echo getting GPS fix
sleep 20
/home/pi/code/meteopi/gps.py -c /home/pi/code/meteopi/meteopi.cfg -n 3
echo restoring GPRS
sleep 20
sudo pon