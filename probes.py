import os
import threading
import time
import traceback

class OWFS(object):
    def __init__(self, path):
        self.path = path
        print ("OWFS init from %s" % (path))
        
    def read(self, file):
        with open("%s/%s" % (self.path, file)) as f:
            v = float(f.readline())
            print ("OWFS read %s from %s: %s" % (file, self.path, v))
            return v

    def destroy(self):
        pass

class DS18B20(OWFS):
    def __init__(self, path):
        OWFS.__init__(self, path)

        self.temp_cache = None

        self.thread_cancel = False
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def loop(self):
        print ("Thread %s starting" % (self))
        try:
            while not self.thread_cancel:
                self.temp_cache = self.read("temperature")
                time.sleep(1)
        except Exception:
            traceback.print_exc()
        print ("Thread %s is done" % (self))

    def temperature(self):
        return self.temp_cache

    def destroy(self):
        self.thread_cancel = True

    def __str__(self):
        return "DS18B20(%s)" % (self.path)

max_sensors = 9

sensors = max_sensors * [None]

def scan():
    for bus in range(0, 8):
        busdir = "/owfs/bus.0/bus.%d" % (bus)
        # 28 is the device code for the DS18B20
        devs = list(filter(lambda d: d.startswith("28."), os.listdir(busdir)))
        if len(devs) > 1:
            raise Exception("Only one device per bus supported")
        if len(devs) > 0:
            dp = "%s/%s" % (busdir, devs[0])
            if sensors[bus] is None or sensors[bus].path != dp:
                print ("Found new device %s" % (dp))
                sensors[bus] = DS18B20(dp)
        else:
            if sensors[bus] is not None:
                sensors[bus].destroy()
                sensors[bus] = None
                           
def value(sel):
    # 3 and 2 are backwards
    smap = [1,2,4,3]
    i = list(map(lambda x: "t%d" % (x), smap)).index(sel)
    if sensors[i] is None:
        v = 0
    else:
        try:
            v = sensors[i].temperature()
        except Exception:
            traceback.print_exc()
            v = 0
    print ("%s: %s" % (sensors[i], v))
    return v
