#!/usr/bin/env python3
import argparse
import requests
import time
import datetime
import subprocess, os, sys
import logging
from systemd import journal
import ephem
import json

def fetchCameraConfig(URL):
	response = requests.get(URL)
	data = json.loads(response.text)
	information("%s has the following parameters for the camera"%URL)
	information(str(data))
	return data

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
	information("Sun azimuth: %s altitude: %s"%(sun.az, sun.alt))
	altitude = sun.alt*180/3.14125
	information("Sun altitude is: %.2f"%altitude)
	if altitude<-5: 
		information("will take night exposure...")
		night = True
		
	return night


def uploadToServer(imageFilename):
	destinationURL = 'https://www.astrofarm.eu/imageUpload'
	files = {'skycam': open(imageFilename, 'rb')}
	try: response = requests.post(destinationURL, files=files)
	except Exception as e: 
		 if args.service: log.error("Failed to upload image to %s\n"%destinationURL)
		 print(e)
		 return 
	if args.service: log.info("Uploaded image to %s\n"%destinationURL) 
	else: print(response)

def information(message):
	global log
	if service: log.info(message)
	else: 
		print(message)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Runs the camera to capture a still image.')
	parser.add_argument('-t', '--cadence', type=int, default=180, help='Cadence in seconds.' )
	parser.add_argument('-u', '--upload', type=int, default=300, help='Upload cadence in seconds.' )
	parser.add_argument('-c', '--config', type=str, default='meteopi.cfg', help='Config file.' )
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )
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

	while True:
		beginning = datetime.datetime.now()
		cameraConfig = fetchCameraConfig(config['cameraparameterURL'])
		night = isNight(locationInfo)

		# Execute raspistill and time the execution
		imageCommand = ['raspistill']
		if night: 
			try:
				expTime = float(cameraConfig['expTime'])
			except: 
				expTime = 10
			try: 
				cadence = float(cameraConfig['cadence'])
			except:
				cadence = args.cadence

			timeMicros = expTime*1E6
			cmdString = "-t 10 -md 3 -st -ex off -ag 1 -ss %.0f"%timeMicros
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
		imageCommand.append('-o')	
		imageCommand.append('/tmp/camera.jpg')

		cmdString = ""
		for piece in imageCommand:
			cmdString+= piece + " "
		information("cmdString: %s"%cmdString)
		start = datetime.datetime.now()
		subprocess.call(imageCommand)	
		end = datetime.datetime.now()
		duration = end - start
		midpoint = start + duration/2
		information("time elapsed %s"%str(duration))
		
		timeString = midpoint.strftime("%Y%m%d_%H%M%S")
		destinationFilename = os.path.join(config['cameraoutputpath'], timeString + ".jpg")
		information("moving the capture to %s"%destinationFilename)
		os.rename("/tmp/camera.jpg", destinationFilename)
		uploadToServer(destinationFilename)
		if args.exit: sys.exit()

		end = datetime.datetime.now()
		elapsedTime = (end - beginning).total_seconds()
		timeToWait = cadence - elapsedTime
		information("Total elapsed time: %.1f  Cadence is %.1f   ... time to wait %0.1f"%(elapsedTime, cadence, timeToWait))
		if timeToWait>0: 
			information("Sleeping now")
			time.sleep(timeToWait)
	


	sys.exit()
	debug = False
	cadence = args.cadence
	uploadCadence = args.upload
	destinationPath = "/home/pi/share/camera"
	
	if args.service:
		log = logging.getLogger('skycam.service')
		log.addHandler(journal.JournaldLogHandler())
		log.setLevel(logging.INFO)
		logLine = "Starting the skycam with a cadence of %d seconds"%cadence
		log.info(logLine)
	
	sun = ephem.Sun()
	meteoLocation = ephem.Observer()
	#meteoLocation.lon = '-3.5262707'
	#meteoLocation.lat = '40.3719808'
	#meteoLocation.elevation = 900
	#meteoLocation.lon = '342.12'
	# meteoLocation.lat = '28.76'
	meteoLocation.elevation = 2326
	meteoLocation.lon = '-17.7742491'
	meteoLocation.lat = '28.6468866'
	#meteoLocation.elevation = 281
	d = datetime.datetime.utcnow()
	localTime = ephem.localtime(ephem.Date(d))
	print(localTime)
	meteoLocation.date = ephem.Date(d)
	sun = ephem.Sun(meteoLocation)
	
	while True:
		# Get the sun's current altitude
		night = False
		d = datetime.datetime.utcnow()
		meteoLocation.date = ephem.Date(d)
		sun = ephem.Sun(meteoLocation)
		print(sun.az, sun.alt)
		altitude = sun.alt*180/3.14125
		if args.service:
			log.info("Sun altitude is: %.2f\n"%altitude)
		else: 
			print("Sun altitude is: %.2f"%altitude)
		if altitude<-5: 
			log.info("will take night exposure...")
			night = True
		nightExposureSecs = 100
		nightExposureString = str(nightExposureSecs * 1E6)
		nightOptions = ['-ex', 'verylong', '-ISO', '400', '-ss', nightExposureString, '-md', '3', '-bm', '-ag', '1', '-st']
		# Take an image
		imageCommand = ['raspistill']
		imageCommand.append('-n')	# No preview
		imageCommand.append('-ae')
		if not night: imageCommand.append('64,0x000000,0xffffff')
		else: imageCommand.append('64,0xffffff,0x000000')
		imageCommand.append('-a')	# Add annotation ...
		imageCommand.append('12')	# ... date and time
		imageCommand.append('-a')	# Add annotation ...
		imageCommand.append('"%Y-%m-%d %X"')	# ... date and time
		if night:
			imageCommand = imageCommand + nightOptions
		imageCommand.append('-r')
		imageCommand.append('-o')
		imageCommand.append('latest.jpg')
		cmdString = ""		
		for piece in imageCommand:
			cmdString+=piece + " "
		if args.service: log.info(cmdString)
		if args.service: log.info(imageCommand)
		else: print(imageCommand)
		subprocess.call(imageCommand)
		currentTime = datetime.datetime.now()
		timeString = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
		destinationFilename = os.path.join(destinationPath, timeString + ".jpg")
		os.rename("latest.jpg", destinationFilename)
		if args.service: log.info("written image to %s\n"%destinationFilename)
		else: 
			print("written image to %s"%destinationFilename)
		uploadToServer(destinationFilename)
		time.sleep(cadence)
	
	
