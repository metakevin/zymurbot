#!/usr/bin/python2.7

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

pin_step = 24
pin_dir = 25

GPIO.setup(pin_step, GPIO.OUT) # STEP
GPIO.setup(pin_dir, GPIO.OUT) # DIRECTION

def set_gpio(pin, v):
    if v:
        GPIO.output(pin, GPIO.HIGH)
    else:
        GPIO.output(pin, GPIO.LOW)
def set_dir(v):
    set_gpio(pin_dir, v)
def set_step(v):
    set_gpio(pin_step, v)

# while True:
#     l = [(True,True),(True,False),(False,True),(False,False)]
#     for s,d in l:
#         set_step(s)
#         set_dir(d)        
#         time.sleep(1/10.0)

try:
    set_dir(True)
    interval = 1000.0
    while True:
        set_step(True)
        time.sleep(1/interval)
        set_step(False)
        time.sleep(1/interval)
finally:
    GPIO.cleanup()
    
    
    
    
