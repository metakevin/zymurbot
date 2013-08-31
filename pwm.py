import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

pin_step = 24
pin_dir = 25

GPIO.setup(pin_step, GPIO.OUT) # STEP
GPIO.setup(pin_dir, GPIO.OUT) # DIRECTION


pwm = GPIO.PWM(pin_step, 1)

def start(hz):
    pwm.ChangeFrequency(hz)
    pwm.start(50.0)

def stop():
    pwm.stop()
    

import code

try:
    interpreter = code.InteractiveConsole(locals())
    interpreter.interact("peristaltic pump")
finally:
    GPIO.cleanup()
    


