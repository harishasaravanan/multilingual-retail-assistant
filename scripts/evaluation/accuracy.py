import sys, glob, os, wave, subprocess, httpx, collections
H = {"Authorization": "Bearer dev-device"}
B = "http://127.0.0.1:8000"
c = httpx.Client(timeout=60)
hit, tot, misses = collections.Counter(), collections.Counter(), []
for f in sorted(glob.glob("tests/test_dataset/*.wav")):
    parts = os.path.basename(f)[:-4].split("_")
    if len(parts) < 3 or not parts[0].startswith("P"):
        print("skip (bad name):", f); continue
    pid, style = parts[0], "_".join(parts[1:-1])
    tmp = "/tmp/_t.wav"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",f,"-ar","16000","-ac","1","-sample_fmt","s16",tmp], check=True)
    w = wave.open(tmp); pcm = w.readframes(w.getnframes())
    sid = c.post(B+"/voice-query/start", headers=H).json()["session_id"]
    for i in range(0, len(pcm), 6400):
        c.post(f"{B}/voice-query/{sid}/chunk", headers=H, content=pcm[i:i+6400])
    d = c.post(f"{B}/voice-query/{sid}/end", headers=H).json()
    tot[style] += 1
    if d["product_id"] == pid: hit[style] += 1
    else: misses.append((f, d["status"], d["product_id"]))
for s in tot: print(s, f"{hit[s]}/{tot[s]}", f"{100*hit[s]/tot[s]:.0f}%")
print("MISSES:"); [print(" ", m) for m in misses]
