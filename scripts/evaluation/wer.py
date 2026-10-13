import sys,glob,os,re,wave,collections,csv,httpx,jiwer
H={"Authorization":"Bearer dev-device"};B="http://127.0.0.1:8000"
sheet,folder=sys.argv[1],sys.argv[2]
ref={}
for l in open(sheet,encoding="utf8"):
    m=re.match(r"\s*\d+\.\s+(\S+\.wav)\s+(.+)",l)
    if m: ref[m.group(1)]=m.group(2).strip()
P=str.maketrans({c:" " for c in "?.,!।-'\"’:;"})
norm=lambda t:" ".join(t.lower().translate(P).split())
c=httpx.Client(timeout=60);R=collections.defaultdict(list);Hy=collections.defaultdict(list);rows=[]
for f in sorted(glob.glob(folder+"/*.wav")):
    n=os.path.basename(f)
    if n not in ref: continue
    w=wave.open(f);pcm=w.readframes(w.getnframes())
    sid=c.post(B+"/voice-query/start",headers=H).json()["session_id"]
    for i in range(0,len(pcm),6400): c.post(f"{B}/voice-query/{sid}/chunk",headers=H,content=pcm[i:i+6400])
    d=c.post(f"{B}/voice-query/{sid}/end",headers=H).json()
    st="_".join(n[:-4].split("_")[1:-1]);r,h=norm(ref[n]),norm(d.get("transcript") or "")
    R[st].append(r);Hy[st].append(h);rows.append((n,r,h))
out="results/wer/wer_"+os.path.basename(folder.rstrip("/"))+".csv"
csv.writer(open(out,"w",encoding="utf8",newline="")).writerows([("file","ref","hyp")]+rows)
for s in R: print(s,f"WER {100*jiwer.wer(R[s],Hy[s]):.0f}%",len(R[s]),"clips")
