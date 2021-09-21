#!/usr/bin/env python
import board
import requests
import argparse
import busio
import json
import time
import datetime
import adafruit_bme280
import threading
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import subprocess
import logging
import sys
from systemd import journal

""" blink the LED according to the pattern"""
def blinkLED():   
	while True:
		for status in pattern:
			if status[0]==1:
				GPIO.output(pinID, GPIO.HIGH) # Turn on
			else: 
				GPIO.output(pinID, GPIO.LOW) # Turn off
			time.sleep(status[1]) # Sleep
		
patterns = { "heartbeat" : [ [1, 0.02], [0, 7] ],
			 "error"     : [ [1, 0.01], [0, 0.09] ], 
			 "off"       : [ [0, 5] ], 
			 "on"		 : [ [1, 5] ]
			 }

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Controls the LED status light.')
	parser.add_argument('-t', '--cadence', type=int, default=5, help='Cadence in seconds.' )
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )
	parser.add_argument('-c', '--config', type=str, default='/home/pi/code/meteopi/meteopi.cfg', help='Config file.' )
	args = parser.parse_args()

	configFile = open(args.config, 'rt')
	config = json.loads(configFile.read())
	ledFile = config['ledFile']
	
	GPIO.setwarnings(True) # Ignore warning for now
	GPIO.setmode(GPIO.BCM) # Use BCM pin numbering
	pinID = config['ledPIN']
	cadence = args.cadence
	GPIO.setup(pinID, GPIO.OUT, initial=GPIO.LOW) #
	
	if args.service:
		log = logging.getLogger('LEDstatus.service')
		log.addHandler(journal.JournaldLogHandler())
		log.setLevel(logging.INFO)
		logLine = "Starting the LED status service with a cadence of %d seconds"%cadence
		log.info(logLine)

	
	try:
		statusFile = open(ledFile, "rt")
		line = statusFile.readline().strip()
		statusFile.close()
	except OSError as e:
		print("No",  ledFile, "file found.")
		sys.exit()
	
	try:
		pattern = patterns[line]
		t = threading.Thread(name='non-block', target=blinkLED)
		t.start()
		if args.service: log.info("Set LED to %s."%line)
		currentPattern = pattern
	except:
		print("Status %s unrecognised"%line)
		sys.exit()
	
	while True:
		time.sleep(cadence)
		try:
			statusFile = open(ledFile, "rt")
			line = statusFile.readline().strip()
			statusFile.close()
		except OSError as e:
			print("No",  ledFile, "file found.")
			
		try:
			pattern = patterns[line]
			if pattern==currentPattern: continue
			else:
				if args.service: log.info("Changed LED to %s."%line)
				currentPattern = pattern
		except:
			print("Status %s unrecognised"%line)
		
	
		
