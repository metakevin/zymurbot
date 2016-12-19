import wiringpi2
import time

def open(ch):
    wiringpi2.wiringPiSPISetup(ch, 4000)

def read(ch):
    buf = "00" # any 2 bytes
    wiringpi2.wiringPiSPIDataRW(ch, buf)
    # this returns [D0:D7] [D8:D15] (i.e. D0 is the highest order bit if the 16 bit word
    bytes = map(ord, buf)
    word = (bytes[0]<<8) + bytes[1]
    return word
#    revword = int('{:016b}'.format(word)[::-1], 2)
#    return revword

def temp(word):
    # extract bits 3-14 and reverse them (bit 0 is MSB in word)
    return int('{:016b}'.format(word)[3:14][::-1],2)


if __name__ == "__main__":

    open(0)
    open(1)
    
    while True:
        c1 = read(0)
        c2 = read(1)
        print '0: {:016b}   1: {:016b}'.format(c1, c2)
        print "0: %d C   1: %d C"%(temp(c1), temp(c2))
        time.sleep(1)
        
        
    
