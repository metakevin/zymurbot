def decode(b1, b2):
    word = (b1<<8) + b2

    bits = '{:016b}'.format(word)

    temp = (int(bits[5:14][::-1],2)*1.0) / 4.0

    bits = map(int, bits)
    
    print "raw %04X id %d TC present %d  temp %f"%(word, bits[3], bits[4], temp)
            
