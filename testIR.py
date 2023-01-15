#!/usr/bin/env python3

import datetime
import time
import subprocess

while True:
	now = datetime.datetime.now()
	
	try: 
		output = subprocess.check_output(['/home/rashley/code/meteopi/readTsky']).decode('UTF-8')
		skytemperature = round(float(output.split('\n')[0]),1)
	except Exception as e:
		print("Could not read the IR sensor", flush = True)
		print(e)

	try: 
		output = subprocess.check_output(['/home/rashley/code/meteopi/readTamb']).decode('UTF-8')
		ambienttemperature = round(float(output.split('\n')[0]),1)
	except Exception as e:
		print("Could not read the IR sensor", flush = True)
		print(e)

	print('%s - %.1f \u00b0C\t %.1f \u00b0C'%(now, skytemperature, ambienttemperature))
	time.sleep(5)
