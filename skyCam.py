#!/usr/bin/env python3
import argparse
from posixpath import basename
import requests
import time
import datetime
import subprocess, os, sys
import logging
from systemd import journal
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import ephem
import json
import config, imagedata
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
		print(message, flush=True)
	return

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Runs the camera to capture a still image.')
	parser.add_argument('-c', '--config', type=str, default='meteopi.cfg', help='Config file.' )
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )
	parser.add_argument('--test', action="store_true", default=False, help='Test mode. Don\'t upload images.' )
	parser.add_argument('-x', '--exit', action="store_true", default=False, help='Take one exposure and then exit.' )
	args = parser.parse_args()
	
	service = args.service

	config = config.config(filename=args.config)
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
		dbTimeString = beginning.strftime("%Y-%m-%d %H:%M:%S")
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
		information("time elapsed during camera operation %s"%str(duration))
		
		destinationFilename = os.path.join(config.cameraoutputpath, timeString + "_" + hostname + ".jpg")
		information("moving the capture to %s"%destinationFilename)
		os.rename("/tmp/camera.jpg", destinationFilename)

        # Write image metadata
		imageData = imagedata.imagedata()
		imageData.setProperty("hostname", hostname)
		imageData.setProperty("file", os.path.basename(destinationFilename))
		imageData.setProperty("date", dbTimeString)
		imageData.setProperty("location", locationInfo)
		imageData.setProperty("moon", { "elevation": "%.1f"%ephemeris['moonElevation'], "illumination":  "%.1f"%ephemeris['moonIllumination']} )
		imageData.setProperty("sun", { "elevation": "%.1f"%ephemeris['sunElevation'] } )
		
		imageData.setFilename(destinationFilename.split('.')[0] + ".json")
		imageData.save()

		if not args.test: 
			information("image post processing...")			
			processorCommand = [ os.path.join(config.installpath, "imageProcessor.py"), "-c" , args.config, "-f", destinationFilename ] 
			commandLine =""
			for s in processorCommand:
				commandLine+= s + " "
			information("calling: %s"%commandLine)
			subprocess.call(processorCommand)
		if args.exit: sys.exit()

		end = datetime.datetime.now()
		elapsedTime = (end - beginning).total_seconds()
		timeToWait = cadence - elapsedTime
		information("Total elapsed time: %.1f  Cadence is %.1f   ... time to wait %0.1f"%(elapsedTime, cadence, timeToWait))
		if timeToWait>0: 
			information("Sleeping now")
			time.sleep(timeToWait)
	
	sys.exit()
