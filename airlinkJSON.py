#!/usr/bin/env python3
import matplotlib.pyplot, sys
import argparse, json
import datetime
import time, requests
import numpy

def getJSONfromURL(url):
	response = requests.get(url)
	data = json.loads(response.text)
	#print("%s has the following JSON data"%url)
	#print(str(data))
	response.close()
	return data

def toCelsius(temp):
	return (temp - 32) * 5/9

if __name__ == "__main__":	
	parser = argparse.ArgumentParser(description='Pings the airlink for a JSON data set and logs it. ')
	parser.add_argument('--url', type=str, default="http://192.168.86.115/v1/current_conditions", help='airlink URL.')
	parser.add_argument('-o', '--output', type=str, help="")
	parser.add_argument('-c', '--cadence', type=float, default=180, help="Cadence in seconds. Default is 5s.")
	args = parser.parse_args()

	cadence= args.cadence

	if args.output is None:
		args.output = "airlink.csv"	
	

	outputfile = open(args.output, "at")
	while True:
		jsonResponse = getJSONfromURL(args.url)
		ts = jsonResponse['data']['ts']
		data = jsonResponse['data']['conditions'][0]
		print(json.dumps(data, indent=4))
		temperature = toCelsius(data['temp'])
		humidity = data['hum']
		pm_1 = data['pm_1']
		pm_2p5 = data['pm_2p5']
		pm_10 = data['pm_10']
		print("%d, %.1f, %.1f, %.2f, %.2f, %.2f"%(ts, temperature, humidity, pm_1, pm_2p5, pm_10))
		outputfile.write("%d, %.1f, %.1f, %.2f, %.2f, %.2f\n"%(ts, temperature, humidity, pm_1, pm_2p5, pm_10))
		outputfile.flush()
		time.sleep(cadence)
	
	outputfile.close()
	fileHandle.close()
	data = str(data)
	print(data)
	endOfEntry = '"error": null }'
	startIndex=0
	index = 0
	JSONstring = "["
	airlinkLog = []
	while index!=-1: 
		index = data.find(endOfEntry, startIndex)
		print("Found string at position", index)
		subString= data[startIndex+ len(endOfEntry)-1: index + len(endOfEntry)]
		print(subString)
		startIndex = index+1
		JSONstring+= subString + ",\n"
		entry = json.loads(subString)
		print(entry)

	JSONstring+= "]\n"
	print(JSONstring)
	airlinkData = json.loads(JSONstring)
	sys.exit()


	for i, d in enumerate(data):
		print(i, ": ",d)


	print("Length is:",len(data))

	O2 = []
	heartRate = []
	times = []
	three = []
	movement = []

	# First two lines (of 5 bytes each) are the date and time
	year = data[3] * 256 + data[2]
	month = data[4]
	day = data[5]
	hour = data[6]
	minute = data[7]
	second = data[8]
	print("Year: ", year, "Month:", month, "Day:", day, " - ", hour, ":", minute, ":", second)  
	decimalString = ""
	for c in range(25):
		decimalString+= str(data[c]) + " : " 
	print(decimalString)
	input()
	count = 0
	for i in range(20, len(data), 5):
		print(i, end=' | ')
		decimalString = ""
		for c in range(5):
			decimalString+= str(data[i+c]) + " : " 
		time = (i-20)/5*2
		print(time, decimalString)
		count+=1
		if data[i]==0 or data[i]==255 or data[i+1]==0 or data[i+1]==255:
			#input("bad data?")
			continue
		times.append(time)
		heartRate.append(data[i])
		three.append(data[i+2])
		movement.append(data[i+3])
		O2.append(data[i+1])
		
	print("%d datapoints read\n%d good datapoints"%(count, len(heartRate)))

	# Write to csv format
	startTime = datetime.datetime(year, month, day, hour, minute, second)
	outfile = open(args.output, "wt")
	outfile.write("time, spO2, pulse, movement\n")
	for t, hr, sp, mv in zip(times, O2, heartRate, movement):
		currentTime = startTime + datetime.timedelta(seconds=t)
		outfile.write("%s, %d, %d, %d\n"%((str(currentTime), sp, hr, mv) ))
	outfile.close()
	print("written to file:", args.output)
	matplotlib.pyplot.figure(figsize=(12,6))
	matplotlib.pyplot.plot(times, heartRate, lw=0.4)
	matplotlib.pyplot.plot(times, O2)
	#matplotlib.pyplot.plot(times, three)
	matplotlib.pyplot.plot(times, movement)
	mean = numpy.mean(O2)
	O2 = [ o-mean for o in O2]
	mean = numpy.mean(heartRate)
	matplotlib.pyplot.figure()
	heartRate = [ h-mean for h in heartRate]
	frequency, power = LombScargle(times, O2).autopower(maximum_frequency=0.2)
	matplotlib.pyplot.plot(frequency, power)
	frequency, power = LombScargle(times, heartRate).autopower(maximum_frequency=0.2)
	matplotlib.pyplot.plot(frequency, power, alpha=0.5)
	matplotlib.pyplot.draw()
	matplotlib.pyplot.show()