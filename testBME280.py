#!/usr/bin/env python3

import datetime
import time
import board
import busio


# Initialise the bme280
address = "0x77"
from adafruit_bme280 import basic as adafruit_bme280
i2c = board.I2C()  # uses board.SCL and board.SDA
decAddress = int(address, 16)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address = decAddress)

while True:
	now = datetime.datetime.now()

	temperature = round(bme280.temperature, 1)
	pressure = round(bme280.pressure, 1)
	humidity = round(bme280.humidity, 1)
	print('%s - %.1f %sC\t %.1f hPa\t %.1f %%'%(now, temperature, '\u00b0', pressure, humidity))
	time.sleep(5)
