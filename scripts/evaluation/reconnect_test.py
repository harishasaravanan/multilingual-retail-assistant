import os, sys, time, wave, httpx
B = os.environ.get("MRA_URL", "https://localhost:8443")
CA = os.environ.get("MRA_CA", "secrets/server.pem")
H = {"Authorization": "Bearer " + os.environ.get("MRA_DEVICE_TOKEN", "test-device")}
w = wave.open(sys.argv[1]); pcm = w.readframes(w.getnframes())
ERR = (httpx.TransportError,)
def attempt():
    c = httpx.Client(verify=CA, timeout=4)
    sid = c.post(B + "/voice-query/start", headers=H).json()["session_id"]
    for i in range(0, len(pcm), 6400):
        r = c.post(f"{B}/voice-query/{sid}/chunk", headers=H, content=pcm[i:i+6400])
        if r.status_code != 204: raise RuntimeError(f"chunk {r.status_code}")
        time.sleep(0.2)  # real-time pace
    r = c.post(f"{B}/voice-query/{sid}/end", headers=H, json={"transcript": "where is parle-g biscuits"})
    if r.status_code != 200: raise RuntimeError(f"end {r.status_code}")
    return r.json()
t0 = time.time(); fail = None; delay = 0.5; n = 0
while True:
    n += 1
    try:
        d = attempt()
        rec = round(time.time() - fail, 2) if fail else 0
        print(f"RESULT {d['status']} {d['product_id']} attempts={n} recovered {rec} s after first failure, total {round(time.time()-t0,1)} s")
        sys.exit(0 if d["status"] == "OK" else 1)
    except (ERR + (RuntimeError,)) as e:
        if fail is None: fail = time.time(); print(f"[{round(time.time()-t0,1)}s] failure detected: {type(e).__name__}")
        print(f"[{round(time.time()-t0,1)}s] retry {n} in {delay} s"); time.sleep(delay); delay = min(delay * 2, 4)
    if time.time() - t0 > 60: print("RESULT FAIL gave up"); sys.exit(1)
