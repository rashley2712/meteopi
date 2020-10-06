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
	parser = argparse.ArgumentParser(description='Polls the BME 280 sensor for temperature, pressure and relative humidity.')
	parser.add_argument('-c', '--cadence', type=int, default=60, help='Cadence in seconds.' )
	parser.add_argument('-u', '--upload', type=int, default=300, help='Upload cadence in seconds.' )
	args = parser.parse_args()

	debug = False
	GPIO.setwarnings(True) # Ignore warning for now
	GPIO.setmode(GPIO.BCM) # Use BCM pin numbering
	pinID = 16
	cadence = args.cadence
	GPIO.setup(pinID, GPIO.OUT, initial=GPIO.LOW) #
	i2c = busio.I2C(board.SCL, board.SDA)
	bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
	logBuffer = []
	lastUpload = datetime.datetime.now()
	uploadCadence = args.upload
	cpuTempPath = "/sys/class/thermal/thermal_zone0/temp"
	

	try: 
		logFile = open("/var/log/meteo.log", "at")
	except PermissionError:
		logFile = open("debug.log", "at")
		print("Can't write to /var/log so creating a local 'debug.log' file.")
		debug = True
		
	logBuffer = logBufferClass(debug=debug)
	
	errorFlash = None
	while True:
		currentTime = datetime.datetime.now()
		try:
			CPUtempFile = open(cpuTempPath, "rt")
			for line in CPUtempFile:
				cpuTemp = float(line.strip())
			CPUtempFile.close() 
			logLine = "%s|%0.1f|%0.1f|%0.1f|%0.1f"%(str(currentTime), bme280.temperature, bme280.humidity, bme280.pressure, cpuTemp/1000)
			logBuffer.addEntry(logLine)
			timeSinceUpload = currentTime - lastUpload
			if debug: print("time since last upload %d seconds"%timeSinceUpload.seconds)
			if timeSinceUpload.seconds > uploadCadence: 
				if logBuffer.upload():
					lastUpload = datetime.datetime.now()
				else:
					lastUpload = datetime.datetime.now()
					print("Upload failed! Will try again in %d seconds"%uploadCadence)
					
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
	
	
