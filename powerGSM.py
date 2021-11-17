#!/usr/bin/python3

import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BOARD)
GPIO.setup(37, GPIO.OUT)
while True:
	GPIO.output(37, GPIO.LOW)
	time.sleep(4)
	GPIO.output(37, GPIO.HIGH)
	break
GPIO.cleanup()

