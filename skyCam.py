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
import skywatch
import socket

def fetchCameraConfig(URL):
	response = requests.get(URL)
	data = json.loads(response.text)
	information("%s has the following parameters for the camera"%URL)
	information(str(data))
	response.close()
	return data

def offLED():   
	global config
	information("turning off status LED by writing to " + str(config.ledFile))
	outfile = open(config.ledFile, "wt")
	outfile.write("off\n")
	outfile.close()
	time.sleep(config.ledRefresh)
		
def onLED():   
	global config
	information("status LED back to heartbeat by writing to " + str(config.ledFile))
	outfile = open(config.ledFile, "wt")
	outfile.write("heartbeat\n")
	outfile.close()

def getSunMoon(locationInfo): 
	night = False
	meteoLocation = ephem.Observer()
	meteoLocation.lon = str(locationInfo['longitude'])
	meteoLocation.lat = str(locationInfo['latitude'])
	meteoLocation.elevation = locationInfo['elevation']
	d = datetime.datetime.utcnow()
	localTime = ephem.localtime(ephem.Date(d))
	information("local time: " + str(localTime))
	information("universal time: " + str(d))
	meteoLocation.date = ephem.Date(d)
	sun = ephem.Sun(meteoLocation)
	moon = ephem.Moon(meteoLocation)
	# information("Sun azimuth: %s altitude: %s"%(sun.az, sun.alt))
	altitude = sun.alt*180/3.14125
	information("Sun elevation is: %.2f"%altitude)
	currentDate = ephem.Date(d)
	timeToNewMoon = ephem.next_new_moon(currentDate) - currentDate
	timeSinceLastNewMoon = currentDate - ephem.previous_new_moon(currentDate)
	period = timeToNewMoon + timeSinceLastNewMoon
	phase = timeSinceLastNewMoon / period
	information("Moon elevation is: %.2f and illumination is: %.2f"%(moon.alt*180/3.14125, moon.phase))
	if altitude<-5: 
		# information("will take night exposure...")
		night = True
		
	results = {
		"night" : night,
		"sunElevation" : altitude,
		"moonIllumination": moon.phase, 
		"moonElevation": (moon.alt*180/3.14125)
	}
	return results


def uploadToServer(imageFilename, URL):
	destinationURL = URL
	files = {'camera': open(imageFilename, 'rb')}
	headers = { 'Content-type': 'image/jpeg'}
	try:
		response = requests.post(destinationURL, files=files)
		information("SkyWATCH server's response code: " + str(response.status_code))
		response.close()
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
	parser.add_argument('-c', '--config', type=str, default='meteopi.cfg', help='Config file.' )
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )
	parser.add_argument('--test', action="store_true", default=False, help='Test mode. Don\'t upload images.' )
	parser.add_argument('-x', '--exit', action="store_true", default=False, help='Take one exposure and then exit.' )
	args = parser.parse_args()
	
	service = args.service

	config = skywatch.config(filename=args.config)
	config.load()
	#print(config.getProperties())
	
	# Get hostname
	hostname = socket.gethostname()

	location = config.currentLocation
	locationInfo = {}
	for l in config.locations:
		if l['name'] == location: locationInfo = l
	
	if service:
		log = logging.getLogger('skycam.service')
		log.addHandler(journal.JournaldLogHandler())
		log.setLevel(logging.INFO)
		logLine = "Starting the skycam service"
		log.info(logLine)

	information("Location is: " + str(locationInfo))

	while True:
		beginning = datetime.datetime.now()
		offLED()
		# cameraConfig = fetchCameraConfig(config.cameraparameterURL)
		ephemeris = getSunMoon(locationInfo)
		if not ephemeris['night']: mode = 'day'
		else: mode = 'night'
		
		information("Exposures will be in " + mode + " mode.")
		cameraConfig = config.camera[mode]
		cadence = cameraConfig['cadence']
		
		timeString = beginning.strftime("%Y%m%d_%H%M%S")
		# Execute raspistill and time the execution
		imageCommand = ['raspistill']
		
		if mode=="night": 
			expTime = float(cameraConfig['expTime'])
			
			timeMicros = expTime*1E6
			cmdString = cameraConfig['params'] + " -ss %.0f"%timeMicros
			for piece in cmdString.split(" "):
				imageCommand.append(piece)
			imageCommand.append('-ae')
			imageCommand.append('64,0xffffff,0x000000')
		else: 
			cmdString = cameraConfig['params']
			for piece in cmdString.split(" "):
				imageCommand.append(piece)	
			imageCommand.append('-ae')
			imageCommand.append('64,0x000000,0xffffff')

		#imageCommand.append('--awb')	# Correct for removal of IR filter
		#imageCommand.append('greyworld')	
		#imageCommand.append('-a')	# Add annotation ...
		#imageCommand.append('%Y-%m-%d %X')	# ... date and time
		extraAnnotation = timeString
		if mode=="night": extraAnnotation+= " N %ds"%int(expTime)
		extraAnnotation+= " sun: %.0f moon: %.0f (%.0f%%)"%(ephemeris['sunElevation'], ephemeris['moonElevation'], ephemeris['moonIllumination'])
		if len(cameraConfig['annotation']) > 0:
			information("Custom annotation requested: " + cameraConfig['annotation'])
			extraAnnotation+= " " + cameraConfig['annotation']
		extraAnnotation = "'" + extraAnnotation + "'"
		
		imageCommand.append('-a')	# Add annotation ...
		imageCommand.append(extraAnnotation)	# custom text 
			
		imageCommand.append('-o')	
		imageCommand.append('/tmp/camera.jpg')

		cmdString = ""
		for piece in imageCommand:
			cmdString+= piece + " "
		information("cmdString: %s"%cmdString)
		start = datetime.datetime.now()
		subprocess.call(imageCommand)	
		end = datetime.datetime.now()
		onLED()
		duration = end - start
		midpoint = start + duration/2
		information("time elapsed %s"%str(duration))
		
		destinationFilename = os.path.join(config.cameraoutputpath, timeString + "_" + hostname + ".jpg")
		information("moving the capture to %s"%destinationFilename)
		os.rename("/tmp/camera.jpg", destinationFilename)
		if not args.test: uploadToServer(destinationFilename, config.camerauploadURL)
		if args.exit: sys.exit()

		end = datetime.datetime.now()
		elapsedTime = (end - beginning).total_seconds()
		timeToWait = cadence - elapsedTime
		information("Total elapsed time: %.1f  Cadence is %.1f   ... time to wait %0.1f"%(elapsedTime, cadence, timeToWait))
		if timeToWait>0: 
			information("Sleeping now")
			time.sleep(timeToWait)
	
	sys.exit()
