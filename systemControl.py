#!/usr/bin/env python
import board
import argparse
import time
import datetime
import threading
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import logging
from systemd import journal
import json, sys, os, requests
import skywatch
import threading
import signal

def debugOut(message):
	if debug: print(message)
	
def information(message):
	global log
	if service: log.info(message)
	else: 
		print(message)
	return


def signal_handler(sig, frame):
	print("Caught Ctrl-C")
	sys.exit(-1)


if __name__ == "__main__":
	signal.signal(signal.SIGINT, signal_handler)
	parser = argparse.ArgumentParser(description='Service to allow configuration and control via the web service.')
	parser.add_argument('-t', '--cadence', type=int, default=60, help='Starting cadence in seconds.' )
	parser.add_argument('-c', '--config', type=str, default='meteopi.cfg', help='Configuration file.' )
	parser.add_argument('--local', action="store_true", default=False, help='Run in ''local'' mode.' )
	parser.add_argument('--debug', action="store_true", default=False, help='Add degub information to the output.' )
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )
	args = parser.parse_args()

	debug = args.debug
	local = args.local
	service = args.service
	
	if service:
		log = logging.getLogger('skywatch.service')
		log.addHandler(journal.JournaldLogHandler())
		log.setLevel(logging.INFO)
		logLine = "Starting the skywatch system daemon."
		log.info(logLine)
	
	config = skywatch.config()
	config.load()
	if local: config.local = True
	
	# config.refresh()
	
	# Initiliase temperature sensors and fans
	domeSensor = skywatch.domeSensor()
	cpuSensor = skywatch.cpuSensor()
	exteriorSensor = skywatch.exteriorSensor()
	caseFan = skywatch.fanController(pin=config.caseFanGPIO)
	caseFan.triggerTemperature = 55
	caseFan.name = "case"
	domeFan = skywatch.fanController(pin=config.domeFanGPIO)
	domeFan.triggerTemperature = 35
	domeFan.name = "dome"
	cpuSensor.setFan(caseFan)
	domeSensor.setFan(domeFan)
	cpuSensor.startMonitor()
	domeSensor.startMonitor()
	
	n=0
	
	while True: 
		print("iteration %d"%n)
		print("Main loop... CPU: %.1f"%(cpuSensor.temperature))
		time.sleep(30)
		n+=1
		if n>5: break
		
	
	sys.exit()
	
	
	
	
