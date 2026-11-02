"""25 soniyalik sotuv Reels/Shorts: real kadrlar + tez kesishlar + karaoke subtitr."""
import os, sys, math, random, subprocess, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import render as R
from render import W, H, FPS, SR, eo, eio, eback, clamp, put, pill, text_img, font, disp
from footage import CLIP, phone_mask, PHONE_W, PHONE_H

VOICE = "/home/user/ovozlar_yt/ad1.mp3"
OUT = os.environ.get("AD_OUT", "/home/user/airpods_videos/sotuv_video/ad1_pods_pro3.mp4")
YEL = (255, 214, 0); WH = (255, 255, 255); BLK = (0, 0, 0); PUR = (112, 0, 255)

PARTS = [
    "Yuz ellik to'qqiz ming so'mga shovqinni bostiradigan quloqchin? Ha, bu haqiqat!",
    "Qutini ochamiz. Pods Pro 3 ANC.",
    "Telefonga bir soniyada ulanadi.",
    "Shovqinni bostirishni yoqing, metroda ham shovqin deyarli eshitilmaydi.",
    "Quti bilan o'ttiz soatgacha ishlaydi, ustiga bir yil kafolat.",
    "Do'konimizdan allaqachon ikki mingdan ortiq buyurtma berilgan.",
    "Uzum Marketda Airpods market deb qidiring. Havola profilda!",
]
# har sahna: kadrlar ro'yxati (klip, boshlanish, tezlik) — sahna ichida teng bo'linib tez kesiladi
SHOTS = [
    [("c1", 3.0, 1.0), ("c6", 27.5, 1.0)],
    [("c6", 1.0, 2.2), ("c6", 7.5, 2.0), ("c1", 4.8, 1.3)],
    [("c5", 0.3, 1.2), ("c4", 0.0, 0.8)],
    [("c6", 27.0, 1.0), ("c1", 9.5, 1.0)],
    [("c6", 15.5, 1.3), ("c5", 8.0, 1.0)],
    [("c7", 19.0, 0.6)],
    [("c2", 0.3, 1.0)],
]

class KReader:
    """Biroz kattaroq o'qiydi va Ken Burns (asta yaqinlashish) uchun kesadi."""
    def __init__(self, clip, start, speed, zoom_dir=1):
        self.z = 1.10; self.size = (int(W * self.z) // 2 * 2, int(H * self.z) // 2 * 2)
        self.r = R_reader(clip, start, speed, self.size); self.dir = zoom_dir
    def get(self, t, dur):
        fr = self.r.get(t); u = clamp(t / max(dur, .1))
        s = 1 + (self.z - 1) * (u if self.dir > 0 else 1 - u)
        cw, ch = int(self.size[0] / s * (1 / 1)), int(self.size[1] / s)
        cw = min(self.size[0], int(W * self.z / s)); ch = min(self.size[1], int(H * self.z / s))
        x0 = (self.size[0] - cw) // 2; y0 = (self.size[1] - ch) // 2
        return fr.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR)

def R_reader(clip, start, speed, size):
    import footage
    return footage.Reader(clip, start, speed, size)

# ---------- matn ----------
@functools.lru_cache(maxsize=None)
def word_img(w, col, size=84):
    f = font("black", size)
    bb = f.getbbox(w, stroke_width=8)
    im = Image.new("RGBA", (bb[2] - bb[0] + 24, bb[3] - bb[1] + 24), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((12 - bb[0], 12 - bb[1]), w, font=f, fill=col + (255,), stroke_width=8, stroke_fill=(0, 0, 0, 255))
    return im

def draw_karaoke(layer, words, T):
    """words: [(t0,t1,word)]. 3 so'zlik guruhlar, joriy so'z sariq va kattaroq."""
    groups = [words[i:i + 3] for i in range(0, len(words), 3)]
    for g in groups:
        if g[0][0] - .05 <= T < (g[-1][1] + .05):
            imgs = []
            for (t0, t1, w) in g:
                cur = t0 <= T < t1 + .02
                imgs.append(word_img(w.upper(), YEL if cur else WH, 84))
            gap = 10; total = sum(i.width for i in imgs) + gap * (len(imgs) - 1)
            sc = min(1.0, 1000 / total); x = W / 2 - total * sc / 2
            q = eback((T - g[0][0]) / .18)
            for (t0, t1, w), im in zip(g, imgs):
                cur = t0 <= T < t1 + .02
                s = sc * (1.08 if cur else 1.0) * (.85 + .15 * clamp(q))
                put(layer, im, x + im.width * sc / 2, 1330, clamp(q * 2), s)
                x += (im.width + gap) * sc
            break

def shade(im, top=.35, bot=.55):
    a = np.zeros((H, W), np.float32); y = np.linspace(0, 1, H)[:, None]
    a[:] = np.clip(top * np.clip((0.3 - y) / 0.3, 0, 1) + bot * np.clip((y - 0.55) / 0.35, 0, 1), 0, .85)
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0)); o.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    im.alpha_composite(o); return im

