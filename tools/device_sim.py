import sys, os, json, time, wave, urllib.request, urllib.error
BASE = os.environ.get("MRA_URL", "http://127.0.0.1:8000")
TOK = os.environ.get("MRA_DEVICE_TOKEN", "")

def call(path, method="POST", body=b"", token=TOK):
    h = {"Content-Type": "application/octet-stream"}
    if token is not None:
        h["Authorization"] = "Bearer " + token
    r = urllib.request.Request(BASE + path, data=body if method == "POST" else None, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as x:
            raw = x.read()
            return x.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: return e.code, json.loads(raw)
        except Exception: return e.code, {}

def pcm(path):
    with wave.open(path) as w:
        assert (w.getframerate(), w.getsampwidth(), w.getnchannels()) == (16000, 2, 1), "need 16 kHz 16-bit mono WAV"
        return w.readframes(w.getnframes())

def replay(path, chunk=32000):
    data = pcm(path)
    t0 = time.perf_counter()
    st, j = call("/voice-query/start"); sid = j["session_id"]
    for i in range(0, len(data), chunk):
        st, _ = call(f"/voice-query/{sid}/chunk", body=data[i:i+chunk]); assert st == 204, st
    t1 = time.perf_counter()
    st, out = call(f"/voice-query/{sid}/end")
    t2 = time.perf_counter()
    print(f"end -> HTTP {st}  status={out.get('status')}  transcript={out.get('transcript')!r}")
    print(f"upload {t1-t0:.2f}s  end(STT+pipeline) {t2-t1:.2f}s  total {t2-t0:.2f}s")
    print("timings:", out.get("timings"))
    return out

def r11():
    res = []
    def chk(name, got, want): res.append(got == want); print(("PASS" if got == want else "FAIL"), name, "got", got, "want", want)
    chk("no token /start", call("/voice-query/start", token=None)[0], 401)
    chk("bad token /start", call("/voice-query/start", token="wrong")[0], 401)
    chk("bad token /chunk", call("/voice-query/x/chunk", body=b"\0\0", token="wrong")[0], 401)
    chk("unknown session /chunk", call("/voice-query/nope/chunk", body=b"\0\0")[0], 404)
    chk("unknown session /end", call("/voice-query/nope/end")[0], 404)
    sid = call("/voice-query/start")[1]["session_id"]
    chk("odd-length chunk", call(f"/voice-query/{sid}/chunk", body=b"\0\0\0")[0], 422)
    call(f"/voice-query/{sid}/chunk", body=b"\0\0" * 1600); call(f"/voice-query/{sid}/end")
    chk("chunk after end", call(f"/voice-query/{sid}/chunk", body=b"\0\0")[0], 410)
    chk("end twice", call(f"/voice-query/{sid}/end")[0], 410)
    print(f"R11: {sum(res)}/{len(res)} passed")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "r11": r11()
    elif len(sys.argv) > 1: replay(sys.argv[1])
    else: print("usage: device_sim.py clip.wav | r11")
