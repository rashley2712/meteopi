
import json, os, requests


class config():
	def __init__(self, filename="meteopi.cfg", debug=False):
		self._db = {}
		self.filename = filename
		self._debug = debug
		self._json = {}
		self._local = False
		self._logger = None
		self._service = False
		
	def load(self):
		configFile = open(self.filename, 'rt')
		self._json = json.loads(configFile.read())
		configFile.close()
		self.setProperties()
		
	def setProperties(self):
		for key in self._json.keys():
			self.debugOut(str(key) + ":" + str(self._json[key]))
			setattr(self, key, self._json[key])
		
	def getProperties(self):
		self.debugOut("I have the following properties:")
		self._propertyList = []
		for key in self.__dict__.keys():
			if not key.startswith('_'): self._propertyList.append(key)
		return self._propertyList
	
	def refresh(self):
		configURL = os.path.join(self.baseURL, "runtime.cfg")
		if self.local: configURL = os.path.join(self.localURL, "runtime.cfg")
		self.debugOut("Fetching config from " + configURL) 
		response = requests.get(configURL)
		if response.status_code != 200: 
			self.debugOut(str(response.status_code) + ": " +  response.reason)
			return -1 
		data = json.loads(response.text)
		response.close()
		self.db = data
		self.setProperties()
		return

	def debugOut(self, message):
	    if self._debug: print(message, flush=True)