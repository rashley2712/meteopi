#!/usr/bin/env python
import board
import requests
import argparse
import busio
import time
import datetime
import adafruit_bme280
import threading
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import subprocess
import logging
import socket
import json
from systemd import journal

class logBufferClass():
	def __init__(self, debug=False):
		self.filename = "/var/log/logbuffer.tmp"
		if debug: self.filename="logbuffer.tmp"
		self.logData = []
		self.uploadDestination = "https://www.astrofarm.eu/upload"
		if debug: self.uploadDestination = "http://astrofarm.local:3001/upload"
		
	def addEntry(self, logLine):
		self.logData.append(logLine)
		self.dump()
		return len(self.logData)
	
	def load(self):
		loadFile = open(self.filename, "r")
		data = loadFile.readlines()
		for d in data:
			self.logData.append(d.strip())
		loadFile.close()
	
		
	def dump(self):
		dumpFile = open(self.filename, "wt")
		for item in self.logData:
			dumpFile.write(item + "\n")
		dumpFile.close()
		
	def clear(self):
		self.logData = []
		self.dump()
		
	def upload(self):
		print("Uploading logBuffer")
		success = False
		print("Uploading to ", self.uploadDestination)
		myobj = {'logData': self.logData}
		print(myobj)
		try: 
			x = requests.post(self.uploadDestination, data = myobj)
			print(x.text)
			if x.text == "SUCCESS": success = True
			self.clear()
		except Exception as e: 
			success = False
			print(e)
				
		return success
		
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Polls the BME 280 sensor(s) for temperature, pressure and relative humidity.')
	parser.add_argument('-c', '--config', type=str, default='meteopi.cfg', help='Config file.' )
	parser.add_argument('-t', '--cadence', type=int, default=60, help='Cadence in seconds.' )
	parser.add_argument('-u', '--upload', type=int, default=300, help='Upload cadence in seconds.' )
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )

	args = parser.parse_args()
	configFile = open(args.config, 'rt')
	config = json.loads(configFile.read())
	print(config)
	debug = True
	GPIO.setwarnings(True) # Ignore warning for now
	GPIO.setmode(GPIO.BCM) # Use BCM pin numbering
	pinID = 16
	cadence = args.cadence
	GPIO.setup(pinID, GPIO.OUT, initial=GPIO.HIGH) #
	i2c = busio.I2C(board.SCL, board.SDA)
	bme280addresses = [config['exteriorsensoraddress'], config['domesensoraddress']] 
	if debug: print("Temperature sensors on I2C at", bme280addresses)
	bme280 = []
	for address in bme280addresses:
		decAddress = int(address, 16)
		print("dec: ", decAddress)
		bme280.append(adafruit_bme280.Adafruit_BME280_I2C(i2c, address = 0x76))

	bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
	logBuffer = []
	lastUpload = datetime.datetime.now()
	uploadCadence = args.upload
	cpuTempPath = "/sys/class/thermal/thermal_zone0/temp"
	
	if args.service:
		log = logging.getLogger('logmeteo.service')
		log.addHandler(journal.JournaldLogHandler())
		log.setLevel(logging.INFO)
		logLine = "Starting the logmeteo service with a cadence of %d seconds"%cadence
		log.info(logLine)

	try: 
		logFile = open("/var/log/meteo.log", "at")
	except PermissionError:
		logFile = open("debug.log", "at")
		print("Not running as root, so can't write to /var/log. Creating a local 'debug.log' file.")
		debug = True
		
	logBuffer = logBufferClass(debug=debug)
	logBuffer.load()
	if debug: print("logbuffer ready.")

	while True:
		currentTime = datetime.datetime.now()
		try:
			logLine="%s|"%(str(currentTime))
			# Get the CPU temperatures
			CPUtempFile = open(cpuTempPath, "rt")
			for line in CPUtempFile:
				cpuTemp = float(line.strip())
			CPUtempFile.close() 
			# Get the hostname of this device
			hostname = socket.gethostname()
			
			
			# Get the BME280 sensor temperatures
			for sensor in bme280:
				temp = sensor.temperature
				print(temp)
			#logLine = "%s|%s|%0.1f|%0.1f|%0.1f|%0.1f|%0.1f|%0.1f"%(str(currentTime), hostname, bme280.temperature, bme280.humidity, bme280.pressure, cpuTemp/1000, IRambient, IRsky)
			logBuffer.addEntry(logLine)
			if args.service: log.info(logLine)
			timeSinceUpload = currentTime - lastUpload
			if debug: print("time since last upload %d seconds"%timeSinceUpload.seconds)
			if timeSinceUpload.seconds > uploadCadence: 
				if logBuffer.upload():
					lastUpload = datetime.datetime.now()
					if args.service: log.info("Uploaded data successfully")
				else:
					lastUpload = datetime.datetime.now()
					print("Upload failed! Will try again in %d seconds"%uploadCadence)
					if args.service: log.error("Failed to upload data. Will try again in %d seconds."%uploadCadence)
					
			logFile.write(logLine + "\n")
			if debug: print(logLine.strip())
			logFile.flush()
		except OSError as e:
			if debug: 
				print("Error connecting to sensor")
				print(e)
	
	
		time.sleep(cadence)
	
	
