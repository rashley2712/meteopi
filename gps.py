#!/usr/bin/python3
import serial
import time
import sys
import argparse
import json

def sendCommand(command):
	global ser
	print("COMMAND:",command)
	ser.write(command.encode())
	ser.flushInput()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Starts the GPS process on the GSM HAT and waits until location information is found.')
	parser.add_argument('-c', '--config', type=str, default='meteopi.cfg', help='Config file.' )
	parser.add_argument('-n', '--number', default = 5, type=int, help="Stop after 'n' good GPS readings.")
	parser.add_argument('--gpson', action="store_true", default=False, help="Leave GPS device on when finished.")
	args = parser.parse_args()

	configFile = open(args.config, 'rt')
	config = json.loads(configFile.read())
	
	try: serialDev = config.GSMserial
	except: serialDev = "/dev/ttyUSB0"
	try: GPSlogfile = config.GPSlog
	except: GPSlogfile = "/var/log/gps.log"

	ser = serial.Serial(serialDev,115200)

	W_buff = ["AT+CGNSPWR=1\r\n", "AT+CGNSSEQ=\"RMC\"\r\n", "AT+CGNSINF\r\n", "AT+CGNSURC=2\r\n","AT+CGNSTST=1\r\n"]

	powerOn = "AT+CGNSPWR=1\r\n"
	powerOff = "AT+CGNSPWR=0\r\n"
	baudRate = "AT+CGNSIPR?\r\n"
	navigation = "AT+CGNSINF\r\n"
	status = "AT+CGNSTST=1\r\n"

	sendCommand(powerOn)
	data = ""

	bufferedBytes = 0
	timeoutCounter = 0
	while True:

		bufferedBytes = ser.inWaiting()
		print("%d timeout.... %d bytes to be read."%(timeoutCounter, bufferedBytes), flush=True)
		time.sleep(0.2)
		timeoutCounter+=1
		if bufferedBytes >1: break
		if timeoutCounter>50:
			print("No response from GSM HAT. Is it powered on?")
			sys.exit()
	data += ser.read(ser.inWaiting()).decode()
	print(data)


	print("next command:", baudRate)
	time.sleep(3)
	data =""
	sendCommand(baudRate)
	while True:
		print(ser.inWaiting())
		while ser.inWaiting() > 0:
			data += ser.read(ser.inWaiting()).decode()
		if len(data) > 1:
			print("Response:", data, flush=True)
			break
		time.sleep(1)


	print("next command:", navigation, flush=True)
	time.sleep(1)
	data =""
	sendCommand(navigation)
	while True:
		print(ser.inWaiting())
		while ser.inWaiting() > 0:
			data += ser.read(ser.inWaiting()).decode()
		if len(data) > 1:
			print("Response:\n------------------\n", data, "\n----------------", flush=True)
			break
		time.sleep(1)

	def toTimeString(timeRMC):
		timeString = ""
		hours = int(timeRMC/10000)
		minutes = int((timeRMC - hours*10000)/100)
		seconds = int(timeRMC - minutes*100 - hours*10000)
		timeString+= "%02d:%02d:%02dUT"%(hours, minutes, seconds)
		return timeString
		
	def toDecimal(latlonRMC):
		degrees = int(latlonRMC/100)
		minutes = latlonRMC - degrees*100
		decimal = minutes/60
		degrees = degrees + decimal
		return "%5f"%degrees
		
	def toDateString(dateRMC):
		month = dateRMC[2:4]
		day = dateRMC[0:2]
		year = "20" + dateRMC[4:6]
		return "%s-%s-%s"%(year, month, day)

	print("next command", flush=True)
	time.sleep(1)
	data =""
	sendCommand(status)

	counter = 0
	timeoutCounter = 0
	try:
		while True:
			while ser.inWaiting() > 0:
				data += ser.read(ser.inWaiting()).decode()
			if len(data) > 1:
				# print("len:", len(data))
				# print("Response:", data)
				lines = data.split('\n')
				RMClines = []
				for line in lines:
					fields = line.split(',')
					if fields[0] == "$GNRMC": RMClines.append(line)
				
				fields = RMClines[-1].split(',')
				if len(fields) < 10:
					fields = RMClines[-2].split(',')
				
				try:
					status = fields[2]
					if (status=='V'): 
						print ("no GPS fix", flush=True)
						timeoutCounter+=1
						if timeoutCounter>40:
							print("Giving up. No GPS fix.")
							sys.exit()
					else: 
						latitude = float(fields[3])
						latCardinal = fields[4]
						longitude = float(fields[5])
						lonCardinal = fields[6]
						timeRMC = float(fields[1])
						dateRMC = fields[9]
						print(toDateString(dateRMC), toTimeString(timeRMC), toDecimal(latitude) + latCardinal, toDecimal(longitude)+ lonCardinal, flush=True)
						logFile = open("/var/log/gps.log", "at")
						logFile.write("%s %s %s %s\n"%(toDateString(dateRMC), toTimeString(timeRMC), toDecimal(latitude) + latCardinal, toDecimal(longitude)+ lonCardinal))
						logFile.close()
						counter+=1
						if counter==args.number: break
				except:
						print("...waiting...")
				data =""
			time.sleep(5)

	except KeyboardInterrupt:
		if ser != None:
			print("Clearing serial bus.")
			ser.close()
			sys.exit()

	# Power off the GPS device
	if not args.gpson:
		print("Powering off")
		sendCommand(powerOff)
		data = ""

		bufferedBytes = 0
		while True:
			bufferedBytes = ser.inWaiting()
			print("bytes to be read: ", bufferedBytes)
			time.sleep(0.2)
			if bufferedBytes >1: break
		data += ser.read(ser.inWaiting()).decode()
		print(data, flush=True)


