import sys,serial,wave,struct,os
import numpy as np
out=sys.argv[1]; os.makedirs(out,exist_ok=True)
PH=[("Where is Parle-G biscuits?","en"),("Parle-G biscuit kahan milega?","hi"),("Parle-G biscuit enga irukku?","ta-en"),("Parle-G பிஸ்கட் எங்கே இருக்கு?","ta")]*5
N=min(len(PH),int(sys.argv[2]) if len(sys.argv)>2 else len(PH))
s=serial.Serial('/dev/serial/by-id/usb-Silicon_Labs_J-Link_OB_000440353914-if00',115200,timeout=120)
s.reset_input_buffer()
done=0; rnd=0; hx=[]; on=False; rate=16000; det=0; res=[]
def save(rnd,hx,rate):
    h=''.join(hx)
    v=[int(h[i:i+4],16) for i in range(0,len(h)-3,4)]
    v=[x-65536 if x>=32768 else x for x in v]
    w=wave.open('%s/u%02d.wav'%(out,rnd),'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(struct.pack('<%dh'%len(v),*v)); w.close()
    a=np.array(v,dtype=float)
    tail=int(np.sqrt((a[-4000:]**2).mean())) if len(a) else 0
    return len(a)/rate,int(np.abs(a).max()) if len(a) else 0,tail
while done<N:
    raw=s.readline()
    if raw==b'':
        print('no data for 120 s, stopping'); break
    l=raw.decode(errors='ignore').strip()
    if not l: continue
    if 'ERR' in l: print(l)
    if l=='WAIT':
        rnd+=1; hx=[]; on=False
        if rnd>N: break
        print('>>> (%d/%d) HOLD BTN0 and say: %s   [%s]   release when done'%(rnd,N,PH[rnd-1][0],PH[rnd-1][1]),flush=True); continue
    if l=='REC':
        hx=[]; on=False; continue
    if l=='SILENCE':
        done+=1; res.append((rnd,'MISSED (nothing sent)')); print('    %d: MISSED (nothing sent)'%rnd,flush=True); continue
    if l.startswith('START'): on=True; rate=int(l.split()[2]); continue
    if l=='END' and on:
        d,pk,tail=save(rnd,hx,rate); cut=tail>1500; ok=d>=1.0 and pk>1500 and not cut; det+=ok; done+=1; on=False
        why='DETECTED' if ok else ('MISSED (cut off at end: spoke too late or too long)' if cut else 'MISSED (too short)')
        res.append((rnd,'%.2f s peak %d %s'%(d,pk,why))); print('    %d: %s'%(rnd,res[-1][1]),flush=True); continue
    if on: hx.append(l)
print('SUMMARY')
for r in res: print(r[0],r[1])
print('VAD detected',det,'/',N)
