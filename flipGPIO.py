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
	parser.add_argument('-c', '--cadence', type=int, default=5, help='Cadence in seconds.' )
	parser.add_argument('-p', '--pin', type=int, default=55, help='Pin number to flip.' )
	args = parser.parse_args()
	cadence = args.cadence
	debug = False
	GPIO.setwarnings(True) # Ignore warning for now
	GPIO.setmode(GPIO.BCM) # Use BCM pin numbering
	
	pinID = args.pin
	GPIO.setup(pinID, GPIO.OUT, initial=GPIO.HIGH) #
	
	while True:
		print("Setting pin #%d to high"%pinID)
		GPIO.output(pinID, GPIO.HIGH) #
		time.sleep(cadence)	
		print("Setting pin #%d to low"%pinID)
		GPIO.output(pinID, GPIO.LOW) #
		
		time.sleep(cadence)
	
	
