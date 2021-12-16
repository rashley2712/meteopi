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
import skywatch, config    # These are libraries that are part of meteopi
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
	print("Killing monitors")
	exteriorSensor.killMonitor()
	domeSensor.killMonitor()
	cpuSensor.killMonitor()
	#webber.killMonitor()
	logger.close()
	sys.exit()

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
		logLine = "Starting the skyWATCH system daemon."
		log.info(logLine)
	
	config = config.config(filename=args.config)
	config.load()
	if local: config.local = True
	print(config.getProperties())
	# config.refresh()
	

	sensors = []
	
	# Initialiase the log file
	logger = skywatch.logger()
	meteouploader = skywatch.meteoUploader(config = config.meteoUpload)
	#webber = skywatch.webController(baseURL = config.baseURL)
	#webber = skywatch.webController()
	# Initiliase temperature sensors and fans
	print("Dome sensor info:", config.domeTempSensor)
	if hasattr(config, "domeTempSensor"):
		if (config.domeTempSensor['type'] == "BME280"):
			domeSensor = skywatch.domeSensor2(config = config.domeTempSensor)
			sensors.append(domeSensor)
	if hasattr(config, "skySensor"):
		IRSensor = skywatch.IRSensor(config = config.skySensor)
		sensors.append(IRSensor)
	cpuSensor = skywatch.cpuSensor(config = config.cpuSensor)
	sensors.append(cpuSensor)

	
	# Attach the fans
	if config.caseFan!="none":
		caseFan = skywatch.fanController(config.caseFan)
		if config.caseFan['attachedTo'] == "cpuSensor":
			cpuSensor.attachFan(caseFan)
		if config.caseFan['attachedTo'] == "domeSensor":
			domeSensor.attachFan(caseFan)
	if config.domeFan!="none":
		domeFan = skywatch.fanController(config.domeFan)
		if config.domeFan['attachedTo'] == "cpuSensor":
			cpuSensor.attachFan(domeFan)
		if config.caseFan['attachedTo'] == "domeSensor":
			domeSensor.attachFan(domeFan)

	# Create the logging services
	for s in sensors:
		s.startMonitor()
		logger.attachSensor(s)
		meteouploader.attachSensor(s)


	#webber.attachSensor(cpuSensor)
	#webber.attachSensor(domeSensor)
	#webber.attachSensor(exteriorSensor)
	time.sleep(6)
	#webber.startMonitor()
	
	n=0
	logger.startMonitor()
	meteouploader.startMonitor()
	while True: 
		#information("Main control loop [%d]... CPU: %.1f Dome: %.1f Exterior: %.1f"%(n, domeSensor.temperature))
		time.sleep(180)
		n+=1
		
	
	sys.exit()
	
	
	
	
