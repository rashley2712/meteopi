#!/usr/bin/env python

import config    # These are libraries that are part of meteopi
import subprocess,argparse, json, sys, os, datetime, shutil
import ephem

def debugOut(message):
	if debug: print(message)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Script to copy files from the local machine (pi) to a network mounted archive.')
	parser.add_argument('--debug', action="store_true", default=False, help='Add debug information to the output.' )
	parser.add_argument('-c', '--config', type=str, default='meteopi.cfg', help='Configuration file.' )
	parser.add_argument('-m', '--makeMovie', action="store_true", default=False, help='Make the movie with FFMPEG.' )
		
	args = parser.parse_args()

	debug = args.debug
	
	config = config.config(filename=args.config)
	config.load()
	#print(config.getProperties())
	
	if not hasattr(config, "archive"):
		print("No archive information found in the config file: %s"%args.config)
		sys.exit()
		
	print("Archive configuration %s"%json.dumps(config.archive))
	localPath = config.archive['local']
	
	now = datetime.datetime.now()
	nowSeconds = datetime.datetime.timestamp(now)
	timeString = now.strftime("%Y%m%d_%H%M")
	dateString = now.strftime("%Y%m%d")

	print("Today is:", dateString)
	yesterdayTemp = now - datetime.timedelta(days = 1)
	yesterday = yesterdayTemp.replace(hour = 12)
	print("Yesterday was:", yesterday)
	yesterdayString = yesterday.strftime("%Y%m%d")
	print(yesterdayString)
	
	rsyncCommand = ["rsync", "-av"]
	rsyncCommand.append(config.archive['local'] + "/%s*"%yesterdayString)
	remoteLocation = config.archive['remote'].replace("{date}", yesterdayString)
	rsyncCommand.append(remoteLocation)
	rsyncCommandString = " ".join(rsyncCommand)
	print("Running: %s"%rsyncCommandString)
	from subprocess import Popen, PIPE
	subprocess.call(rsyncCommandString, shell=True, executable="/bin/bash")

	rsyncCommand = ["rsync", "-av"]
	rsyncCommand.append(config.archive['local'] + "/%s*"%dateString)
	remoteLocation = config.archive['remote'].replace("{date}", dateString)
	rsyncCommand.append(remoteLocation)
	rsyncCommandString = " ".join(rsyncCommand)
	print("Running: %s"%rsyncCommandString)
	from subprocess import Popen, PIPE
	subprocess.call(rsyncCommandString, shell=True, executable="/bin/bash")


	sys.exit()
	
	# Get a list of all files in the local folder
	localPath = config.archive['local']
	fileList = os.listdir(localPath)
	fileData = []
	for f in fileList:
		if ".jpg" in f:
			mtime = os.stat(os.path.join(localPath, f)).st_mtime
			ageSeconds = nowSeconds - mtime
			ageDays = ageSeconds/86400
			fileInfo = { 'filename' : f, 'age' : ageDays}
			fileData.append(fileInfo)
	print(fileData)
	
	for location in config.locations:
		if location['name'] == config.currentLocation:
			currentLocation = location
	print(currentLocation)
	
	skywatchLocation=ephem.Observer()
	skywatchLocation.lat = str(currentLocation['latitude'])
	skywatchLocation.lon = str(currentLocation['longitude'])
	skywatchLocation.elevation = currentLocation['elevation']
	skywatchLocation.date = yesterday
	skywatchLocation.horizon = 0
	
	sun = ephem.Sun()
	sunsetSeconds = datetime.datetime.timestamp(skywatchLocation.next_setting(sun).datetime())
	sunriseSeconds = datetime.datetime.timestamp(skywatchLocation.next_rising(sun).datetime())
	duration = sunriseSeconds - sunsetSeconds

	print("Last night's sunset at %s was at: %s"%(config.currentLocation, ephem.localtime(skywatchLocation.next_setting(sun))))
	print("This morning's sunrise at %s was at: %s"%(config.currentLocation, ephem.localtime(skywatchLocation.next_rising(sun))))
	print("Duration was %.1f hours."%(duration/3600))

	nightExposures = []
	for f in fileData:
		year = int(f['filename'][0:4])
		month = int(f['filename'][4:6])
		day = int(f['filename'][6:8])
		hour = int(f['filename'][9:11])
		minute = int(f['filename'][11:13])
		second = int(f['filename'][13:15])
		timestamp = datetime.datetime(year, month, day, hour, minute, second)
		timestampSeconds = datetime.datetime.timestamp(timestamp)
		if timestampSeconds>sunsetSeconds and timestampSeconds<sunriseSeconds:
			nightExposures.append(f['filename'])
	nightExposures.sort()
	

	listFile = open("%s.list"%yesterdayString, "wt")
	for n in nightExposures:
		listFile.write(os.path.join(localPath, n) + "\n")
	listFile.close()
	
	print("Written %d filenames (exposures) to '%s.list'"%(len(nightExposures), yesterdayString))
	
	destinationPath = config.archive['location']
		
	if args.makeMovie:
		user = os.getlogin()
		ffmpegCommand = ["nice", "/home/%s/bin/pipeFFMPEG.bash"%user]
		ffmpegCommand.append(yesterdayString)
		print("Running:", ffmpegCommand)
		from subprocess import Popen, PIPE
		subprocess.call(ffmpegCommand)

	
		print("Copying movie %s, %s"%(yesterdayString + ".mp4", os.path.join(destinationPath, yesterdayString + ".mp4")))
		shutil.copyfile(yesterdayString + ".mp4", os.path.join(destinationPath, yesterdayString + ".mp4"))
	
		# Move the movie from the home folder. 
		print("Moving local copy of movie %s, %s"%(yesterdayString + ".mp4", os.path.join(localPath, yesterdayString + ".mp4")))
		shutil.move(yesterdayString + ".mp4", os.path.join(localPath, yesterdayString + ".mp4"))
		shutil.move(yesterdayString + ".list", os.path.join(localPath, yesterdayString + ".list"))

	
		#
		# 
		#
	# Now copy the sunset to sunrise original files to the archive folder.
	destinationNewFolder = os.path.join(destinationPath, yesterdayString)
	if not os.path.exists(destinationNewFolder):
		os.mkdir(destinationNewFolder)
	for f in nightExposures:
		print("Copying file: %s to %s"%(os.path.join(localPath, f), os.path.join(destinationNewFolder, f)))
		shutil.copyfile(os.path.join(localPath, f), os.path.join(destinationNewFolder, f))
