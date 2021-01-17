#!/usr/bin/env python
import requests
import argparse
import time
import datetime
import logging
import socket
from systemd import journal
import sys
import json
import shutil


def upload(diagnostics):
	uploadDestination = "http://astrofarm.local/diagnostics"
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
	parser.add_argument('-c', '--cadence', type=int, default=10, help='Cadence in seconds.' )
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )
	parser.add_argument('-d', '--debug', action="store_true", default=False, help='Give more debug information.') 
	args = parser.parse_args()

	debug = args.debug

	
	diagnostics = {}
	
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
	
	
	sys.exit()
	
	
