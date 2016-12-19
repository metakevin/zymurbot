import time
import argparse
import sys
from i2c import I2C
        
class MAX7300(I2C):
    def __init__(self, address):
        I2C.__init__(self, address)
        self.write8(0x0B, 0x55)  # configure 12-15 to outputs
        self.write8(0x0C, 0x55)  # configure 16-19 to outputs
        self.write8(0x04, 0x01)  # exit standby

    def set(self, pin, val):
        self.write8(0x2c + pin, val)

    def __str__(self):
        return "MAX7300(%s)" % (self.address)
        

class LED(object):
    def __init__(self, label, max73k, pin):
        self.label = label
        self.pin = pin
        self.max73k = max73k

    def set(self, on):
        self.max73k.set(self.pin, 0 if on else 1)
        
    def on(self):
        self.set(True)

    def off(self):
        self.set(False)

    def __str__(self):
        return "LED(%s, %s, %s)" % (self.label, self.max73k, self.pin)


class HT16K33(I2C):
    def __init__(self, address):
        I2C.__init__(self, address)
        self.write(0x21) 
        self.write(0x81)
        # clear buffer
        for d in range(0, 10, 2):
            self.write16(d, 0)

class SegmentX(HT16K33):
    def __init__(self, address, label):
        self.label = label
        HT16K33.__init__(self, address)
            
class Segment4x7(SegmentX):
    digit_bits = [0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x6f]
    def __init__(self, address, label):
        SegmentX.__init__(self, address, label)

    def number(self, n, colon=False):
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
                d = self.digit_bits[int((n/p)%10)]
            elif dot and i >= dot:
                d = self.digit_bits[0]
            else:
                d = 0
            self.write8(fbaddr[i], d | (0x80 if dot == i else 0))
        self.write8(4, 0xFF if colon else 0)
        
    def __str__(self):
        return "Segment4x7(%02X, %s)" % (self.address, self.label)

class Segment4x14(SegmentX):
    digit_bits = [
        0b0000000000111111,
        0b0000000000000110,
        0b0000000011011011,
        0b0000000010001111,
        0b0000000011100110,
        0b0000000011101101, 
        0b0000000011111101,
        0b0000000000000111,
        0b0000000011111111,
        0b0000000011101111]

    minus = 0b0000000011000000

    # Dots are 0,14 2,14 4,14, 6,14
    
    def __init__(self, address, label):
        SegmentX.__init__(self, address, label)

    def number(self, n):
        dot = None
        neg = False
        if n < 0:
            neg = True
            n = -n
        if type(n) == float:
            if n > 100:
                dot = 2 
                n = int(n*10)
            else:
                dot = 1 
                n = int(n*100)
        fbaddr = [0, 2, 4, 6]
        for i, p in enumerate([1000, 100, 10, 1]):
            if n >= p or i == 3:
                d = self.digit_bits[int((n/p)%10)]
            elif dot and i >= dot:
                d = self.digit_bits[0]
            elif neg and i == 0:
                d = self.minus
            else:
                d = 0
            self.write16(fbaddr[i], d | (0x4000 if dot == i else 0))

    def bitmap(self, a, b):
        self.write16(a, b)
        
    def __str__(self):
        return "Segment4x14(%02X, %s)" % (self.address, self.label)

    
led_labels = ["pump_sel", "time_sel", "temp_sel", "alarm", "heat", "cool", "x", "ok"]

max73k = MAX7300(0x44)

leds = dict(map(lambda t: (t[1], LED(t[1], max73k, t[0])), enumerate(led_labels)))

displays = [
    Segment4x14(0x74, "pump"),
    Segment4x7(0x70, "time"),
    Segment4x14(0x71, "temp_input_1"),
    Segment4x14(0x73, "temp_input_2"),
    Segment4x14(0x72, "temp_target"),
]

display = dict(map(lambda s: (s.label, s), displays))

def test_leds(delay=0.1):
    while True:
        for lname in leds:
            l = leds[lname]
            print(l)
            l.on()
            time.sleep(delay)
            l.off()
            time.sleep(delay)

def test_time(inc=0.01):
    v = 0
    while True:
        for d in displays:
            d.number(v)
        v += inc
        time.sleep(0.25)

def test_alpha():

    for d in range(0,8):            
        for i in range(0, 16):
            display["pump"].bitmap(d, 1<<i)
            display["temp_input_1"].number(d)
            display["temp_input_2"].number(i)
            print ("%d %x" % (d, 1<<i)),
            sys.stdin.readline()
            
def test():
    while True:
        li = -1
        for v in range(0, 1000, 1):
            li = (li + 1) % len(leds)
            leds[li].on()
            for d in displays:            
                d.number(v)
            time.sleep(.1)
            leds[li].off()
            time.sleep(.1)

# obsolete ?
mode = {
    "pump_sel": "gpm",
    "time_sel": "up",
    "temp_input_1": "t1",
    "temp_input_2": "t2",
    "temp_setpoint": 1
}
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Panel control")
    parser.add_argument('--test-leds', help="Test LEDs in a loop", action="store_true")
    parser.add_argument('--test-time', help="Test time display in a loop", action="store_true")
    parser.add_argument('--test-alpha', help="Test alpha display in a loop", action="store_true")
    parser.add_argument('-t', '--test-all', help="Test all in a loop", action="store_true")
    args = parser.parse_args()

    if args.test_leds:
        test_leds()
    elif args.test_time:
        test_time()
    elif args.test_alpha:
        test_alpha()
    elif args.test_all:
        test()
    else:
        print("No command")

