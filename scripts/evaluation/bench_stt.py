import os, sys, time, glob, wave, statistics, subprocess
model, threads, folder, n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
os.environ["MRA_WHISPER_MODEL"] = model
os.environ["MRA_WHISPER_THREADS"] = threads
sys.path.insert(0, "backend")
from app import stt_whisper
files = sorted(glob.glob(folder + "/*.wav"))
files = files[::max(1, len(files)//n)][:n]
def pcm(f):
    t = "/tmp/_b.wav"
    subprocess.run(["ffmpeg","-nostdin","-y","-loglevel","error","-i",f,"-ar","16000","-ac","1","-sample_fmt","s16",t], check=True)
    with wave.open(t) as w:
        return w.readframes(w.getnframes())
stt_whisper.transcribe(pcm(files[0]))  # warmup
ts, out = [], []
for f in files:
    d = pcm(f)
    t = time.perf_counter()
    txt = stt_whisper.transcribe(d)
    dt = time.perf_counter() - t
    ts.append(dt)
    out.append(os.path.basename(f) + f" | {dt:.2f}s | " + txt)
ts.sort()
tag = f"{model}_t{threads}" + ("_temp0" if os.environ.get("MRA_TEMP0") else "") + ("_norep" if os.environ.get("MRA_NOREPEAT") else "") + ("_pin" if os.environ.get("PIN") else "")
open(f"results/latency/bench_{tag}.txt", "w").write("\n".join(out))
print(f"{tag}: median {statistics.median(ts):.2f}s  p95 {ts[int(len(ts)*0.95)-1]:.2f}s  n={len(ts)}")
