#!/usr/bin/env python
import board
import argparse
import time
import datetime
import threading
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import logging
from systemd import journal

def fanOn(pinID):
	GPIO.output(pinID, GPIO.HIGH) # Turn on

def fanOff(pinID):
	GPIO.output(pinID, GPIO.LOW) # Turn on



if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Monitors the CPU temp and turns the fan on if above a certain temperature..')
	parser.add_argument('-c', '--cadence', type=int, default=60, help='Cadence in seconds.' )
	parser.add_argument('-t', '--temp', type=int, default=55, help='Temperature to turn the fan on.' )
	args = parser.parse_args()

	debug = False
	GPIO.setwarnings(True) # Ignore warning for now
	GPIO.setmode(GPIO.BCM) # Use BCM pin numbering
	pinID = 26
	cadence = args.cadence
	GPIO.setup(pinID, GPIO.OUT, initial=GPIO.LOW) #
	cpuTempPath = "/sys/class/thermal/thermal_zone0/temp"
	logLine = "Fan will switch on at %d degrees.\n"%args.temp
	log = logging.getLogger('fanmonitor.service')
	log.addHandler(journal.JournaldLogHandler())
	log.setLevel(logging.INFO)
	log.info(logLine)
	
	fanStatus = False
	
	while True:
		try:
			CPUtempFile = open(cpuTempPath, "rt")
			for line in CPUtempFile:
				cpuTemp = float(line.strip())/1000
			CPUtempFile.close() 
			logLine = "CPU temp %0.1f"%(cpuTemp)
			log.info(logLine)
			print(logLine)
			if cpuTemp>args.temp: 
				if not fanStatus: 
					log.info("Turning fan on\n")
					fanOn(pinID)
					fanStatus = True
			if cpuTemp<args.temp-5: 
				if fanStatus:
					log.info("Turning fan off\n")
					fanOff(pinID)
					fanStatus = False
		except:
			log.error("Could not read the CPU temperature.\n")
			print("Could not read the CPU temperature.")
	
		time.sleep(cadence)
	
	
