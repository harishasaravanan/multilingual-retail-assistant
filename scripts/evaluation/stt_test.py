import sys,time
from faster_whisper import WhisperModel
m=WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=8)
for f in sys.argv[1:]:
    t=time.time()
    segs,info=m.transcribe(f, beam_size=1, vad_filter=True)
    txt=" ".join(s.text for s in segs).strip()
    print(f, info.language, round(info.language_probability,2), "|", txt, "|", round(time.time()-t,2),"s")
