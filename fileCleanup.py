#!/usr/bin/python3
import argparse
import datetime
import os

def uploadToServer(imageFilename):
	destinationURL = 'http://astrofarm.eu/imageUpload'
	files = {'skycam': open(imageFilename, 'rb')}
	response = requests.post(destinationURL, files=files)
	print(response)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Checks a folder and deletes files older than x days.')
	parser.add_argument('path', type=str, help='Folder to clean up.' )
	parser.add_argument('-d', '--days', type=float, default=5.0, help='Age of file to remove. Default is 5 days.' )
	parser.add_argument('-l', '--list', action="store_true", default=False, help='Just list the files, but don\'t remove them. ')
	args = parser.parse_args()

	debug = False
		
	now = datetime.datetime.now()
	nowSeconds = datetime.datetime.timestamp(now)
	if debug: print("Now is:", now)
	if debug: print("Now is:", nowSeconds)
	fileList = os.listdir(args.path)
	fileData = []
	for f in fileList:
		mtime = os.stat(os.path.join(args.path, f)).st_mtime
		ageSeconds = nowSeconds - mtime
		ageDays = ageSeconds/86400
		fileInfo = { 'filename' : f, 'age' : ageDays}
		fileData.append(fileInfo)

	if args.list:
		for f in fileData:
			print("Filename: %s is %.1f days old"%(f['filename'], f['age']))

		print("\nfiles for deleting...")
		print("\033[31m") 
		for f in fileData:
			if f['age']>args.days:
				print("Filename: %s is %.1f days old and should be deleted"%(f['filename'], f['age']))
		print("\033[0m") 
	else: 
		for f in fileData:
			if f['age']>args.days:
				os.remove(os.path.join(args.path, f['filename']))
				print("Deleted: ", f['filename'])
	
		