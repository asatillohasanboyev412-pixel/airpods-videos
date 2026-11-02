# Montaj dasturi (Airpods market videolari)

- `render.py` — asosiy motion-grafika dvigateli (ikonkalar, matn, musiqa, effektlar)
- `render_yt.py` + `content_yt.py` — 5 xil dizayndagi YouTube Shorts
- `footage.py` — real kadrlarni (kliplarni) videoga qo'shish
- `render_ad.py` — 25–30 soniyalik sotuv videosi (karaoke subtitr, tez kesishlar)
- `asr_one.py` — ovozni so'zlar bo'yicha tanish (faster-whisper)
- `content.py` — Instagram uchun 10 ta video ssenariysi

Kerakli: python3, ffmpeg, numpy, pillow, scipy, faster-whisper, Inter shrifti.
Kliplar (`/tmp/clips_in/c1..c7`) bu ochiq repozitoriyga yuklanmagan — yangi sessiyada qayta biriktiring.
