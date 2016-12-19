if [ -z $1 ]; then
  BLINKS=0
else
  BLINKS=$1
fi


echo $BLINKS

read() {   # address
  ./i2cget -y 1 0x44 $1 | tr a-z A-Z | sed s/0X/0x/
}
write() {  # address value
  A=$1
  V=$2
  R=`read $A`
  while [ "$R" != "$V" ]; do
    ./i2cset -y 1 0x44 $A $V
    R=`read $A`
  done
}

init() {
  write 0x0b 0x55  # configure 12-15 to outputs
  write 0x0c 0x55  # configure 16-19 to outputs
  write 0x04 0x01  # exit standby
}

set() {   # led# 0|1
  write 0x4c `printf 0x%02X $(((~($2 << $1))&0xFF))`
}
 
off() {
  write 0x4c 0xFF 
}
 
init
off
off

for i in {0..7}; do
  echo $i ...
  for j in `seq 0 $BLINKS`; do
    set $i 0 
    sleep 1
    set $i 1
    sleep 1
  done
done

