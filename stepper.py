import wiringpi2

pin_step = 1 # GPIO1, BCM pin 18 (labeled on pi plate 18)
pin_dir = 6 # GPIO6, BCM pin 25 (labeled on pi plate 25)
pin_statusled = 3 # GPI3, BCM pin 22

wiringpi2.wiringPiSetup()

wiringpi2.pinMode(pin_dir, wiringpi2.GPIO.OUTPUT)
wiringpi2.pinMode(pin_step, wiringpi2.GPIO.PWM_OUTPUT)
wiringpi2.pinMode(pin_statusled, wiringpi2.GPIO.OUTPUT)

i2c = wiringpi2.I2C()


wiringpi2.pwmSetMode(wiringpi2.GPIO.PWM_MODE_MS) # mark/space i.e. run of 1s followed by run of 0s
# the base clock is 19.2MHz and this is a divider
pwm_base = 19.2*1000000
pwm_divider = 16 # 1.2 MHz
wiringpi2.pwmSetClock(pwm_divider) 
# the range is 0-1024 which is another divider.  so with a 1.2MHz clock we can go as low as 1172Hz

def set_motor(hz, direction):
    wiringpi2.digitalWrite(pin_dir, direction)
    
    if hz == 0:
        wiringpi2.pwmWrite(pin_step, 0)
        return
    # if hz is 2000 (60 RPM) we want
    # x = 1200000/2000 = 600
    r = int((pwm_base/pwm_divider)/hz)
    
    wiringpi2.pwmSetRange(r)
    wiringpi2.pwmWrite(pin_step, r/2) # 50% duty cycle

# stepper is 200 steps per ref
# the G210X is in microstep mode (10 pulses per step)

# 100HZ, ~20 seconds per rev measured
# 100HZ * 20 seconds = 2,000 pulses per rev

# 1,000 HZ = 1000/2000 rev/sec = 60*1000/2000 rev/min = 30 RPM


# gpio mode 1 pwm
# gpio pwm-ms
# gpio pwmc 32  # 19.2MHz / 32 = 600kHz
# gpio pwm 1 1 # not balanced but works

# gpio pwmr 10000  # 600kHz / 10,000 = 60Hz

# gpio pwmr 600  # 600kHz / 600 = 1000Hz

# pwmc 16 pwmr 600 2kHz

vol_accum = 0
cur_gpm = 0
cur_start = 0
motor_dir = 1

def reset_vol():
    global vol_accum, cur_start
    vol_accum = 0
    cur_start = time.time()

def accum_vol():
    global cur_start, vol_accum
    now = time.time()
    if cur_start != 0:
        duration = now - cur_start;
        vol_accum += cur_gpm * duration / 60
    cur_start = now
    
def est_vol():
    if cur_start != 0:
        now = time.time()
        duration = now - cur_start;
        return vol_accum + cur_gpm * duration / 60
    else:
        return 0

p2d = ['cw', 'ccw']
def pin_to_dir(p):
    return p2d[p]

def dir_to_pin(d):
    return p2d.index(d.lower())
        
def set_direction(d):
    global motor_dir
    dl = d.lower()
    if dl == 'cw' or dl == '0':
        motor_dir = 0
    elif dl == 'ccw' or dl == '1':
        motor_dir = 1
    else:
        print "unrecognized direction %s" % (d)

def start(gpm, md):
    global cur_gpm, cur_start, motor_dir

    if motor_dir != md and cur_gpm != 0:
        print "braking first"
        reactor.callLater(0.3, start, 0, motor_dir)
        reactor.callLater(0.6, start, gpm/2, md)
        reactor.callLater(0.9, start, gpm, md)
        gpm /= 2 # drop to half speed right away
    else:
        motor_dir = md
    
    accum_vol()
    cur_gpm = gpm
    cur_start = time.time()
    rpm = gpm_to_rpm(gpm)
    hz = rpm * 33.33333333
    set_motor(hz, motor_dir)
    print "Pump running %s at %f GPM, %f RPM, %f Hz"%(pin_to_dir(motor_dir), gpm, rpm, hz)

def stop():
    global cur_gpm
    accum_vol()
    cur_gpm = 0
    set_motor(0, motor_dir)
    print "Pump stopped"

dia = 5.5
occvol = 3.22 #cc/inch
rollers = 2
occlen = dia*3.14159265359/rollers
# observed volumes:
# 1 GPM .4 gallons = 1 liter actual
# 2 GPM .4 gallons = 1 liter actual
# .1 GPM .39 gallons = 1 liter actual
# 1 liter = .264 gallons
correction = .264/.4
    
# 1 GPM ~= 68 RPM
def rpm_to_gpm(rpm):
    ccm = occvol * occlen * rollers * rpm
    gpm = ccm / 3785
    return gpm*correction

def gpm_to_rpm(gpm):
    ccm = gpm * 3785
    rpm = ccm / (occvol * occlen * rollers)
    return rpm/correction


