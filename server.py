import json
import time
import panel
#import stepper
import probes
import arduino
from pump import pump

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

status_led_state = False

user_gpm = 0

pump_rotation = "cw"

temp_display = {
    "temp sel 1":  {
        "display": "temp_input_1",
        "current": "nil",
        "upper": lambda t1,t2: t1,
        "middle": lambda t1,t2: t2,
        "lower": lambda t1,t2: t1-t2,
        "nil": lambda t1,t2: 0
    },
    "temp sel 2": {
        "display": "temp_input_2",
        "current": "nil",
        "upper": lambda t1,t2: t1,
        "middle": lambda t1,t2: t2,
        "lower": lambda t1,t2: t1-t2,
        "nil": lambda t1,t2: 0
    }
}

def temp_display_cb(control, value):
    temp_display[control.name]["current"] = value

for t in temp_display:
    arduino.inputs.controls[t].add_callback(temp_display_cb)

def panel_update():
    global status_led_state, user_gpm, button_change_count
    status_led_state = not status_led_state
    panel.leds["ok"].set(status_led_state)    

    probes.scan()
    t1 = probes.value("t1")
    t2 = probes.value("t2")
    
    for p in temp_display:
        t = temp_display[p]
        print("temp_display: %s" % (t))
        panel.display[t["display"]].number(t[t["current"]](t1, t2))

    user_gpm, buttons_changed = arduino.get_pump_gpm()

    if buttons_changed:
        arduino.inputs.update()

    disp = user_gpm
    if pump_rotation == "ccw":
        disp = -disp
    panel.display["pump"].number(disp)
    pump.set_gpm_target(user_gpm, pump_rotation)
    
    panel.display["temp_target"].number(pump.volume)

    
def reset_volume(control, value):
    pump.volume = 0
    
arduino.inputs.controls["pump button 1"].add_callback(reset_volume)

pump_tick = 0
def pump_alternate():
    global pump_rotation, pump_tick
    if pump_tick % 30 == 29:
        print("Changing pump rotation")
        if pump_rotation == "cw":
            pump_rotation = "ccw"
        else:
            pump_rotation = "cw"
    panel.display["pump"].rotate(True)
pump_alternate_loop = task.LoopingCall(pump_alternate)
alternating = False

def pump_input_changed(control, value):
    global pump_rotation, alternating
    if control.name == "pump direction":
        if value == "lower":
            alternating = True
            pump_alternate_loop.start(1)
        elif alternating:
            pump_alternate_loop.stop()
            alternating = False
            panel.display["pump"].rotate(False)
        if value == "upper":
            pump_rotation = "cw"
        else:
            pump_rotation = "ccw"

arduino.inputs.controls["pump direction"].add_callback(pump_input_changed)


panel_update_loop = task.LoopingCall(panel_update)
panel_update_loop.start(0.5)

pump_update_loop = task.LoopingCall(pump.update)
pump_update_loop.start(0.1)    


def handle_ajax(args):
    global cur_gpm, motor_dir
    if args['op'] == 'setpump':
        pass
    elif args['op'] == 'reset':
        pass
    elif args['op'] == 'status':
        pass
    elif args['op'] == 'setdir':
        pass
    else:
        print ("Unrecognized operation %s"%(str(args)))


if __name__ == "__main__":

    
    for l in panel.leds:
        panel.leds[l].off()
    
    root = MainPage()

    root.putChild("x", static.File("."))

    site = server.Site(root)
    reactor.listenTCP(80, site)
    reactor.run()



