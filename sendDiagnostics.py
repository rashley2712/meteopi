#!/usr/bin/env python
import requests
import argparse
import time
import datetime
import socket
import sys
import json
import shutil
import os
import uuid


def upload(diagnostics):
	global baseURL
	uploadDestination = os.path.join(baseURL, "diagnostics")
	success = False
	print("Uploading to ", uploadDestination)
	try: 
		x = requests.post(uploadDestination, data = diagnostics)
		print(x.text)
		if x.text == "SUCCESS": success = True
	except Exception as e: 
		success = False
		print(e)
	return success

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Reports to the astrofarm webserver some diagnostic information.')
	parser.add_argument('-c', '--config', type=str, default='meteopi.cfg', help='Config file.' )
	parser.add_argument('-w', '--wait', action="store_true", default=False, help='Wait for 1 minute before trying to send diagnostic information.')
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )
	args = parser.parse_args()
	if args.wait:
		time.sleep(60)

	configFile = open(args.config, 'rt')
	config = json.loads(configFile.read())
	print(config)
	baseURL = config['baseURL']

	diagnostics = {}
	
	if args.service:
		original_stdout = sys.stdout # Save a reference to the original standard output
		original_stderr = sys.stderr # Save a reference to the original standard error
		logFile = open('/var/log/diagnostic.log', 'a+')
		sys.stdout = logFile
		sys.stderr = logFile
    
	# Get date-time
	now = datetime.datetime.utcnow()
	print(now)
	diagnostics['datetimeutc'] = str(now)
	
	# Get hostname
	hostname = socket.gethostname()
	diagnostics['hostname'] = hostname
	
	# Get IP address
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(("8.8.8.8", 80))
	ipAddress = s.getsockname()[0]
	diagnostics['localip'] = ipAddress

	# Get mac address
	macAddress = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
	diagnostics['macaddress'] = macAddress

	# Get uptime
	with open('/proc/uptime', 'r') as f:
		uptime_seconds = float(f.readline().split()[0])
	diagnostics['uptime'] = uptime_seconds
	
	
	# Get disk usage
	total, used, free = shutil.disk_usage("/")
	diagnostics['disktotal'] = total // (2**30)
	diagnostics['diskused'] = used // (2**30)
	diagnostics['diskfree'] = free // (2**30)
	
	# Get CPU temperature
	cpuTempPath = "/sys/class/thermal/thermal_zone0/temp"
	CPUtempFile = open(cpuTempPath, "rt")
	for line in CPUtempFile:
		cpuTemp = float(line.strip())/1000
	CPUtempFile.close() 
	diagnostics['cputemp'] = cpuTemp
	
	# Get OS version
	with open('/proc/version', 'r') as f:
		OSversion = f.readline().strip()
	diagnostics['osversion'] = OSversion
	
	print(json.dumps(diagnostics, indent=4))
	
	upload(diagnostics)
	
	if args.service:
		sys.stdout = original_stdout # Reset the standard output to its original value
		sys.stderr = original_stderr # Reset the standard output to its original value
		logFile.close()
	sys.exit()
	
	
