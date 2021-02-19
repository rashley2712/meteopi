#!/usr/bin/env python3
import argparse
import requests
import time
import datetime
import subprocess, os, sys
import logging
from systemd import journal
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import ephem
import json

def fetchCameraConfig(URL):
	response = requests.get(URL)
	data = json.loads(response.text)
	information("%s has the following parameters for the camera"%URL)
	information(str(data))
	return data


def testLED():   
	blinkTime = 0.05
	pinID = 47
	GPIO.setmode(GPIO.BCM) # Use BCM pin numbering
	GPIO.setwarnings(False) # Ignore warning for now	
	GPIO.setup(pinID, GPIO.OUT, initial=GPIO.LOW) #
	
	GPIO.output(pinID, GPIO.HIGH) # Turn on
	for i in range(20):
		GPIO.output(pinID, GPIO.HIGH) # Turn on
		time.sleep(blinkTime) # Sleep 
		GPIO.output(pinID, GPIO.LOW) # Turn off
		time.sleep(blinkTime) # Sleep 


def offLED():   
	pinID = 47
	GPIO.output(pinID, GPIO.HIGH) # Turn LED off

def onLED():   
	pinID = 47
	GPIO.output(pinID, GPIO.LOW) # Turn LED on


def isNight(locationInfo): 
	night = False
	meteoLocation = ephem.Observer()
	meteoLocation.lon = str(locationInfo['longitude'])
	meteoLocation.lat = str(locationInfo['latitude'])
	meteoLocation.elevation = locationInfo['elevation']
	d = datetime.datetime.utcnow()
	localTime = ephem.localtime(ephem.Date(d))
	meteoLocation.date = ephem.Date(d)
	sun = ephem.Sun(meteoLocation)
	# information("Sun azimuth: %s altitude: %s"%(sun.az, sun.alt))
	altitude = sun.alt*180/3.14125
	information("Sun altitude is: %.2f"%altitude)
	if altitude<-5: 
		information("will take night exposure...")
		night = True
		
	return night


def uploadToServer(imageFilename, URL):
	destinationURL = URL
	files = {'skycam': open(imageFilename, 'rb')}
	try:
		response = requests.post(destinationURL, files=files)
		information("response code: " + str(response.status_code))
	except Exception as e: 
		if args.service: log.error("Failed to upload image to %s\n"%destinationURL)
		information("error: " + repr(e))
		return 
	information("Uploaded image to %s\n"%destinationURL) 
	return

def information(message):
	global log
	if service: log.info(message)
	else: 
		print(message)
	return

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Runs the camera to capture a still image.')
	parser.add_argument('-t', '--cadence', type=int, default=180, help='Cadence in seconds.' )
	parser.add_argument('-u', '--upload', type=int, default=300, help='Upload cadence in seconds.' )
	parser.add_argument('-c', '--config', type=str, default='meteopi.cfg', help='Config file.' )
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )
	parser.add_argument('--test', action="store_true", default=False, help='Test mode. Don\'t upload images.' )
	parser.add_argument('-x', '--exit', action="store_true", default=False, help='Take one exposure and then exit.' )
	args = parser.parse_args()
	cadence = args.cadence
	service = args.service

	configFile = open(args.config, 'rt')
	config = json.loads(configFile.read())
	configFile.close()
	location = config['currentLocation']
	locationInfo = {}
	for l in config['locations']:
		if l['name'] == location: locationInfo = l
	
	if service:
		log = logging.getLogger('skycam.service')
		log.addHandler(journal.JournaldLogHandler())
		log.setLevel(logging.INFO)
		logLine = "Starting the skycam with a cadence of %d seconds"%cadence
		log.info(logLine)

	information("Location is: " + str(locationInfo))

	testLED()

	while True:
		beginning = datetime.datetime.now()
		cameraConfig = fetchCameraConfig(config['cameraparameterURL'])
		night = isNight(locationInfo)
		
		# Execute raspistill and time the execution
		imageCommand = ['raspistill']
		try: 
			cadence = float(cameraConfig['cadence'])
		except:
			cadence = args.cadence
		
		if night: 
			try:
				expTime = float(cameraConfig['expTime'])
			except: 
				expTime = 10
		
			timeMicros = expTime*1E6
			cmdString = cameraConfig['nightParams'] + " -ss %.0f"%timeMicros
			for piece in cmdString.split(" "):
				imageCommand.append(piece)
			imageCommand.append('-ae')
			imageCommand.append('64,0xffffff,0x000000')
		else: 
			imageCommand.append('-ae')
			imageCommand.append('64,0x000000,0xffffff')

		imageCommand.append('-a')	# Add annotation ...
		imageCommand.append('12')	# ... date and time
		imageCommand.append('-a')	# Add annotation ...
		imageCommand.append('%Y-%m-%d %X')	# ... date and time
		if len(cameraConfig['annotation']) > 0:
			information("Custom annotation requested: " + cameraConfig['annotation'])
			imageCommand.append('-a')	# Add annotation ...
			imageCommand.append(cameraConfig['annotation'])	# custom text 
			
		imageCommand.append('-o')	
		imageCommand.append('/tmp/camera.jpg')

		cmdString = ""
		for piece in imageCommand:
			cmdString+= piece + " "
		information("cmdString: %s"%cmdString)
		offLED()
		start = datetime.datetime.now()
		subprocess.call(imageCommand)	
		end = datetime.datetime.now()
		onLED()
		duration = end - start
		midpoint = start + duration/2
		information("time elapsed %s"%str(duration))
		
		timeString = midpoint.strftime("%Y%m%d_%H%M%S")
		destinationFilename = os.path.join(config['cameraoutputpath'], timeString + ".jpg")
		information("moving the capture to %s"%destinationFilename)
		os.rename("/tmp/camera.jpg", destinationFilename)
		if not args.test: uploadToServer(destinationFilename, config['camerauploadURL'])
		if args.exit: sys.exit()

		end = datetime.datetime.now()
		elapsedTime = (end - beginning).total_seconds()
		timeToWait = cadence - elapsedTime
		information("Total elapsed time: %.1f  Cadence is %.1f   ... time to wait %0.1f"%(elapsedTime, cadence, timeToWait))
		if timeToWait>0: 
			information("Sleeping now")
			time.sleep(timeToWait)
	


	sys.exit()
