write() {
  ./i2cset -y 0 0x1f 0xe1 $1
}

read() {
  write $1
  ./i2cget -y 0 0x1f
} 

show() {
  printf "%-20s" "$1"
  read $2
}


reset() {
  write 0xB4
  read 0xF0
}


config() {
  ./i2cset -y 0 0x1f 0xD2 00 
}


search() {
  ./i2cset -y 0 0x1f 0x78 $1
  ./i2cget -y 0 0x1f
}

devsel() {
  ./i2cset -y 0 0x1f 0xc3 $1
}

show "Status" 0xF0
show "Read Data" 0xE1
show "Channel Selection" 0xD2
show "Configuration" 0xC3

reset
config
reset

for c in 0xf0 0xe1 0xd2 0xc3 0xb4 0xa5 0x96 0x87; do
  echo $c...
  devsel $c
  show
  search 0x00
  search 0x80
done
