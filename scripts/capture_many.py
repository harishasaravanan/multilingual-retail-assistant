import sys,serial,wave,struct,os
import numpy as np
N=int(sys.argv[1]); out=sys.argv[2]; os.makedirs(out,exist_ok=True)
PORT='/dev/serial/by-id/usb-Silicon_Labs_J-Link_OB_000440353914-if00'
s=serial.Serial(PORT,115200,timeout=120)
print('ready. In Studio press F8 ONCE, then speak at every SPEAK NOW')
done=0; rnd=0; hx=[]; on=False; rate=16000; det=0; res=[]
def save(rnd,hx,rate):
    h=''.join(hx)
    v=[int(h[i:i+4],16) for i in range(0,len(h)-3,4)]
    v=[x-65536 if x>=32768 else x for x in v]
    f='%s/u%02d.wav'%(out,rnd)
    w=wave.open(f,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(struct.pack('<%dh'%len(v),*v)); w.close()
    pk=int(np.abs(np.array(v)).max()) if v else 0
    return len(v)/rate,pk
while done<N:
    raw=s.readline()
    if raw==b'':
        print('no data for 120 s, stopping'); break
    l=raw.decode(errors='ignore').strip()
    if not l: continue
    if 'ERR' in l: print(l)
    if l=='REC':
        rnd+=1; hx=[]; on=False
        print('>>> SPEAK NOW (%d/%d)'%(rnd,N),flush=True); continue
    if l=='SILENCE':
        done+=1; res.append((rnd,'MISSED (board sent nothing)')); print('    %d: MISSED (silence)'%rnd); continue
    if l.startswith('START'):
        on=True; rate=int(l.split()[2]); continue
    if l=='END' and on:
        d,pk=save(rnd,hx,rate); ok=d>0.5 and pk>1500; det+=ok; done+=1; on=False
        res.append((rnd,'%.2f s peak %d %s'%(d,pk,'DETECTED' if ok else 'MISSED')))
        print('    %d: %s (next round starting)'%(rnd,res[-1][1]),flush=True); continue
    if on: hx.append(l)
print('SUMMARY')
for r in res: print(r[0],r[1])
print('VAD detected',det,'/',N)
