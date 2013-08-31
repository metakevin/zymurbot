import RPi.GPIO as GPIO
import json
import time

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
        status = {'volume': est_vol(), 'cur_gpm': cur_gpm}
        return json.dumps(status)

    def getChild(self, name, request):
        #print "getChild(%s, %s)"%(name, request)
        if name == "":
            return self
            
        return resource.Resource.getChild(self, name, request)



GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

pin_step = 24
pin_dir = 25

GPIO.setup(pin_step, GPIO.OUT) # STEP
GPIO.setup(pin_dir, GPIO.OUT) # DIRECTION


# stepper is 200 steps per ref
# the G210X is in microstep mode (10 pulses per step)

# 100HZ, ~20 seconds per rev measured
# 100HZ * 20 seconds = 2,000 pulses per rev

# 1,000 HZ = 1000/2000 rev/sec = 60*1000/2000 rev/min = 30 RPM


pwm = GPIO.PWM(pin_step, 1)

vol_accum = 0
cur_gpm = 0
cur_start = 0

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

def start(gpm):
    global cur_gpm, cur_start
    accum_vol()
    cur_gpm = gpm
    cur_start = time.time()
    rpm = gpm_to_rpm(gpm)
    hz = rpm * 33.33333333
    pwm.ChangeFrequency(hz)
    pwm.start(50.0)
    print "Pump running at %f GPM, %f RPM, %f Hz"%(gpm, rpm, hz)

def stop():
    global cur_gpm
    accum_vol()
    cur_gpm = 0
    pwm.stop()
    print "Pump stopped"

dia = 5.5
occvol = 3.22 #cc/inch
rollers = 2
occlen = dia*3.14159265359/rollers
    
# 1 GPM ~= 68 RPM
def rpm_to_gpm(rpm):
    ccm = occvol * occlen * rollers * rpm
    gpm = ccm / 3785
    return gpm

def gpm_to_rpm(gpm):
    ccm = gpm * 3785
    rpm = ccm / (occvol * occlen * rollers)
    return rpm


def handle_ajax(args):
    global cur_gpm
    if args['op'] == 'setpump':
        gpm = float(args['gpm'])
        if gpm == 0:
            stop()
        else:
            start(gpm)
    elif args['op'] == 'reset':
        reset_vol()
    elif args['op'] == 'status':
        pass
    else:
        print "Unrecognized operation %s"%(args['op'])


if __name__ == "__main__":
    root = MainPage()

    root.putChild("x", static.File("."))

    site = server.Site(root)
    reactor.listenTCP(80, site)
    reactor.run()
