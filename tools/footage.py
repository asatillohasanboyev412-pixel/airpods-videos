import subprocess, math, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import render as R
from render import W, H, FPS, eo, eio, eback, clamp, put, pill, text_img, disp, font, wrap

CLIP = {k: f"/tmp/clips_in/{k}.{'mp4' if k == 'c3' else 'mov'}" for k in ("c1", "c2", "c4", "c5", "c6", "c7")}

class Reader:
    """Klipdan ketma-ket kadr o'qiydi (start, tezlik, o'lcham)."""
    def __init__(self, clip, start, speed=1.0, size=(W, H)):
        self.clip, self.start, self.speed, self.size = clip, start, speed, size
        self.p = None; self.idx = -1; self.last = None
    def _open(self):
        w, h = self.size
        vf = f"setpts=PTS/{self.speed},fps={FPS},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{self.start:.3f}", "-i", CLIP[self.clip], "-an", "-vf", vf,
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    def get(self, t):
        if self.p is None: self._open()
        want = int(t * FPS); n = self.size[0] * self.size[1] * 3
        while self.idx < want:
            buf = self.p.stdout.read(n)
            if len(buf) < n: break
            self.last = buf; self.idx += 1
        if self.last is None: return Image.new("RGBA", self.size, (0, 0, 0, 255))
        return Image.frombuffer("RGB", self.size, self.last, "raw", "RGB", 0, 1).convert("RGBA")

@functools.lru_cache(maxsize=None)
def shade(kind):
    a = np.zeros((H, W), np.float32); y = np.linspace(0, 1, H)[:, None]
    if kind == "hook": a[:] = 0.42 + 0.25 * np.exp(-((y - 0.42) ** 2) / 0.05)
    elif kind == "product": a[:] = np.clip(0.55 * np.exp(-((y - 0.14) ** 2) / 0.012) + 0.75 * np.clip((y - 0.52) / 0.3, 0, 1), 0, 0.82)
    elif kind == "cta1": a[:] = 0.25 + 0.45 * np.exp(-((y - 0.4) ** 2) / 0.03)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); im.putalpha(Image.fromarray((a * 255).astype(np.uint8))); return im

PHONE_W, PHONE_H = 560, 1214
@functools.lru_cache(maxsize=None)
def phone_mask():
    m = Image.new("L", (PHONE_W * 2, PHONE_H * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, PHONE_W * 2 - 1, PHONE_H * 2 - 1), radius=110, fill=255)
    return m.resize((PHONE_W, PHONE_H), Image.LANCZOS)

