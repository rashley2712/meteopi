import json, os, requests, datetime
# import adafruit_dht
import board, time, glob
from adafruit_bme280 import basic as adafruit_bme280
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
		try: 
			output = subprocess.check_output(['sudo', 'iwgetid']).decode('UTF-8')
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
		

class meteoUploader:
	def __init__(self, baseURL = "http://rashley.local", timezone="utc",  config={}):
		self.statusURL = "http://rashley.local/piStatus"
		self.baseURL = baseURL
		self.uploadURL = "https://skywatching.eu/meteo"
		self.identity = socket.gethostname()
		self.status = {self.identity: {}}
		self.sensors = []
		self.exit = False
		try: 
			self.monitorCadence = config['cadence']
		except KeyError:
			self.monitorCadence = 180
		self.name = "meteo uploader"
		self.timezone = timezone

	def attachSensor(self, sensor):
		self.sensors.append(sensor)
		
	def send(self):
		data = {'hostname': self.identity}
		timeStamp = datetime.datetime.now()
		timeStampStr = timeStamp.strftime("%Y-%m-%d %H:%M:%S")
		data['timestamp'] = timeStampStr
		data['timezone'] = self.timezone
		for sensor in self.sensors:
			data[sensor.name] = sensor.logData
		
		print(str(self.name), json.dumps(data, indent=4), flush=True)
		self.sendData(self.uploadURL, data)

	def monitor(self):
		while not self.exit:
			self.send()
			time.sleep(self.monitorCadence)

	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
		
	def killMonitor(self):
		print("stopping %s monitor."%self.name)
		self.exit = True

	def sendData(self, URL, jsonData):
		success = False
		print("Sending to:", URL)
		try: 
			response = requests.post(URL, json=jsonData)
			responseJSON = json.loads(response.text)
			print(json.dumps(responseJSON, indent=4))
			if responseJSON['status'] == 'success': success = True
			response.close()
		except Exception as e: 
			success = False
			print(e, flush=True)
				
		print(success, flush=True)
		return success


class statusController:
	def __init__(self, config = {}):
		print("config", config)
		self.URL = config['URL']
		self.identity = socket.gethostname()
		self.status = {self.identity: {}}
		self.exit = False
		self.monitorCadence = config['cadence']
		self.name = "web uploader"
		self.timezone = "UTC"


	def sendSystem(self):
		self.status = { "hostname" : self.identity}
		print("generating system info", flush=True)
		systemJSON = {}
		timeStamp = datetime.datetime.now()
		timeStampStr = timeStamp.strftime("%Y-%m-%d %H:%M:%S")
		self.status['system'] = systemInfo().systemInfo
		self.status['date'] = timeStampStr
		self.status['timezone'] = self.timezone
		print("Sending..." + json.dumps(self.status, indent=4), flush=True)
		self.sendData(self.URL, self.status)

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
				
		print(success, flush=True)
		return success

	def monitor(self):
		while not self.exit:
			print("status monitor", flush=True)
			self.sendSystem()
			time.sleep(self.monitorCadence)

	def startMonitor(self):
		self.systemThread = threading.Thread(name='non-block', target=self.monitor)
		print("starting status monitor", flush=True)
		self.systemThread.start()
		

	def killMonitor(self):
		print("stopping %s monitor."%self.name)
		self.exit = True

		

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
		timeStampStr = timeStamp.strftime("%Y-%m-%d %H:%M:%S")
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
	def __init__(self, name="exterior", config = {}):
		self.temperature = -999
		self.base_dir = '/sys/bus/w1/devices/'
		self.name = name
		self.monitorCadence = config['cadence']
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
			print(self.name + "monitor: ", self.temperature, flush=True)
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
	def __init__(self, name = "cpu", config = {}):
		self.cpuTempPath = "/sys/class/thermal/thermal_zone0/temp"
		self.temperature = -999
		self.name = name
		self.attachedFan = None
		self.fan = False
		self.exit = False
		try: 
			self.monitorCadence = config['cadence']
		except KeyError:
			self.monitorCadence = 20
		self.logData = { } 
		

	def attachFan(self, fan):
		self.fan = True
		self.attachedFan = fan
		
	def killMonitor(self):
		print("stopping %s monitor."%self.name, flush=True)
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
			print(self.name + "monitor: ", self.temperature, flush=True)
			if self.fan: self.attachedFan.checkFan(self.temperature)
			time.sleep(self.monitorCadence)
		
	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
	
