#!/usr/bin/env python
import requests
import argparse
import json
import time
import datetime
import subprocess
import sys
import os
import config, imagedata
from systemd import journal
from PIL import Image,ImageDraw
from PIL.ExifTags import TAGS


def debugOut(message):
	if debug: print(message, flush=True)

def uploadMetadata(jsonData, URL):
		success = False
		information("Sending JSON payload to: %s"%URL)
		try: 
			response = requests.post(URL, json=jsonData)
			responseJSON = json.loads(response.text)
			print(json.dumps(responseJSON, indent=4))
			if responseJSON['status'] == 'success': success = True
			response.close()
		except Exception as e: 
			success = False
			print(e, flush=True)
				
		print(success, flush=True)
		return success


def uploadToServer(imageFilename, URL):
	destinationURL = URL
	files = {'camera': open(imageFilename, 'rb')}
	headers = { 'Content-type': 'image/jpeg'}
	try:
		response = requests.post(destinationURL, files=files)
		information("SkyWATCH server's response code: " + str(response.status_code))
		response.close()
	except Exception as e: 
		information("error: " + repr(e))
		return 
	information("Uploaded image to %s\n"%destinationURL) 
	return
   
def information(message):
	print(message, flush=True)
	return

def showTags(tags):
	for key in tags.keys():
		print(TAGS[key], tags[key])
	
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Performs post processing of the skycam images.')
	parser.add_argument('-t', '--cadence', type=int, default=5, help='Cadence in seconds.' )
	parser.add_argument('-f', '--filename', type=str, default="latest", help='Filename to process (or look for the latest).' )
	parser.add_argument('-c', '--config', type=str, default='/home/pi/code/meteopi/local.cfg', help='Config file.' )
	parser.add_argument('--debug', action="store_true", default=False, help='Add debug information to the output.' )
	parser.add_argument('--preview', action="store_true", default=False, help='Show preview.' )
	
	args = parser.parse_args()
	debug = args.debug
	config = config.config(filename=args.config)
	config.load()
	#print(config)

	if args.filename == "latest":
		# Generate the list of files in the specified folder
		debugOut("Looking for the most recent file in %s"%config.cameraoutputpath)
		import glob
		listing = glob.glob(config.cameraoutputpath + "/*.jpg")
		fileCollection = []
		for f in listing:
			fdict = { "filename": os.path.join(config.cameraoutputpath, f), "timestamp": os.path.getmtime(os.path.join(config.cameraoutputpath, f))}
			fileCollection.append(fdict)

		fileCollection.sort(key=lambda item: item['timestamp'])
		imageFile = fileCollection[-1]
		debugOut("Most recent: %s"%imageFile)
	else:
		imageFile = { "filename": args.filename } 

	imageData = imagedata.imagedata()
	imageData.setFilename(os.path.splitext(imageFile['filename'])[0] + ".json")
	imageData.load()
	imageData.show()
	
	image = Image.open(imageFile["filename"])
	exif_data = image._getexif()
	if debug: showTags(exif_data)
	size = image.size
	imageData.setProperty("width", size[0])
	imageData.setProperty("height", size[1])
	debugOut("size: %s"%str(size))
	index = str(exif_data).find("exp=")
	end = str(exif_data).find(' ', index)
	expTime = float(str(exif_data)[index+4: end+1])
	imageData.setProperty("exposure", expTime/1E6)
	debugOut("Exposure time %.2f seconds"%(expTime/1E6))
	debugOut("Bands: %s"%str(image.getbands()))
	imageData.save()		
	
	lowBandwidth = False
	try:
		if config.bandwidthlimited==1: 
			print("Upload bandwidth is limited. We will re-scale the image.", flush=True)
			lowBandwidth = True
	except AttributeError:
		print("Assuming full upload bandwidth is available.", flush=True)

	
	if lowBandwidth:
		if imageFile['filename'].find('small')!=-1:
			print("Filename already contains the word 'small' ... not resizing.")
		else:
			newFilename = imageFile['filename'].split('.')[0] + "_small.jpg"
			imageData.setFilename(os.path.splitext(newFilename)[0] + ".json")
			imageData.setProperty("resized", True)
			imageData.setProperty("width", int(size[0]/4))
			imageData.setProperty("height", int(size[1]/4))
			scaleCommand = ["convert", imageFile['filename'], '-resize', '1014', newFilename]
			#scaleCommand.append()
			commandLine =""
			for s in scaleCommand:
				commandLine+= s + " "
			print("Running:", commandLine, flush=True)
			subprocess.call(scaleCommand)
			# Reload the re-scaled image
			image = Image.open(newFilename)
			imageFile['filename'] = newFilename
			imageData.setProperty("file", os.path.basename(newFilename))
			imageData.save()
		

	information("Image size is now: %s"%str(image.size))
	# If upload is set... upload to skyWATCH server
	URL = config.camerauploadURL
	uploadToServer(imageFile['filename'], URL)	

	uploadMetadata(imageData.getJSON(), "https://skywatching.eu/imagedata")
	

	if args.preview: 
		print("Rendering a preview to the X-session ... will take about 30s")
		image.show()

	