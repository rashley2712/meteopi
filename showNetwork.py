#!/usr/bin/env python
import argparse
import time
import datetime
import json, sys, os, requests
import skywatch, config    # These are libraries that are part of meteopi
import subprocess


def debugOut(message):
	if debug: print(message)
	
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Test script to read device\'s netwrok information.')
	parser.add_argument('-t', '--cadence', type=int, default=0, help='Repeat measurements every \'t\' seconds.' )
	parser.add_argument('-c', '--config', type=str, default='meteopi.cfg', help='Configuration file.' )
	parser.add_argument('--debug', action="store_true", default=False, help='Add degub information to the output.' )
	args = parser.parse_args()

	debug = args.debug
	
	config = config.config(filename=args.config)
	config.load()
	

	print("Testing network properties reader")

	systemInfo = skywatch.systemInfo()
	print(json.dumps(systemInfo.systemInfo, indent=4))


	sys.exit()

	output = subprocess.check_output(['ifconfig']).decode('UTF-8')
	


	sections = []
	section = ""
	for line in output.split("\n"):
		if len(line.strip())==0:
			sections.append(section)
			section = ""
		section+=line.strip()
	
	netConfig  = []
	for n, section in enumerate(sections):
		if len(section) <1: continue
		configInfo = {}
		print("Section ", n)
		print(section)
		configInfo['interface'] = section.split(":")[0]
		startIndex = section.find("inet ") + len("inet ")
		endIndex = section.find(" ", startIndex+1)
		ip = section[startIndex:endIndex]
		configInfo['ip'] = ip
		if not configInfo['interface']=='lo': netConfig.append(configInfo)
	print(json.dumps(netConfig, indent=4))