class domeSensor2():
	def __init__(self, name = "dome", config={}):
		# Initialise the bme280
		i2c = board.I2C()  # uses board.SCL and board.SDA
		self.active = False
		decAddress = int(config['address'], 16)
		try:
			self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address = decAddress)
		except ValueError:
			print("Sensor BME280 failed!", flush=True)
			self.active = False
		
		self.fan = False
		self.attachedFans = []
		self.temperature = -999
		self.humidity = -999
		self.pressure = -999
		self.name = name
		print(config, flush=True)
		try: 
			self.monitorCadence = config['cadence']
		except KeyError:
			self.monitorCadence = 20
		self.exit = False
		self.logData = { } 

	def attachFan(self, fan):
		self.attachedFans.append(fan)
		self.fan = True
		
	def readTemp(self):
		try:
			self.temperature = round(self.bme280.temperature, 1)
		except:
			self.temperature = -999
		self.logData['temperature'] = self.temperature
		return self.temperature
			
	def readHumidity(self):
		try:
			self.humidity = round(self.bme280.humidity, 1)
		except:
			self.humidity = -999
		self.logData['humidity'] = self.humidity
		return self.humidity
			
			
	def readPressure(self):
		try:
			self.pressure = round(self.bme280.pressure, 1)
		except:
			self.pressure = -999
		self.logData['pressure'] = self.pressure
		return self.pressure
			
	def monitor(self):
		while not self.exit:
			self.readTemp()
			self.readHumidity()
			self.readPressure()
			print(self.name + "monitor: ", self.temperature, self.humidity, self.pressure, flush=True)
			if self.fan: 
				for fan in self.attachedFans:
					fan.checkFan(self.temperature)
	
			time.sleep(self.monitorCadence)
	

		
	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
			
	def killMonitor(self):
		print("stopping %s monitor."%self.name, flush=True)
		self.exit = True

class IRSensor(): 
		def __init__(self, name = "IR", config={}):
			self.logData = { }
			self.monitorCadence = 10
			self.skytemperature = -999
			self.ambienttemperature = -999
			self.exit = False
			self.name = name
			try: 
				self.monitorCadence = config['cadence']
			except KeyError:
				self.monitorCadence = 20
			
		def readSky(self):
			try: 
				output = subprocess.check_output(['/home/pi/code/meteopi/readTsky']).decode('UTF-8')
				self.skytemperature = round(float(output.split('\n')[0]),1)
			except Exception as e:
				print(e, flush=True)
				self.skytemperature = -999	
			self.logData['sky'] = self.skytemperature	
			return self.skytemperature
			
		def readAmb(self):
			try: 
				output = subprocess.check_output(['/home/pi/code/meteopi/readTamb']).decode('UTF-8')
				self.ambienttemperature = round(float(output.split('\n')[0]),1)
			except Exception as e:
				print(e)
				self.ambienttemperature = -999
			self.logData['ambient'] = self.ambienttemperature	
			return self.ambienttemperature
			
		def monitor(self):
			while not self.exit:
				self.readSky()
				self.readAmb()
				print(self.name + "monitor: ", self.skytemperature, self.ambienttemperature, flush=True)
				time.sleep(self.monitorCadence)
		
		def startMonitor(self):
			self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
			self.monitorThread.start()
			
		def killMonitor(self):
			print("stopping %s monitor."%self.name, flush=True)
			self.exit = True


