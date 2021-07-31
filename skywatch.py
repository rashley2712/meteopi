import json, os, requests, datetime
import adafruit_dht
import board, time, glob
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import threading
import socket, subprocess, uuid, shutil

class systemInfo:
	def __init__(self):
		self.systemInfo = {}
		# Get IP address
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(("8.8.8.8", 80))
		ipAddress = s.getsockname()[0]
		self.systemInfo['localip'] = ipAddress

		# Get WIFI SSID
		output = subprocess.check_output(['sudo', 'iwgetid']).decode('UTF-8')
		try: 
			ssid = output.split('"')[1]
		except:
			ssid = "none"	
		self.systemInfo['SSID'] = ssid

		# Get mac address
		macAddress = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
		self.systemInfo['macaddress'] = macAddress

		# Get uptime
		with open('/proc/uptime', 'r') as f:
			uptime_seconds = float(f.readline().split()[0])
		self.systemInfo['uptime'] = uptime_seconds
		
		
		# Get disk usage
		total, used, free = shutil.disk_usage("/")
		self.systemInfo['disktotal'] = total // (2**30)
		self.systemInfo['diskused'] = used // (2**30)
		self.systemInfo['diskfree'] = free // (2**30)
		



class webController:
	def __init__(self):
		self.statusURL = "http://rashley.local/piStatus"
		self.identity = socket.gethostname()
		self.status = {"hostname": self.identity}
		self.system = systemInfo()
		self.sensors = []

	def attachSensor(self, sensor):
		self.sensors.append(sensor)
		

	def sendStatus(self):
		sensorJSON = {}
		for sensor in self.sensors:
			sensorJSON[sensor.name] = sensor.logData
		self.status['sensors'] = sensorJSON
		self.sendData("http://rashley.local/pistatus", self.status)



	def sendData(self, URL, jsonData):
		success = False
		try: 
			response = requests.post(URL, json=jsonData)
			responseJSON = json.loads(response.text)
			print(json.dumps(responseJSON, indent=4))
			if responseJSON['status'] == 'success': success = True
			response.close()
		except Exception as e: 
			success = False
			print(e)
				
		print(success)
		return success


	def sendSystem(self):
		print(json.dumps(self.status, indent=4))
		print("Uploading to ", self.statusURL)
		self.status['system'] = self.system.systemInfo
	
		success = False
		try: 
			headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
			response = requests.post(self.statusURL, json=self.status)
			responseJSON = json.loads(response.text)
			print(json.dumps(responseJSON, indent=4))
			if responseJSON['status'] == 'success': success = True
			response.close()
		except Exception as e: 
			success = False
			print(e)
				
		print(success)
		return success


class logger():

	def __init__(self, filename = '/var/log/skywatch.log'):
		self.logfile = filename
		self.handle = open(self.logfile, 'at')
		self.sensors = []
		self.logCadence = 120
		self.exit = False
		self.name = "log"
		
	def writeEntry(self, message):
		timeStamp = datetime.datetime.now()
		timeStampStr = timeStamp.strftime("%Y%m%d %H:%M:%S")
		self.handle.write(timeStampStr + ": " + message)
		self.handle.write("\n")
		self.handle.flush()
		
	def attachSensor(self, sensor):
		self.sensors.append(sensor)
		
	def createEntry(self):
		for sensor in self.sensors: 
			self.writeEntry(str(sensor.name) + ": " + str(sensor.logData))
			
	def createJSONlog(self):
		logEntry = {}
		for sensor in self.sensors:
			logEntry[sensor.name] = sensor.logData
		self.writeEntry(json.dumps(logEntry))
			
	def monitor(self):
		while not self.exit:
			self.createJSONlog()
			time.sleep(self.logCadence)
			
	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()

	def killMonitor(self):
		print("stopping %s monitor."%self.name)
		self.exit = True
		
		
	def reset(self):
		self.handle.truncate(0)
		
	def close(self):
		self.handle.close()
	

class exteriorSensor():
	def __init__(self):
		self.temperature = -999
		self.base_dir = '/sys/bus/w1/devices/'
		self.name = "exterior"
		self.monitorCadence = 20
		self.fan = False
		self.attachedFan = None
		self.exit = False
		self.logData = { }
		
		try: 
			self.device_folder = glob.glob(self.base_dir + '28*')[0]
			self.device_file = self.device_folder + '/w1_slave'
		except IndexError as e:
			print("Cannot initiliase the DS18B20")
		
	def monitor(self):
		while not self.exit:
			self.readTemp()
			print(self.name + "monitor: ", self.temperature)
			if self.fan: self.attachedFan.checkFan(self.temperature)
			self.logData['temperature'] = self.temperature
			time.sleep(self.monitorCadence)
		
	def startMonitor(self):
		self.exit = False
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
	
	def killMonitor(self):
		print("stopping %s monitor."%self.name)
		self.exit = True

	def readTemp(self): 
		try:
			f = open(self.device_file, 'r')
			lines = f.readlines()
			f.close()
			equals_pos = lines[1].find('t=')
			if equals_pos != -1:
				temp_string = lines[1][equals_pos+2:]
				self.temperature = float(temp_string) / 1000.0
		except IndexError as e:
			print("Cannot read the DS18B20")
			return -999
		return self.temperature


