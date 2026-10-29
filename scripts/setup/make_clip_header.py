import sys, wave
w = wave.open(sys.argv[1]); d = w.readframes(min(w.getnframes(), 64000))
open(sys.argv[2], 'w').write("const unsigned char clip_pcm[]={%s};\nconst unsigned clip_pcm_len=%d;\n" % (",".join(map(str, d)), len(d)))
