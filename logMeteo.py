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
from systemd import journal

""" blink the LED for a bit"""
def blinkLED():   
	blinkTime = 0.1
	for i in range(2):
		GPIO.output(pinID, GPIO.HIGH) # Turn on
		time.sleep(blinkTime) # Sleep
		GPIO.output(pinID, GPIO.LOW) # Turn off
		time.sleep(blinkTime) # Sleep

def errorLED():   
	blinkTime = 0.05
	for i in range(50):
		GPIO.output(pinID, GPIO.HIGH) # Turn on
		time.sleep(blinkTime) # Sleep 
		GPIO.output(pinID, GPIO.LOW) # Turn off
		time.sleep(blinkTime) # Sleep 


class logBufferClass():
	def __init__(self, debug=False):
		self.filename = "/var/log/logbuffer.tmp"
		if debug: self.filename="logbuffer.tmp"
		self.logData = []
		self.uploadDestination = "http://astrofarm.eu/upload"
		if debug: self.uploadDestination = "http://astrofarm.local/upload"
		self.load()
		
	def addEntry(self, logLine):
		self.logData.append(logLine)
		self.dump()
		return len(self.logData)
	
	def load(self):
		loadFile = open(self.filename, "rt")
		for line in loadFile:
			self.logData.append(line)
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
		
def getIRSky():
		readCommand = ["/home/pi/share/meteopi/readTsky"]
		result = subprocess.run(readCommand, stdout=subprocess.PIPE)
		Tsky = float(result.stdout.decode('utf-8'))
		return Tsky
	
def getIRAmbient():
		readCommand = ["/home/pi/share/meteopi/readTamb"]
		result = subprocess.run(readCommand, stdout=subprocess.PIPE)
		Tamb = float(result.stdout.decode('utf-8'))
		return Tamb


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Polls the BME 280 sensor for temperature, pressure and relative humidity.')
	parser.add_argument('-c', '--cadence', type=int, default=60, help='Cadence in seconds.' )
	parser.add_argument('-u', '--upload', type=int, default=300, help='Upload cadence in seconds.' )
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )

	args = parser.parse_args()

	debug = False
	GPIO.setwarnings(True) # Ignore warning for now
	GPIO.setmode(GPIO.BCM) # Use BCM pin numbering
	pinID = 16
	cadence = args.cadence
	GPIO.setup(pinID, GPIO.OUT, initial=GPIO.HIGH) #
	i2c = busio.I2C(board.SCL, board.SDA)
	bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address = 0x76)
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
	
	errorFlash = None
	while True:
		currentTime = datetime.datetime.now()
		try:
			# Get the CPU temperatures
			CPUtempFile = open(cpuTempPath, "rt")
			for line in CPUtempFile:
				cpuTemp = float(line.strip())
			CPUtempFile.close() 
			# Get the IR detector temperatures
			try: 
				IRsky = getIRSky()
				IRambient = getIRAmbient()
			except:
				IRsky = -100
				IRambient = -100
			logLine = "%s|%0.1f|%0.1f|%0.1f|%0.1f|%0.1f|%0.1f"%(str(currentTime), bme280.temperature, bme280.humidity, bme280.pressure, cpuTemp/1000, IRambient, IRsky)
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
					
			t = threading.Thread(name='non-block', target=blinkLED)
			t.start()
			logFile.write(logLine + "\n")
			if debug: print(logLine.strip())
			logFile.flush()
		except OSError as e:
			if debug: 
				print("Error connecting to sensor")
				print(e)
			errorFlash = threading.Thread(name='error flash', target=errorLED)
			errorFlash.start()

	
		time.sleep(cadence)
	
	