class cpuSensor():
	def __init__(self, name = "cpu"):
		self.cpuTempPath = "/sys/class/thermal/thermal_zone0/temp"
		self.temperature = -999
		self.monitorCadence = 10
		self.name = name
		self.attachedFan = None
		self.fan = False
		self.exit = False
		self.logData = { } 
		
	def setFan(self, fan):
		self.fan = True
		self.attachedFan = fan
		
	def killMonitor(self):
		print("stopping %s monitor."%self.name)
		self.exit = True

	def readTemp(self):
		try:
			CPUtempFile = open(self.cpuTempPath, "rt")
			for line in CPUtempFile:
				self.temperature = float(line.strip())/1000
				self.logData['temperature'] = self.temperature
			CPUtempFile.close() 
		except Exception as e:
			print(str(e))	
		return self.temperature
		
	def monitor(self):
		while not self.exit:
			self.readTemp()
			print(self.name + "monitor: ", self.temperature)
			if self.fan: self.attachedFan.checkFan(self.temperature)
			time.sleep(self.monitorCadence)
		
	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
	
			
class domeSensor():
	def __init__(self, name = "dome"):
		# Initialise the dht device, with data pin connected to:
		self.pin = board.D17
		self.dhtDevice = adafruit_dht.DHT22(board.D17)
		self.temperature = -999
		self.humidity = -999
		self.monitorCadence = 20
		self.name = "dome"
		self.attachedFan = None
		self.fan = False
		self.exit = False
		self.logData = { }
		
	def killMonitor(self):
		print("stopping %s monitor."%self.name)
		self.exit = True

	def setFan(self, fan):
		self.fan = True
		self.attachedFan = fan
		
	def readTemp(self):
		try:
			self.temperature = self.dhtDevice.temperature
		except RuntimeError as error:
			# Errors happen fairly often, DHT's are hard to read, just keep going
			# print(error.args[0])
			time.sleep(2.0)
		except Exception as error:
			dhtDevice.exit()
			print("Re-initiliasing dome sensor")
			time.sleep(5)
			self.dhtDevice = adafruit_dht.DHT(board.D17)
		self.logData['temperature'] = self.temperature
		return self.temperature


	def readHumidity(self):
		try:
			self.humidity = self.dhtDevice.humidity
		except RuntimeError as error:
			# Errors happen fairly often, DHT's are hard to read, just keep going
			# print(error.args[0])
			time.sleep(2.0)
		except Exception as error:
			dhtDevice.exit()
			print("Re-initiliasing dome sensor")
			time.sleep(5)
			self.dhtDevice = adafruit_dht.DHT(board.D17)
		self.logData['humidity'] = self.humidity
		return self.humidity
		
	def monitor(self):
		while not self.exit:
			self.readTemp()
			self.readHumidity()
			print(self.name + "monitor: ", self.temperature, self.humidity)
			if self.fan: self.attachedFan.checkFan(self.temperature)
			time.sleep(self.monitorCadence)
		
	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
	


class fanController():
	def __init__(self, pin = 17):
		self.GPIO = pin
		self.name = "none"
		self.triggerTemperature = 65
		self.hysterisis = 5
		GPIO.setmode(GPIO.BCM) # Use BCM pin numbering
		GPIO.setup(self.GPIO, GPIO.OUT, initial=GPIO.LOW)
		self.fanOn = False 
		
	def checkFan(self, temp):
		if temp>self.triggerTemperature: 
			if not self.fanOn:
				print("Turning on " + self.name + " fan...")
				self.on()
		if temp<self.triggerTemperature-self.hysterisis:
			if self.fanOn:
				print("Turning the " + self.name + " fan off...")
				self.off()
		
	def on(self):
		GPIO.setup(self.GPIO, GPIO.OUT, initial=GPIO.HIGH) 
		self.fanOn = True
	
	def off(self):
		GPIO.setup(self.GPIO, GPIO.OUT, initial=GPIO.LOW)
		self.fanOn = False 
		
	def flip(self):
		if self.fanOn: self.off()
		else: self.on()
	

class config():
	def __init__(self, filename="meteopi.cfg", debug=False):
		self.db = {}
		self.filename = filename
		self.debug = debug
		self.json = {}
		self.local = False
		self.logger = None
		self.service = False
		
	def load(self):
		configFile = open(self.filename, 'rt')
		self.json = json.loads(configFile.read())
		#print(self.json)
		configFile.close()
		self.setProperties()
		
	def setProperties(self):
		for key in self.json.keys():
			print(key, ":", self.json[key])
			setattr(self, key, self.json[key])
		
	def refresh(self):
		configURL = os.path.join(self.baseURL, "runtime.cfg")
		if self.local: configURL = os.path.join(self.localURL, "runtime.cfg")
		print("Fetching config from " + configURL) 
		response = requests.get(configURL)
		if response.status_code != 200: 
			debugOut(str(response.status_code) + ": " +  response.reason)
			return -1 
		data = json.loads(response.text)
		#print("runtime config: %s "%configURL)
		#print(json.dumps(data, indent=4))
		response.close()
		self.db = data
		self.setProperties()
		return

