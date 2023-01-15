#!/usr/bin/env python3

import datetime
import time
import board
import busio
import adafruit_ina260

i2c = busio.I2C(board.SCL, board.SDA)
ina260 = adafruit_ina260.INA260(i2c)

while True:
	now = datetime.datetime.now()
	print(now)
	print("Current: %.2f mA Voltage: %.2f V Power:%.2f mW"% (ina260.current, ina260.voltage, ina260.power))
	time.sleep(5)
