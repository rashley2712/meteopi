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
		if debug: self.filename="/var/log/logbuffer.tmp"
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
			dumpFile.write(item.strip() + "\n")
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
			x.close()
		except Exception as e: 
			success = False
			print(e)
				
		return success

def information(message):
	global log
	if service: log.info(message)
	else: 
		print(message)
	return

		
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Polls the BME 280 sensor(s) for temperature, pressure and relative humidity.')
	parser.add_argument('-c', '--config', type=str, default='meteopi.cfg', help='Config file.' )
	parser.add_argument('-t', '--cadence', type=int, default=60, help='Cadence in seconds.' )
	parser.add_argument('-u', '--upload', type=int, default=300, help='Upload cadence in seconds.' )
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )
	args = parser.parse_args()	
	cadence = args.cadence
	upload = args.upload
	service = args.service
	debug = False

	configFile = open(args.config, 'rt')
	config = json.loads(configFile.read())
	print(config)
	
	if service:
		log = logging.getLogger('logmeteo.service')
		log.addHandler(journal.JournaldLogHandler())
		log.setLevel(logging.INFO)
		
	information("Started logging of the meteo devices with a cadence of %d seconds and upload cadence of %d seconds."%(cadence, upload))
		
	i2c = busio.I2C(board.SCL, board.SDA)
	bme280addresses = [config['exteriorsensoraddress'], config['domesensoraddress']] 
	if debug: information("Temperature sensors on I2C at %s"%str(bme280addresses))
	bme280 = []
	for address in bme280addresses:
		decAddress = int(address, 16)
		try:
			bme280.append(adafruit_bme280.Adafruit_BME280_I2C(i2c, address = decAddress))
		except:
			information("Sensor defective at address %s"%address)
			bme280.append("null")

	logBuffer = []
	lastUpload = datetime.datetime.now()
	uploadCadence = args.upload
	cpuTempPath = "/sys/class/thermal/thermal_zone0/temp"
	
	
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
		logLine="%s|"%(str(currentTime))
			
		# Get the hostname of this device
		hostname = socket.gethostname()
		logLine+="%s|"%hostname
			
		# Get the BME280 sensor temperatures
		for sensor, address in zip(bme280, bme280addresses):
			try:
				logLine+="%0.1f|%0.1f|%0.1f|"%(sensor.temperature, sensor.humidity, sensor.pressure)
			except:
				logLine+="-100|-100|-100|"			
		# Get the CPU temperature
		CPUtempFile = open(cpuTempPath, "rt")
		for line in CPUtempFile:
			cpuTemp = float(line.strip())/1000
		CPUtempFile.close() 
		logLine+="%0.1f|"%cpuTemp
		
		logBuffer.addEntry(logLine)
		timeSinceUpload = currentTime - lastUpload
		if debug: information("time since last upload %d seconds"%timeSinceUpload.seconds)
		if timeSinceUpload.seconds > uploadCadence: 
			lastUpload = datetime.datetime.now()
			if logBuffer.upload():
				information("Uploaded data successfully")
			else:
				information("Upload failed! Will try again in %d seconds"%uploadCadence)
			# If a sensor is not responding, try to initialise
			for index, b in enumerate(bme280):
				if b=="null":
					for address in bme280addresses:
						decAddress = int(address, 16)
						try:
							newDevice = adafruit_bme280.Adafruit_BME280_I2C(i2c, address = decAddress)
							bme280[index] = newDevice
						except:
							information("Sensor still defective at address %s"%address)
							
					
		logFile.write(logLine + "\n")
		information(logLine.strip())
		logFile.flush()
		
	
		time.sleep(cadence)
	
	
