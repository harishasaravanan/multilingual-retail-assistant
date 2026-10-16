import os, sys, ssl, httpx
B = os.environ.get("MRA_URL", "https://localhost:8443")
CA = os.environ.get("MRA_CA", "secrets/server.pem")
TOK = os.environ.get("MRA_DEVICE_TOKEN", "test-device")
H = {"Authorization": "Bearer " + TOK}
c = httpx.Client(verify=CA, timeout=30)
res = []
def chk(name, ok, info=""):
    res.append(bool(ok)); print(("PASS " if ok else "FAIL ") + name, info)
r = c.get(B + "/health"); chk("health over TLS", r.status_code == 200, r.status_code)
r = c.post(B + "/voice-query/start"); chk("start, no token -> 401", r.status_code == 401, r.status_code)
r = c.post(B + "/voice-query/start", headers={"Authorization": "Bearer wrong"}); chk("start, bad token -> 401", r.status_code == 401, r.status_code)
r = c.post(B + "/voice-query/start", headers={"Authorization": "Basic " + TOK}); chk("start, wrong scheme -> 401", r.status_code == 401, r.status_code)
r = c.post(B + "/voice-query/start", headers=H); sid = r.json().get("session_id"); chk("start, good token -> session", r.status_code == 200 and sid, sid)
r = c.post(f"{B}/voice-query/{sid}/chunk", content=b"\0" * 6400); chk("chunk, no token -> 401", r.status_code == 401, r.status_code)
r = c.post(f"{B}/voice-query/s_nope/chunk", headers=H, content=b"\0" * 6400); chk("chunk, unknown session -> 404", r.status_code == 404, r.status_code)
r = c.post(f"{B}/voice-query/{sid}/chunk", headers=H, content=b"\0" * 6400); chk("chunk, good -> 204", r.status_code == 204, r.status_code)
r = c.post(f"{B}/voice-query/{sid}/end", content=b""); chk("end, no token -> 401", r.status_code == 401, r.status_code)
r = c.post(f"{B}/voice-query/{sid}/end", headers=H, json={"transcript": "where is parle-g biscuits"}); chk("end, good -> OK P003", r.status_code == 200 and r.json().get("status") == "OK", (r.status_code, r.json().get("product_id")))
r = c.post(f"{B}/voice-query/{sid}/end", headers=H, json={"transcript": "x"}); chk("end again (closed session) -> 404/410", r.status_code in (404, 410), r.status_code)
try:
    httpx.Client(timeout=10).get(B + "/health"); chk("no CA pinned -> rejected", False)
except Exception as e: chk("self-signed cert rejected without CA", True, type(e).__name__)
try:
    httpx.Client(timeout=10).get(B.replace("https", "http") + "/health"); chk("plain HTTP to TLS port refused", False)
except Exception as e: chk("plain HTTP to TLS port refused", True, type(e).__name__)
print("TLS version:", c.get(B + "/health").extensions.get("network_stream").get_extra_info("ssl_object").version())
print("RESULT", sum(res), "/", len(res)); sys.exit(0 if all(res) else 1)
