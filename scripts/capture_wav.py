import sys,serial,wave,struct
s=serial.Serial('/dev/serial/by-id/usb-Silicon_Labs_J-Link_OB_000440353929-if00',115200,timeout=60)
print('waiting; press F8 in Studio, then speak for 3 s')
hx=[];rate=16000;on=False
while True:
    l=s.readline().decode(errors='ignore').strip()
    if l.startswith('START'): on=True; rate=int(l.split()[2]); continue
    if l.startswith('END'): break
    if on: hx.append(l)
h=''.join(hx)
v=[int(h[i:i+4],16) for i in range(0,len(h)-3,4)]
v=[x-65536 if x>=32768 else x for x in v]
w=wave.open(sys.argv[1],'wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(struct.pack('<%dh'%len(v),*v));w.close()
print(len(v),'samples',round(len(v)/rate,2),'s')
