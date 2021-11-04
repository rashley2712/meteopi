#!/usr/bin/python3
import serial
import time
import sys

def sendCommand(command):
	global ser
	print("COMMAND:",command)
	ser.write(command.encode())
	ser.flushInput()

ser = serial.Serial("/dev/ttyUSB0",115200)

W_buff = ["AT+CGNSPWR=1\r\n", "AT+CGNSSEQ=\"RMC\"\r\n", "AT+CGNSINF\r\n", "AT+CGNSURC=2\r\n","AT+CGNSTST=1\r\n"]

powerOn = "AT+CGNSPWR=1\r\n"
baudRate = "AT+CGNSIPR?\r\n"
navigation = "AT+CGNSINF\r\n"
status = "AT+CGNSTST=1\r\n"

sendCommand(powerOn)
data = ""

bufferedBytes = 0
while True:
	bufferedBytes = ser.inWaiting()
	print("bytes to be read: ", bufferedBytes)
	time.sleep(0.2)
	if bufferedBytes >1: break
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
		print("Response:", data)
		break
	time.sleep(1)


print("next command:", navigation)
time.sleep(1)
data =""
sendCommand(navigation)
while True:
	print(ser.inWaiting())
	while ser.inWaiting() > 0:
		data += ser.read(ser.inWaiting()).decode()
	if len(data) > 1:
		print("Response:\n------------------\n", data, "\n----------------")
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
	day = dateRMC[2:4]
	month = dateRMC[0:2]
	year = "20" + dateRMC[4:6]
	return "%s-%s-%s"%(year, month, day)

print("next command")
time.sleep(1)
data =""
sendCommand(status)

try:
	while True:
		while ser.inWaiting() > 0:
			data += ser.read(ser.inWaiting()).decode()
		if len(data) > 1:
			# print("Response:", data)
			lines = data.split('\n')
			RMClines = []
			for line in lines:
				fields = line.split(',')
				if fields[0] == "$GNRMC": RMClines.append(line)
			
			fields = RMClines[-1].split(',')
			status = fields[2]
			if (status=='V'): print ("no GPS fix")
			else: 
				latitude = float(fields[3])
				latCardinal = fields[4]
				longitude = float(fields[5])
				lonCardinal = fields[6]
				timeRMC = float(fields[1])
				dateRMC = fields[9]
				print(toDateString(dateRMC), toTimeString(timeRMC), toDecimal(latitude) + latCardinal, toDecimal(longitude)+ lonCardinal)
			data =""
		time.sleep(10)

except KeyboardInterrupt:
	if ser != None:
		print("Clearing serial bus.")
		ser.close()
		sys.exit()