class Footage:
    def __init__(self, plan):
        self.plan = plan; self.readers = {}
    def reader(self, key, *a, **k):
        if key not in self.readers: self.readers[key] = Reader(*a, **k)
        return self.readers[key]

    def base(self, sc, t, bg):
        typ = sc["type"]; key = id(sc)
        if typ == "hook" and "hook" in self.plan:
            c, s0, sp = self.plan["hook"]
            fr = self.reader((key, "h"), c, s0, sp).get(t); fr.alpha_composite(shade("hook")); return fr
        if typ == "product" and "product" in self.plan:
            c, s0, sp = self.plan["product"]
            fr = self.reader((key, "p"), c, s0, sp).get(t); fr.alpha_composite(shade("product")); return fr
        if typ == "cta":
            if t < 1.8:
                fr = self.reader((key, "c2"), "c2", 0.3, 1.0).get(t); fr.alpha_composite(shade("cta1")); return fr
            tt = t - 1.8
            fr = self.reader((key, "c2"), "c2", 0.3, 1.0).get(t)
            r = eio(tt / .45) * 2300; d = ImageDraw.Draw(fr)
            d.ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), fill=R.CTA_BG)
            return fr
        return None

    def scene(self, sc, t, layer, v):
        typ = sc["type"]; WH = (245, 245, 247)
        if typ == "hook" and "hook" in self.plan:
            q = eback((t - .05) / .4)
            put(layer, pill(disp(v["tag"]), "xbold", 38, R.ACC_FG, R.ACC + (255,), track=4), W / 2, 560, clamp(q), .6 + .4 * q)
            words = sc["title"].split(); fs = 112
            while max(font("black", fs).getlength(w_) for w_ in words) > 960: fs -= 4
            f = font("black", fs); lines = wrap(sc["title"], f, 960); y = 650; wi = 0
            for line in lines:
                ws = line.split(); widths = [f.getlength(w_) for w_ in ws]; sp = f.getlength(" ")
                x = W / 2 - (sum(widths) + sp * (len(ws) - 1)) / 2
                for w_, ww in zip(ws, widths):
                    qq = eback((t - .12 - wi * .12) / .35)
                    col = R.ACC if (wi == len(words) - 1 and len(words) > 1) else WH
                    put(layer, text_img(w_, "black", fs, col, maxw=2000), x + ww / 2, y + 60 + (1 - clamp(qq)) * 40, clamp(qq * 1.5), .7 + .3 * qq)
                    x += ww + sp; wi += 1
                y += int(fs * 1.12)
            qq = eo((t - .35 - wi * .12) / .5)
            put(layer, text_img(sc["sub"], "med", 52, (225, 225, 230)), W / 2, y + 70 + (1 - qq) * 30, qq)
            return True
        if typ == "product" and "product" in self.plan:
            q = eo((t - .05) / .5)
            put(layer, text_img("Pods Pro 3 ANC", "black", 104, WH), W / 2, 300 + (1 - q) * 30, q)
            q = eo((t - .2) / .5)
            put(layer, text_img("1 yil kafolat · Uzum Market", "med", 44, (220, 220, 226)), W / 2, 395, q)
            for j, ft in enumerate(sc["features"]):
                qf = eback((t - .8 - j * .3) / .4)
                if qf <= 0: continue
                cx = W / 2 + (-238 if j % 2 == 0 else 238); cy = 1240 + (j // 2) * 130
                put(layer, R.feature_chip(ft, R.THEME.get("name")), cx, cy, clamp(qf), .7 + .3 * qf)
            return True
        if typ == "cta":
            if t < 1.8:
                q = eback((t - .1) / .45)
                put(layer, text_img("Uzum Market'da", "black", 108, WH, maxw=2000), W / 2, 690, clamp(q), .7 + .3 * q)
                q = eo((t - .4) / .4)
                put(layer, text_img(disp("“Airpods market” do'koni"), "bold", 64, R.ACC), W / 2, 820, q)
                return True
            tt = t - 1.8
            q = eo((tt - .25) / .4)
            put(layer, text_img("Qidiruvga yozing:", "bold", 54, R.CTA_FG), W / 2, 200 + (1 - q) * 20, q)
            put(layer, pill("Airpods market", "black", 60, R.CTA_BG, R.CTA_FG + (255,), padx=44, pady=20), W / 2, 300, q, .8 + .2 * q)
            qp = eback((tt - .2) / .55)
            if qp > 0:
                if tt < 3.0: scr = self.reader((id(sc), "s1"), "c7", 13.5, 2.3, (PHONE_W, PHONE_H)).get(tt)
                else: scr = self.reader((id(sc), "s2"), "c7", 25.0, 1.2, (PHONE_W, PHONE_H)).get(tt - 3.0)
                scr.putalpha(phone_mask())
                ph = Image.new("RGBA", (PHONE_W + 28, PHONE_H + 28), (0, 0, 0, 0))
                ImageDraw.Draw(ph).rounded_rectangle((0, 0, PHONE_W + 27, PHONE_H + 27), radius=124, fill=(14, 14, 16, 255))
                ph.alpha_composite(scr, (14, 14))
                put(layer, ph, W / 2, 905 + (1 - clamp(qp)) * 300, clamp(qp), .74 + .1 * qp)
            q = eback((tt - .7) / .45)
            hp = pill("i2u.uz/airpodsmarket", "black", 54, R.CTA_BG, R.CTA_FG + (255,), padx=44, pady=22)
            put(layer, hp, W / 2, 1490 - abs(math.sin(t * 3.5)) * 12, clamp(q), .7 + .3 * q)
            q2 = eo((tt - 1.0) / .4)
            put(layer, text_img("Havola profilda va tavsifda", "semi", 40, R.CTA_FG), W / 2, 1590, q2)
            return True
        return False
