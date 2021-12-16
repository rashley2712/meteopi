
import json


class imagedata():
	def __init__(self, debug=False):
		self._filename = "test.json"
		self._imagePath = ""
		self._debug = debug
		self._json = {}

	def setFilename(self, filename):
		self._filename = filename
		
	def load(self):
		input = open(self._filename, 'rt')
		self._json = json.loads(input.read())
		input.close()
		self.setProperties()

	def save(self):
		output = open(self._filename, "wt")
		json.dump(self._json, output, indent=4)
		output.close()

	def setProperty(self, key, value):
		self._json[key] = value
		setattr(self, key, value)

	def show(self):
		for key in self._json.keys():
			print(str(key) + ": " + str(self._json[key]))

	def getJSON(self):
		return self._json

	def setProperties(self):
		for key in self._json.keys():
			self.debugOut(str(key) + ":" + str(self._json[key]))
			setattr(self, key, self._json[key])

	def debugOut(self, message):
	    if self._debug: print(message, flush=True)