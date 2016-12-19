import argparse
import sys
import time
from i2c import I2C

class Arduino(I2C):
    def __init__(self, address):
        I2C.__init__(self, address)

    def __str__(self):
        return "Arduino @ %02X" % (self.address)

class Register(object):
    def __init__(self, arduino, name, address):
        self.arduino = arduino
        self.name = name
        self.address = address

    def read(self):
        return self.arduino.read16(self.address)

    def write(self, value):
        return self.arduiino.write8(self.address, value)

class UserControl(object):
    def __init__(self, inputs, name):
        self.name = name
        self.inputs = inputs
        self.callbacks = []

    def value(self):
        return None

    def add_callback(self, cb):
        self.callbacks.append(cb)
        
    def changed(self):
        v = self.value()
        print ("%s changed to %s" % (self.name, v))
        for c in self.callbacks:
            c(self, v)
    
class RotarySelector(UserControl):
    def __init__(self, inputs, name, row):
        UserControl.__init__(self, inputs, name)
        self.row = row
        self.sel = None

    def update(self):
        s = self.inputs.row[self.row]&3
        if s != self.sel:
            self.sel = s
            self.changed()
        
    def value(self):
        # the two LSBs of the row indicate the selector state
        # 00 : upper position
        # 01 : middle position
        # 10 : lower position
        # 11 : invalid
        if self.sel == 3:
            raise Exception("Invalid selector value")
        elif self.sel == 0:
            return "upper"
        elif self.sel == 1:
            return "middle"
        elif self.sel == 2:
            return "lower"

class Button(UserControl):
    def __init__(self, inputs, name, row, col):
        UserControl.__init__(self, inputs, name)
        self.row = row
        self.col = col
        self.sel = None

    def update(self):
        s = self.inputs.row[self.row] & (1<<self.col)
        if s != self.sel:
            self.sel = s
            if s:
                # on key down 
                self.changed()

    def value(self):
        return "on" if self.sel else "off"
    
class UserInputs(object):
    def __init__(self, arduino):
        self.controls = {}
        self.row = [0] * 6
        self.registers = [Register(arduino, "input row %s" % (r), 0xc0 + r) for r in range(0,6)]

        selector_names = ["pump direction", "timer", "temp sel 1", "temp sel 2", "accumulator"]
        for i in range(0,5):
            self.add_control(RotarySelector(self, selector_names[i], i))

        basic_buttons = [
            ("pump button 1", 5, 3),
            ("pump button 2", 5, 5),
            ("time button 1", 5, 2),
            ("time button 2", 5, 4),
            ("temp 1 button", 5, 1)
        ]
        for b in basic_buttons:
            self.add_control(Button(self, *b))

    def add_control(self, control):
        self.controls[control.name] = control

    def update(self):
        for i, r in enumerate(self.registers):
            self.row[i] = (r.read()&0xFF)
        for c in self.controls:
            self.controls[c].update()
            
    
arduino = Arduino(0x23)
registers = list(map(lambda t: Register(*t),
                     [(arduino, "pump pot", 0),
                      (arduino, "heater relay", 0x80),
                      (arduino, "chiller relay", 0x81),
                      (arduino, "countdown", 0xff)]))
for r in range(0,6):
    registers.append(Register(arduino, "raw row %s" % (r), 0xd0 + r))
    registers.append(Register(arduino, "row %s" % (r), 0xc0 + r))
    
register_map = dict(map(lambda r: (r.name, r), registers))

inputs = UserInputs(arduino)


def get_pump_gpm():
    v = register_map["pump pot"].read()
    p = v & 0x3FF;
    max_gpm = 4
    scaled = (float(p) / float(0x3ff)) * max_gpm
    print ("pump pot: %03X = scaled %.2f changed %s" % (p, scaled, v&0x8000))
    return scaled, (True if (v&0x8000) else False)

def set_relay(relay_name, on):
    register_map[relay_name].write(1 if on else 0)

def print_registers(regs):
    for r in registers:
        if regs is not None and len(regs) > 0 and r.name not in regs:
            continue
        print ("%-20s %02X %04X" % (r.name, r.address, r.read()))

def binfmt(v):
    s = ""
    for i in range(7, -1, -1):
        if v & (1<<i):
            s += "1"
        else:
            s += "0"
    return s

def show_buttons():
    rows = [register_map["row %s" % (r)].read() for r in range(0,6)]
    if rows[0] > 0xFF:
        print ("Changed")
    else:
        print ("Unchanged")
    for r in range(0, 6):
        print ("%d: %s" % (r, binfmt(rows[r]&0xFF)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Arduino interface")
    parser.add_argument('--read', help="Read Arduino registers", action="store_true")
    parser.add_argument('--loop', help="Read in a loop", action="store_true")
    parser.add_argument('--reg', help="Read only these registers", action="append")
    parser.add_argument('--bin', help="Read this register in binary")
    parser.add_argument('--buttons', help="Show button values", action='store_true')
    parser.add_argument('--input-test', help="Poll user inputs", action='store_true')
    
    args = parser.parse_args()

    if args.bin:
        v = register_map[args.bin].read()
        print ("%s: %s %s" % (args.bin,
                              binfmt(v>>8),
                              binfmt(v&0xFF)))
    elif args.buttons:
        show_buttons()
    elif args.read:
        while True:
            print_registers(args.reg)
            if not args.loop:
                break
            time.sleep(.1)
    elif args.input_test:
        while True:
            inputs.update()            
    else:
        print("No command")

