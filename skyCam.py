#!/usr/bin/env python3
import argparse
import requests
import time
import datetime
import threading
import subprocess, os, sys
import logging
from systemd import journal
import ephem

def uploadToServer(imageFilename):
	destinationURL = 'http://astrofarm.eu/imageUpload'
	files = {'skycam': open(imageFilename, 'rb')}
	try: response = requests.post(destinationURL, files=files)
	except Exception as e: 
		 if args.service: log.error("Failed to upload image to %s\n"%destinationURL)
		 print(e)
		 return 
	if args.service: log.info("Uploaded image to %s\n"%destinationURL) 
	else: print(response)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Runs the camera to capture a still image.')
	parser.add_argument('-c', '--cadence', type=int, default=180, help='Cadence in seconds.' )
	parser.add_argument('-u', '--upload', type=int, default=300, help='Upload cadence in seconds.' )
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )
	args = parser.parse_args()

	debug = False
	cadence = args.cadence
	uploadCadence = args.upload
	lastUpload = datetime.datetime.now()
	destinationPath = "/home/pi/share/camera"
	
	if args.service:
		log = logging.getLogger('skycam.service')
		log.addHandler(journal.JournaldLogHandler())
		log.setLevel(logging.INFO)
		logLine = "Starting the skycam with a cadence of %d seconds"%cadence
		log.info(logLine)
	
	sun = ephem.Sun()
	meteoLocation = ephem.Observer()
	meteoLocation.lon = '-3.5262707'
	meteoLocation.lat = '40.3719808'
	meteoLocation.elevation = 900
	meteoLocation.lon = '342.12'
	meteoLocation.lat = '28.76'
	meteoLocation.elevation = 2326
	#meteoLocation.lon = '-17.7742491'
	#meteoLocation.lat = '28.6468866'
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
		nightOptions = ['-ex', 'night', '-ISO', '800', '-ss', '6000000']
		# Take an image
		imageCommand = ['raspistill']
		imageCommand.append('-n')	# No preview
		imageCommand.append('-ae')
		if not night: imageCommand.append('64,0x000000,0xffffff')
		else: imageCommand.append('64,0xffffff, 0x000000')
		imageCommand.append('-a')	# Add annotation ...
		imageCommand.append('12')	# ... date and time
		imageCommand.append('-a')	# Add annotation ...
		imageCommand.append('%Y-%m-%d %X')	# ... date and time
		if night:
			imageCommand = imageCommand + nightOptions
		imageCommand.append('-o')
		imageCommand.append('latest.jpg')
		if args.service: log.info(imageCommand)
		else: print(imageCommand)
		subprocess.call(imageCommand)
		currentTime = datetime.datetime.now()
		timeString = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
		destinationFilename = os.path.join(destinationPath, timeString + ".jpg")
		os.rename("latest.jpg", destinationFilename);
		if args.service: log.info("written image to %s\n"%destinationFilename)
		else: 
			print("written image to %s"%destinationFilename)
		uploadToServer(destinationFilename)
		time.sleep(cadence)
	
	
