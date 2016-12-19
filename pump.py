import time
import wiringpi2

wiringpi2.wiringPiSetup()


class Pump(object):
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

    # allow faster change towards zero
    max_delta_pos = 0.1
    max_delta_neg = 0.4
    
    def __init__(self):
        self.pin_step = 1 # GPIO1, BCM pin 18 (labeled on pi plate 18)
        self.pin_dir = 6 # GPIO6, BCM pin 25 (labeled on pi plate 25)
        # the base clock is 19.2MHz and this is a divider
        self.pwm_base = 19.2*1000000
        self.pwm_divider = 16 # 1.2 MHz

        wiringpi2.pinMode(self.pin_dir, wiringpi2.GPIO.OUTPUT)
        wiringpi2.pinMode(self.pin_step, wiringpi2.GPIO.PWM_OUTPUT)
        wiringpi2.pwmSetMode(wiringpi2.GPIO.PWM_MODE_MS) # mark/space i.e. run of 1s followed by run of 0s

        self.target = 0
        self.current = 0
        self.last_accum = time.time()
        self.volume = 0

    def set_hz(self, hz, direction):
        wiringpi2.digitalWrite(self.pin_dir, direction)

        if hz == 0:
            wiringpi2.pwmWrite(self.pin_step, 0)
            return
        # if hz is 2000 (60 RPM) we want
        # x = 1200000/2000 = 600
        r = (self.pwm_base/self.pwm_divider)/hz
        print ("Pump Hz %s range %s" % (hz, r))
        wiringpi2.pwmSetRange(int(r))
        wiringpi2.pwmWrite(self.pin_step, int(r/2)) # 50% duty cycle

    def set_motor(self, gpm, motor_dir):
        rpm = self.gpm_to_rpm(gpm)
        hz = rpm * 33.33333333
        self.set_hz(hz, motor_dir)

    def set_gpm(self, gpm):
        self.set_motor(abs(gpm), 1 if gpm > 0  else 0)
        
    def set_gpm_target(self, gpm, direction):
        if direction not in ["cw", "ccw"]:
            raise Exception("bad direction")
        if direction == "cw":
            self.target = gpm
        else:
            self.target = -gpm

    def gpm_to_rpm(self, gpm):
        ccm = gpm * 3785
        rpm = ccm / (self.occvol * self.occlen * self.rollers)
        v = rpm/self.correction
        if v < 0.01:
            v = 0
        return v

    def update(self):
        # call periodically to update pwm value based on
        # target and current position
        n = self.current
        if abs(self.target) > abs(self.current):
            max_d = self.max_delta_pos
        else:
            max_d = self.max_delta_neg
            
        if abs(self.target - self.current) <= max_d:
            n = self.target
        elif self.target > self.current:
            print ("increase")
            n += min(max_d, self.target - self.current)
        else:
            print ("decrease")
            n -= min(max_d, self.current - self.target)
        # if not ((n < 0) ^ (self.current >= 0)):
        #     # will be changing direction, stop at 0
        #     print ("zero-cross %s %s" % (n, self.current))
        #     n = 0
        print ("target %.2f was %.2f now %.2f" % (
            self.target, self.current, n))
        now = time.time()
        self.volume += self.current * (now - self.last_accum) / 60
        self.last_accum = now
        self.current = n
        self.set_gpm(n)
    
pump = Pump()
