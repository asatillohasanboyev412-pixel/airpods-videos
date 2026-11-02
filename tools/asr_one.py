import json, sys, subprocess, numpy as np
from faster_whisper import WhisperModel
m = WhisperModel("/tmp/whisper_small", device="cpu", compute_type="int8", cpu_threads=4)
for p in sys.argv[1:]:
    au = np.frombuffer(subprocess.run(["ffmpeg","-v","error","-i",p,"-ac","1","-ar","16000","-f","f32le","-"],capture_output=True,check=True).stdout, np.float32)
    segs, _ = m.transcribe(au, language="uz", word_timestamps=True, beam_size=5)
    words = [(round(w.start,2), round(w.end,2), w.word.strip()) for s in segs for w in s.words]
    name = p.split("/")[-1].split(".")[0]
    json.dump(words, open(f"/tmp/asr/{name}.json","w"), ensure_ascii=False)
    print(name, " ".join(w[2] for w in words))
