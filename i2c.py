import wiringpi2

wiringpi2.wiringPiSetup()

i2c = wiringpi2.I2C()

class I2C(object):
    def __init__(self, address):
        self.fd = i2c.setup(address)
        self.address = address

    def write8(self, reg, val):
        v = -1
        c = 0
        while v < 0:
            v = i2c.writeReg8(self.fd, reg, val)
            c += 1
        #print("%s: write8 %02X <- %02X: %d tries" % (self, reg, val, c))

    def write16(self, reg, val):
        v = -1
        c = 0
        while v < 0:
            v = i2c.writeReg16(self.fd, reg, val)
            c += 1
        #print("%s: write16 %02X <- %04X: %d tries" % (self, reg, val, c))

    def read16(self, reg):
        v = -1
        c = 0
        while v < 0:
            v = i2c.readReg16(self.fd, reg)
            c += 1
        #print("%s: read16 %02X -> %04X: %d tries" % (self, reg, v, c))
        return v

    def write(self, val):
        v = -1
        c = 0
        while v < 0:
            v = i2c.write(self.fd, val)
            c += 1
        #print("%s: write %02X: %d tries" % (self, val, c))

    def __str__(self):
        return "I2C(%02X)" % (self.address)
