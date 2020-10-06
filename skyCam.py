#!/usr/bin/env python3
import argparse
import requests
import time
import datetime
import threading
import subprocess, os
import logging
from systemd import journal

def uploadToServer(imageFilename):
	destinationURL = 'http://astrofarm.eu/imageUpload'
	files = {'skycam': open(imageFilename, 'rb')}
	response = requests.post(destinationURL, files=files)
	print(response)

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
	
	while True:
		
		# Take an image
		imageCommand = ['raspistill']
		imageCommand.append('-n')	# No preview
		imageCommand.append('-a')	# Add annotation ...
		imageCommand.append('12')	# ... date and time
		#imageCommand.append('-ex')	# Exposure mode
		#imageCommand.append('night')	# Night time
		#imageCommand.append('-v') 	# Verbose
		imageCommand.append('-o')
		imageCommand.append('latest.jpg')
		subprocess.call(imageCommand)
		currentTime = datetime.datetime.now()
		timeString = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
		print(timeString)
		destinationFilename = os.path.join(destinationPath, timeString + ".jpg")
		os.rename("latest.jpg", destinationFilename);
		if args.service: log.info("written image to %s\n"%destinationFilename)
		else: 
			print("written image to %s"%destinationFilename)
		uploadToServer(destinationFilename)
		time.sleep(cadence)
	
	
