import json, os, requests
import adafruit_dht
import board, time, glob
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import threading


class exteriorSensor():
	def __init__(self):
		self.temperature = -999
		self.base_dir = '/sys/bus/w1/devices/'
		try: 
			self.device_folder = glob.glob(self.base_dir + '28*')[0]
			self.device_file = self.device_folder + '/w1_slave'
		except IndexError as e:
			print("Cannot initiliase the DS18B20")
		


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
		self.monitorCadence = 4
		self.name = name
		self.attachedFan = None
		self.fan = False
		
	def setFan(self, fan):
		self.fan = True
		self.attachedFan = fan
		
	def readTemp(self):
		try:
			CPUtempFile = open(self.cpuTempPath, "rt")
			for line in CPUtempFile:
				self.temperature = float(line.strip())/1000
			CPUtempFile.close() 
		except Exception as e:
			print(str(e))	
		return self.temperature
		
	def monitor(self):
		while True:
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
		self.monitorCadence = 10
		self.name = "dome"
		self.attachedFan = None
		self.fan = False
		
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
		return self.humidity
		
	def monitor(self):
		while True:
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

