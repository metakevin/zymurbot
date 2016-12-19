import json
import time
import wiringpi2

from twisted.web import server, resource, static
from twisted.internet import reactor, task



class MainPage(resource.Resource):
    isLeaf = False
    allowedMethods = ("GET", "POST")
    def render_GET(self, request):
        with open("main.html", "r") as f:
            return f.read()

    def render_POST(self, request):
        #print "Got a post: " + str(request.args)
        # not sure why the ajax query has each value as an array, but remove that
        flat = {}
        for a in request.args:
            flat[a] = request.args[a][0]
            #print "arg[%s] = %s"%(a, str(flat[a]))
        handle_ajax(flat)
        status = {'volume': est_vol(),
                  'cur_gpm': cur_gpm,
                  'cur_rpm': round(gpm_to_rpm(cur_gpm)),
                  'direction': pin_to_dir(motor_dir).upper()}
        return json.dumps(status)

    def getChild(self, name, request):
        #print "getChild(%s, %s)"%(name, request)
        if name == "":
            return self
            
        return resource.Resource.getChild(self, name, request)



pin_step = 1 # GPIO1, BCM pin 18 (labeled on pi plate 18)
pin_dir = 6 # GPIO6, BCM pin 25 (labeled on pi plate 25)
pin_statusled = 3 # GPI3, BCM pin 22

wiringpi2.wiringPiSetup()

wiringpi2.pinMode(pin_dir, wiringpi2.GPIO.OUTPUT)
wiringpi2.pinMode(pin_step, wiringpi2.GPIO.PWM_OUTPUT)
wiringpi2.pinMode(pin_statusled, wiringpi2.GPIO.OUTPUT)

i2c = wiringpi2.I2C()
ard = i2c.setup(0x23)  # arduino


# active low LED
led_state = 0
def toggle():
    global led_state
    led_state = 0 if led_state is 1 else 1
    wiringpi2.digitalWrite(pin_statusled, led_state)

toggle()
 
def set_gpm(gpm):
    if gpm == 0:
        stop()
    else:
        start(gpm, motor_dir)

lsg = i2c.setup(0x70)
digit_bits = [0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x6f]

def display_init():
    i2c.write(lsg, 0x21)
    i2c.write(lsg, 0x81)
    # clear display
    for d in range(0, 10, 2):
        i2c.writeReg16(lsg, d, 0)

def display_num(n, colon=False):
    dot = None
    if type(n) == float:
        if n > 100:
            dot = 2 
            n = int(n*10)
        else:
            dot = 1 
            n = int(n*100)
    fbaddr = [0, 2, 6, 8]
    for i, p in enumerate([1000, 100, 10, 1]):
        if n >= p or i == 3:
            d = digit_bits[(n/p)%10]
        elif i >= dot:
            d = digit_bits[0]
        else:
            d = 0
        i2c.writeReg8(lsg, fbaddr[i], d | (0x80 if dot == i else 0))
    i2c.writeReg8(lsg, 4, 0xFF if colon else 0)
   
pot = 0
pot_gpm = 0
pot_samples=[]
def arduino_read():
    global pot_gpm, pot, pot_samples
    potreg = i2c.readReg16(ard, 0)
    if potreg < 0 or potreg > 1023:
        print "overrange %s" % (potreg)
        potreg = 0
    if potreg > 400:
        potreg = 400
    flen = 10
    decay = 0.95
    pot_samples = [potreg] + pot_samples[:flen]
    pot = sum(map(lambda i: i[1]*(pow(decay,i[0])), enumerate(pot_samples)))/sum(map(lambda p: pow(decay, p), range(0,len(pot_samples))))
    #pot = round(float(sum(pot_samples))/len(pot_samples))

    gpm = pot / 100.0
    print "ard: potreg %s pot %s gpm %s pot_gpm %s" % (potreg, pot, gpm, pot_gpm)
    if pot_gpm != gpm:
        set_gpm(gpm)
        pot_gpm = gpm

blink = task.LoopingCall(toggle)
blink.start(0.5)

ardpoll = task.LoopingCall(arduino_read)
reactor.callLater(5, lambda: ardpoll.start(0.2))

dmode = "vol"
def display_update():
   global dmode
   if dmode == "gpm":
       display_num(cur_gpm)
   elif dmode == "vol":
       display_num(est_vol())

display_init()
dispup = task.LoopingCall(display_update)
reactor.callLater(5, lambda: dispup.start(0.1))





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


def handle_ajax(args):
    global cur_gpm, motor_dir
    if args['op'] == 'setpump':
        gpm = float(args['gpm'])
        set_gpm(gpm)
    elif args['op'] == 'reset':
        reset_vol()
    elif args['op'] == 'status':
        pass
    elif args['op'] == 'setdir':
        start(cur_gpm, dir_to_pin(args['direction']))
    else:
        print "Unrecognized operation %s"%(str(args))


if __name__ == "__main__":
    root = MainPage()

    root.putChild("x", static.File("."))

    site = server.Site(root)
    reactor.listenTCP(80, site)
    reactor.run()