SHADE = None

# ---------- sahna ustidagi grafikalar ----------
def ov_hook(layer, t):
    q = eback((t - .15) / .35)
    shake = math.sin(t * 60) * 10 * clamp(1 - (t - .15) / .4) if t > .15 else 0
    put(layer, word_img("999 000", (220, 220, 225), 70), W / 2, 420, clamp(eo(t / .3)))
    if t > .35:
        p = clamp((t - .35) / .25); d = ImageDraw.Draw(layer)
        d.line((W / 2 - 170, 425, W / 2 - 170 + 340 * p, 405), fill=(255, 59, 48, 255), width=12)
    big = word_img("159 000 SO'M", YEL, 130)
    put(layer, big, W / 2 + shake, 560, clamp(q * 2), 1.6 - .6 * clamp(q))
    if t > .6:
        q2 = eback((t - .6) / .35)
        put(layer, pill("−84%", "black", 64, WH, (255, 59, 48, 255), padx=36, pady=16), W / 2 + 330, 450, clamp(q2), .5 + .5 * clamp(q2))
    if t > 1.0:
        q3 = eo((t - 1.0) / .3)
        put(layer, word_img("ANC'LI QULOQCHIN", WH, 70), W / 2, 690 + (1 - q3) * 30, q3)

def ov_title(layer, t):
    q = eback((t - .1) / .4)
    put(layer, word_img("POD'S PRO 3 ANC".replace("'", ""), WH, 100), W / 2, 420, clamp(q), .7 + .3 * clamp(q))
    q = eo((t - .4) / .3)
    put(layer, pill("1 YIL KAFOLAT", "xbold", 40, BLK, YEL + (255,), track=3), W / 2, 530, q)

def ov_pair(layer, t):
    q = eback((t - .1) / .4)
    put(layer, pill("1 soniyada ulanadi", "black", 60, WH, PUR + (255,), padx=44, pady=22), W / 2, 420, clamp(q), .6 + .4 * clamp(q))