class batterySensor():
	def __init__(self, name = "battery", config={}):
		self.current = -999
		self.voltage = -999
		self.currentReadings = []
		self.voltageReadings = []
		self.averageCurrent = -999
		self.averageVoltage = -999

		try: 
			self.monitorCadence = config['cadence']
		except KeyError:
			self.monitorCadence = 5
		try: 
			self.numReadings = config['average']
		except KeyError:
			self.numReadings = 20
		
		
		self.name = name
		self.exit = False
		self.logData = { }
		import adafruit_ina260
		import busio
		self.i2c = busio.I2C(board.SCL, board.SDA)
		self.ina260 = adafruit_ina260.INA260(self.i2c)

	def readCurrentVoltage(self):
		self.current = self.ina260.current
		self.voltage = self.ina260.voltage
		if len(self.currentReadings)==self.numReadings: self.currentReadings.pop(0)
		self.currentReadings.append(self.current)
		self.averageCurrent = sum(self.currentReadings) / len(self.currentReadings)	
		if len(self.voltageReadings)==self.numReadings: self.voltageReadings.pop(0)
		self.voltageReadings.append(self.voltage)
		self.averageVoltage = sum(self.voltageReadings) / len(self.voltageReadings)	
		self.logData['current'] = self.averageCurrent	
		self.logData['voltage'] = self.averageVoltage
		
	def monitor(self):
		while not self.exit:
			self.readCurrentVoltage()
			print("%s monitor: %.2f [%.2f] mA %.2f [%.2f] V"%(self.name, self.current, self.averageCurrent, self.voltage, self.averageVoltage), flush=True)
			time.sleep(self.monitorCadence)
		
	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
		

class domeSensor():
	def __init__(self, name = "dome", config={}):
		# Initialise the dht device, with data pin connected to:
		import adafruit_dht
		self.pin = board.D17
		self.dhtDevice = adafruit_dht.DHT22(board.D17)
		self.temperature = -999
		self.humidity = -999
		self.monitorCadence = config['cadence']
		self.name = "dome"
		self.attachedFan = None
		self.attachedFans = []
		self.fan = False
		self.exit = False
		self.logData = { }
		
	def killMonitor(self):
		print("stopping %s monitor."%self.name, flush=True)
		self.exit = True

	def setFan(self, fan):
		self.fan = True
		self.attachedFan = fan

	def attachFan(self, fan):
		self.attachedFans.append(fan)
		self.fan = True
		
	def readTemp(self):
		try:
			self.temperature = self.dhtDevice.temperature
		except RuntimeError as error:
			# Errors happen fairly often, DHT's are hard to read, just keep going
			# print(error.args[0])
			time.sleep(2.0)
		except Exception as error:
			dhtDevice.exit()
			print("Re-initiliasing dome sensor", flush=True)
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
			print(self.name + "monitor: ", self.temperature, self.humidity, flush=True)
			if self.fan: 
				for fan in self.attachedFans:
					fan.checkFan(self.temperature)
			time.sleep(self.monitorCadence)
		
	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
	

class fanController():
	def __init__(self, config):
		print("config:", config)
		self.GPIO = config['GPIO']
		self.name = config['name']
		self.triggerTemperature = config['temperatureUpper']
		self.hysterisis = config['temperatureUpper'] - config['temperatureLower']
		GPIO.setmode(GPIO.BCM) # Use BCM pin numbering
		GPIO.setup(self.GPIO, GPIO.OUT, initial=GPIO.LOW)
		self.fanOn = False
		
	def checkFan(self, temp):
		if temp>self.triggerTemperature: 
			if not self.fanOn:
				print("Input temperature is above %d... Turning on %s fan."%(self.triggerTemperature, self.name), flush=True)
				self.on()
		if temp<self.triggerTemperature-self.hysterisis:
			if self.fanOn:
				print("Input temperature is below %d... Turning off %s fan."%(self.triggerTemperature-self.hysterisis, self.name), flush=True)
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
	
