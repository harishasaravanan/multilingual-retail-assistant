import sys, wave, time, httpx
H = {"Authorization": "Bearer dev-device"}
B = "http://127.0.0.1:8000"
for f in sys.argv[1:]:
    w = wave.open(f)
    assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2), \
        "convert: ffmpeg -i in.wav -ar 16000 -ac 1 out.wav"
    pcm = w.readframes(w.getnframes())
    c = httpx.Client(timeout=60)
    sid = c.post(B + "/voice-query/start", headers=H).json()["session_id"]
    for i in range(0, len(pcm), 6400):
        c.post(f"{B}/voice-query/{sid}/chunk", headers=H, content=pcm[i:i+6400])
    t = time.time()
    d = c.post(f"{B}/voice-query/{sid}/end", headers=H).json()
    print(f, d["status"], d["language"], d["product_id"], d["confidence"], round(time.time()-t, 2), "s")