def ov_anc(layer, t):
    cv = Image.new("RGBA", (1000, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(cv)
    p = clamp((t - .3) / 1.4); rnd = random.Random(5)
    comps = [(rnd.uniform(3, 12), rnd.uniform(0, 6), rnd.uniform(.4, 1)) for _ in range(6)]
    pts = []
    for i in range(201):
        u = i / 200; y = sum(a * math.sin(u * f * 6.28 + ph + t * 4) for f, ph, a in comps) / 3 * 110 * (1 - eio(p))
        pts.append((20 + u * 960, 150 + y * math.sin(u * math.pi)))
    col = tuple(int(255 * (1 - p) + c * p) for c in YEL)
    d.line(pts, fill=col + (255,), width=10, joint="curve")
    put(layer, cv, W / 2, 470)
    lab = "ANC ON" if p > .6 else "SHOVQIN"
    put(layer, word_img(lab, YEL if p > .6 else (255, 90, 80), 80), W / 2, 330, clamp(eo(t / .3)))

def ov_specs(layer, t):
    for j, (txt, dt) in enumerate((("30 SOAT", .1), ("1 YIL KAFOLAT", .9))):
        q = eback((t - dt) / .35)
        if q > 0: put(layer, pill(txt, "black", 70, BLK, YEL + (255,), padx=48, pady=22), W / 2, 380 + j * 150, clamp(q), .5 + .5 * clamp(q))

def ov_proof(layer, t):
    q = eo(t / .3)
    card = Image.new("RGBA", (900, 330), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, 899, 329), radius=48, fill=(255, 255, 255, 240))
    n = int(2178 * eio(t / 1.6))
    f = font("black", 120); s = f"{n:,}".replace(",", " ")
    d.text((450 - f.getlength(s) / 2, 20), s, font=f, fill=BLK)
    f2 = font("bold", 50); s2 = "ta buyurtma"
    d.text((450 - f2.getlength(s2) / 2, 165), s2, font=f2, fill=(90, 90, 96))
    f3 = font("bold", 46); s3 = "4.5  (428 ta sharh)"
    for k in range(5):
        cx = 250 + k * 46; cy = 268
        fill = (255, 184, 0) if k < 4 or eio(t / 1.6) > .5 else (220, 220, 225)
        d.polygon(R.star_poly(cx, cy, 22, 9), fill=fill)
    d.text((490, 242), s3, font=f3, fill=BLK)
    put(layer, card, W / 2, 470 + (1 - q) * 40, q)

def ov_cta(layer, t, ctx):
    if t < 1.2:
        q = eback((t - .05) / .35)
        put(layer, word_img("UZUM MARKET", WH, 110), W / 2, 520, clamp(q), .7 + .3 * clamp(q))
        return
    tt = t - 1.2
    q = eo(tt / .3)
    put(layer, word_img("QIDIRUVGA YOZING:", WH, 62), W / 2, 170, q)
    put(layer, pill("Airpods market", "black", 62, WH, PUR + (255,), padx=44, pady=20), W / 2, 270, q)
    qp = eback((tt - .1) / .5)
    if tt < 2.4: scr = ctx.setdefault("s1", R_reader("c7", 13.5, 2.4, (PHONE_W, PHONE_H))).get(tt)
    else: scr = ctx.setdefault("s2", R_reader("c7", 32.6, .5, (PHONE_W, PHONE_H))).get(tt - 2.4)
    scr.putalpha(phone_mask())
    ph = Image.new("RGBA", (PHONE_W + 28, PHONE_H + 28), (0, 0, 0, 0))
    ImageDraw.Draw(ph).rounded_rectangle((0, 0, PHONE_W + 27, PHONE_H + 27), radius=124, fill=(14, 14, 16, 255))
    ph.alpha_composite(scr, (14, 14))
    put(layer, ph, W / 2, 880 + (1 - clamp(qp)) * 300, clamp(qp), .72)
    q = eback((tt - .5) / .4)
    put(layer, pill("i2u.uz/airpodsmarket", "black", 58, BLK, YEL + (255,), padx=44, pady=22), W / 2, 1490 - abs(math.sin(t * 3.5)) * 10, clamp(q), .7 + .3 * clamp(q))

OVERLAYS = [ov_hook, ov_title, ov_pair, ov_anc, ov_specs, ov_proof, None]

# ---------- audio ----------
def get_voice():
    if os.path.exists(VOICE):
        segs = R.split_user_voice(VOICE, PARTS, "/tmp/asr")
        return segs, "eleven"
    segs = [R.tts(p, f"/tmp/build/tmp/ad_{i}") for i, p in enumerate(PARTS)]
    return segs, "espeak"

def music_punchy(total, seed=31):
    m = R.music(total, seed)
    return m

def build():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    segs, src = get_voice()
    t = 0.0; scenes = []
    for k, a in enumerate(segs):
        lead = .05 if k == 0 else .12
        dur = lead + len(a) / SR + (.12 if k < len(segs) - 1 else .9)
        if k == len(segs) - 1: dur = max(dur, 5.2)
        scenes.append(dict(k=k, start=t, dur=dur, vstart=t + lead, a=a)); t += dur
    total = t
    # karaoke so'z vaqtlari: har bo'lak ichida harf uzunligi bo'yicha
    words = []
    for sc in scenes:
        ws = disp(PARTS[sc["k"]]).replace("Pods Pro 3 ANC", "Pods·Pro·3·ANC").split()
        L = sum(len(w) + 1 for w in ws); acc = 0; vd = len(sc["a"]) / SR
        for w in ws:
            t0 = sc["vstart"] + vd * acc / L; acc += len(w) + 1; t1 = sc["vstart"] + vd * acc / L
            words.append((t0, t1, w.replace("·", " ").strip(",.!?")))
    # audio
    n = int(total * SR) + 1; vo = np.zeros(n)
    for sc in scenes:
        s0 = int(sc["vstart"] * SR); e = min(n, s0 + len(sc["a"])); vo[s0:e] += sc["a"][:e - s0]
    mu = music_punchy(total); mu = np.pad(mu, (0, max(0, n - len(mu))))[:n]
    env = np.convolve(np.abs(vo), np.ones(4410) / 4410, "same"); env = np.clip(env / (env.max() + 1e-9) * 3, 0, 1)
    if os.environ.get('NOVOICE'): vo = vo * 0; env = env * 0
    mix = vo + mu * (0.7 - 0.45 * env)
    def add(sig, at, g):
        s0 = int(at * SR)
        if 0 <= s0 < n: e = min(n, s0 + len(sig)); mix[s0:e] += sig[:e - s0] * g
    add(R.sfx_impact(), 0.12, .8); add(R.sfx_ding(), 0.2, .45); add(R.sfx_pop(500, 1100), .62, .5)
    for sc in scenes[1:]: add(R.sfx_whoosh(.35), sc["start"] - .1, .5)
    for sc in scenes:
        nsh = len(SHOTS[sc["k"]])
        for j in range(1, nsh): add(R.sfx_whoosh(.25), sc["start"] + sc["dur"] * j / nsh - .08, .3)
    add(R.sfx_pop(), scenes[4]["start"] + .1, .5); add(R.sfx_pop(), scenes[4]["start"] + .9, .5)
    add(R.sfx_ding(), scenes[5]["start"] + 1.6, .35)
    add(R.sfx_riser(.8), scenes[6]["start"] - .8, .35)
    mix = np.tanh(mix * 1.1) * .95; fo = int(.4 * SR); mix[-fo:] *= np.linspace(1, 0, fo)
    wav = "/tmp/build/tmp/ad_mix.f32"; mix.astype(np.float32).tofile(wav)
    # video
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", "-shortest", OUT]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    readers = {}; ctx = {}
    brand = text_img("AIRPODS MARKET", "semi", 28, (235, 235, 240), maxw=2000, track=6)
    for fi in range(int(total * FPS)):
        T = fi / FPS
        sc = next(s for s in reversed(scenes) if s["start"] <= T + 1e-6); t = T - sc["start"]; k = sc["k"]
        shots = SHOTS[k]; nsh = len(shots); j = min(nsh - 1, int(t / (sc["dur"] / nsh))); sd = sc["dur"] / nsh; tj = t - j * sd
        key = (k, j)
        if key not in readers: readers[key] = KReader(*shots[j], zoom_dir=1 if (k + j) % 2 == 0 else -1)
        if k == 6 and t >= 1.2:
            frame = Image.new("RGBA", (W, H), PUR + (255,))
            r = eio((t - 1.2) / .35) * 2300
            base = readers[key].get(tj, sd); m = Image.new("L", (W, H), 255)
            ImageDraw.Draw(m).ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), fill=0)
            frame.paste(base, (0, 0), m)
        else:
            frame = readers[key].get(tj, sd)
            if k == 5:  # do'kon sahifasi: yumshoq qorong'ilashtirish
                frame.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 110)))
            frame = shade(frame)
        # kesishda oq chaqnash
        if t < .08 and k > 0 or (j > 0 and tj < .06):
            fl = Image.new("RGBA", (W, H), (255, 255, 255, int(110 * (1 - max(t, tj) / .08))))
            frame.alpha_composite(fl)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if k == 6: ov_cta(layer, t, ctx)
        elif OVERLAYS[k]: OVERLAYS[k](layer, t)
        if not (k == 6 and t >= 1.2): draw_karaoke(layer, words, T)
        frame.alpha_composite(layer); frame.alpha_composite(brand, (60, 110))
        pr.stdin.write(frame.convert("RGB").tobytes())
    pr.stdin.close(); pr.wait()
    print("OK", OUT, round(total, 1), "s", src, flush=True)

if __name__ == "__main__":
    build()
