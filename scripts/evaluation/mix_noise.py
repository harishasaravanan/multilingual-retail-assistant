import sys,glob,os,wave,numpy as np
src,snr,out=sys.argv[1],float(sys.argv[2]),sys.argv[3]
os.makedirs(out,exist_ok=True)
for f in glob.glob(src+"/*.wav"):
    w=wave.open(f);x=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)
    n=np.random.randn(len(x));n*=np.sqrt(np.mean(x**2)/10**(snr/10)/np.mean(n**2))
    y=np.clip(x+n,-32768,32767).astype(np.int16)
    o=wave.open(os.path.join(out,os.path.basename(f)),"wb");o.setnchannels(1);o.setsampwidth(2);o.setframerate(16000);o.writeframes(y.tobytes());o.close()
