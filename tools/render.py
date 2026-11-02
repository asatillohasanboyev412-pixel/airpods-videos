import math, os, re, subprocess, sys, random, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from scipy.signal import butter, sosfilt
from content import VIDEOS, CTA_VOICE, TTS_SUBS

W, H, FPS, SR = 1080, 1920, 30, 44100
OUT = "/home/user/airpods_videos"
TMP = "/tmp/build/tmp"
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)

BG = (244, 244, 246); INK = (17, 17, 20); GRAY = (110, 110, 118); LIGHT = (226, 226, 232)
ACC = (112, 0, 255); WHITE = (255, 255, 255); RED = (255, 59, 48); GREEN = (52, 199, 89)
ORANGE = (255, 159, 10); BLUE = (10, 132, 255); GOLD = (255, 196, 0)
CARD = WHITE; CARD_FG = INK; ACC_FG = WHITE; CTA_BG = ACC; CTA_FG = WHITE; CTA_SUB = (225, 210, 255)
THEME = {}
FD = "/usr/share/fonts/opentype/inter/"

def disp(s):
    s = re.sub(r"([oOgG])'", lambda m: m.group(1) + "ʻ", s)
    return s.replace("'", "’")

def up(s):
    return s.upper() if THEME.get("upper") else s

def tts_text(s):
    for a, b in TTS_SUBS:
        s = s.replace(a, b)
    return s

# ---------------- easing ----------------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eio(x): x = clamp(x); return 4*x*x*x if x < .5 else 1 - (-2*x + 2) ** 3 / 2
def eback(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

# ---------------- text ----------------
@functools.lru_cache(maxsize=None)
def font(weight, size):
    name = {"black": "InterDisplay-Black.otf", "xbold": "InterDisplay-ExtraBold.otf",
            "bold": "InterDisplay-Bold.otf", "semi": "Inter-SemiBold.otf",
            "med": "Inter-Medium.otf", "reg": "Inter-Regular.otf"}[weight]
    return ImageFont.truetype(FD + name, size)

def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if f.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

@functools.lru_cache(maxsize=None)
def text_img(text, weight, size, color, maxw=920, lh=1.12, track=0):
    f = font(weight, size)
    lines = wrap(text, f, maxw)
    asc, desc = f.getmetrics()
    lhpx = int(size * lh)
    widths = [f.getlength(l) + track * len(l) for l in lines]
    w = int(max(widths)) + 8; h = lhpx * (len(lines) - 1) + asc + desc + 8
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        x = (w - widths[i]) / 2
        if track:
            for ch in l:
                d.text((x, i * lhpx), ch, font=f, fill=color + (255,)); x += f.getlength(ch) + track
        else:
            d.text((x, i * lhpx), l, font=f, fill=color + (255,))
    return im

def with_op(im, op):
    if op >= 0.999: return im
    im = im.copy(); a = im.getchannel("A").point(lambda v: int(v * op)); im.putalpha(a); return im

def put(layer, im, cx, cy, op=1.0, scale=1.0):
    if op <= 0.003: return
    if abs(scale - 1) > 0.003:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    im = with_op(im, op)
    layer.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def pill(text, weight, size, fg, bg, padx=34, pady=16, track=0):
    t = text_img(text, weight, size, fg, maxw=2000, track=track)
    w, h = t.width + padx * 2, size + pady * 2 + 6
    im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), radius=h, fill=bg)
    im = im.resize((w, h), Image.LANCZOS)
    im.alpha_composite(t, (padx - 4, (h - t.height) // 2 + 2))
    return im

# ---------------- product sprites ----------------
def grad_fill(mask, top, bot):
    w, h = mask.size
    g = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(top)[None, None] * (1 - g) + np.array(bot)[None, None] * g).astype(np.uint8)
    arr = np.repeat(arr, w, axis=1)
    im = Image.fromarray(arr, "RGB").convert("RGBA"); im.putalpha(mask); return im

def outline(mask, px, color):
    big = mask.filter(ImageFilter.MaxFilter(px * 2 + 1))
    o = Image.new("RGBA", mask.size, color + (255,)); o.putalpha(big); return o

def make_earbud(height, flip=False):
    k = 4; s = height * k / 520
    W_, H_ = int(300 * s), int(520 * s)
    def R(*b): return tuple(int(v * s) for v in b)
    body = Image.new("L", (W_, H_), 0); d = ImageDraw.Draw(body)
    d.ellipse(R(60, 55, 280, 250), fill=255)
    d.rounded_rectangle(R(188, 175, 262, 505), radius=int(37 * s), fill=255)
    tipm = Image.new("L", (W_, H_), 0); ImageDraw.Draw(tipm).ellipse(R(8, 95, 120, 215), fill=255)
    im = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    im.alpha_composite(outline(tipm, int(3 * s), (200, 200, 206)))
    im.alpha_composite(grad_fill(tipm, (236, 236, 240), (206, 206, 212)))
    im.alpha_composite(outline(body, int(3 * s), (214, 214, 220)))
    im.alpha_composite(grad_fill(body, (255, 255, 255), (232, 232, 238)))
    d = ImageDraw.Draw(im)
    d.ellipse(R(150, 92, 218, 140), fill=(40, 40, 44))
    d.rounded_rectangle(R(205, 320, 245, 390), radius=int(20 * s), fill=(236, 236, 241))
    d.ellipse(R(214, 470, 236, 490), fill=(60, 60, 66))
    d.ellipse(R(232, 130, 250, 148), fill=(60, 60, 66))
    im = im.resize((W_ // k, H_ // k), Image.LANCZOS)
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im

def make_case(width):
    k = 4; s = width * k / 560
    W_, H_ = int(560 * s), int(460 * s)
    def R(*b): return tuple(int(v * s) for v in b)
    m = Image.new("L", (W_, H_), 0)
    ImageDraw.Draw(m).rounded_rectangle(R(6, 6, 554, 454), radius=int(150 * s), fill=255)
    im = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    im.alpha_composite(outline(m, int(3 * s), (212, 212, 218)))
    im.alpha_composite(grad_fill(m, (255, 255, 255), (228, 228, 234)))
    d = ImageDraw.Draw(im)
    d.line(R(14, 150, 546, 150), fill=(206, 206, 212), width=max(2, int(3 * s)))
    d.ellipse(R(272, 296, 290, 314), fill=GREEN)
    return im.resize((W_ // k, H_ // k), Image.LANCZOS)

def make_shadow(w, h, op=70):
    im = Image.new("RGBA", (w * 2, h * 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((w // 2, h * 3 // 2, w * 3 // 2, h * 5 // 2), fill=(0, 0, 0, op))
    return im.filter(ImageFilter.GaussianBlur(h * 0.45))

SPR = {}
def sprites():
    if not SPR:
        SPR["bud"] = make_earbud(520); SPR["budL"] = make_earbud(520, True)
        SPR["bud_s"] = make_earbud(300); SPR["budL_s"] = make_earbud(300, True)
        SPR["case"] = make_case(600); SPR["case_s"] = make_case(420)
        SPR["shadow"] = make_shadow(500, 60); SPR["shadow_s"] = make_shadow(300, 40)
    return SPR

# ---------------- icon drawing (on 2x canvas) ----------------
IS = 1280; IC = IS // 2   # canvas 1280 -> shown at 640
def F2(w, s): return font(w, s)

def sine_pts(x0, x1, yc, amp, freq, phase, n=160, noise=None):
    pts = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n; u = i / n
        y = math.sin(u * freq * 2 * math.pi + phase) * amp
        if noise is not None: y += noise(u)
        env = math.sin(u * math.pi) ** 0.6
        pts.append((x, yc + y * env))
    return pts

def jag(t, seed, amt):
    rnd = random.Random(seed)
    comps = [(rnd.uniform(3, 14), rnd.uniform(0, 6.28), rnd.uniform(.3, 1), rnd.uniform(1, 4)) for _ in range(7)]
    return lambda u: amt * sum(a * math.sin(u * f * 6.28 + ph + t * sp) for f, ph, a, sp in comps) / 3

def paste_c(cv, im, cx, cy, op=1, rot=0, scale=1):
    if scale != 1: im = im.resize((int(im.width * scale), int(im.height * scale)), Image.BILINEAR)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    put(cv, im, cx, cy, op)

def badge_circle(d, cx, cy, r, fill, op=1):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill + (int(255 * op),))

def star_poly(cx, cy, R_, r_):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5; rr = R_ if i % 2 == 0 else r_
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts

def sparkle(d, cx, cy, r, col):
    d.polygon([(cx, cy - r), (cx + r * .25, cy - r * .25), (cx + r, cy), (cx + r * .25, cy + r * .25),
               (cx, cy + r), (cx - r * .25, cy + r * .25), (cx - r, cy), (cx - r * .25, cy - r * .25)], fill=col)

def check(d, cx, cy, s, p, col, w):
    a = (cx - s * .5, cy); b = (cx - s * .12, cy + s * .38); c = (cx + s * .55, cy - s * .4)
    p1 = clamp(p / .4); p2 = clamp((p - .4) / .6)
    if p1 > 0: d.line([a, (a[0] + (b[0] - a[0]) * p1, a[1] + (b[1] - a[1]) * p1)], fill=col, width=w, joint="curve")
    if p2 > 0: d.line([b, (b[0] + (c[0] - b[0]) * p2, b[1] + (c[1] - b[1]) * p2)], fill=col, width=w, joint="curve")
    if p1 >= 1: d.ellipse((b[0] - w / 2, b[1] - w / 2, b[0] + w / 2, b[1] + w / 2), fill=col)

def bt_rune(d, cx, cy, s, col, w):
    pts = [(cx - s * .45, cy - s * .45), (cx + s * .45, cy + s * .4), (cx, cy + s * .85), (cx, cy - s * .85),
           (cx + s * .45, cy - s * .4), (cx - s * .45, cy + s * .45)]
    d.line(pts, fill=col, width=w, joint="curve")

def battery(d, cx, cy, level, col, label=None, t=0):
    w, h = 760, 360
    x0, y0 = cx - w / 2, cy - h / 2
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=70, outline=INK, width=26)
    d.rounded_rectangle((x0 + w + 18, cy - 70, x0 + w + 58, cy + 70), radius=20, fill=INK)
    fw = (w - 84) * clamp(level)
    if fw > 10:
        d.rounded_rectangle((x0 + 42, y0 + 42, x0 + 42 + fw, y0 + h - 42), radius=40, fill=col)
    if label:
        f = F2("black", 150); tw = f.getlength(label)
        d.text((cx - tw / 2, cy - 92), label, font=f, fill=WHITE if level > .55 else INK)

def draw_icon(kind, cv, t):
    """cv: 2x RGBA canvas. t: local time in scene (s)."""
    S = sprites(); d = ImageDraw.Draw(cv); c = IC
    p = eo(t / 0.9)
    bob = math.sin(t * 2.2) * 14
    if kind == "case":
        paste_c(cv, S["shadow"], c, c + 330, 1)
        paste_c(cv, S["case"], c, c + 120 + bob * .3, 1, scale=1.25)
        for i, (sp, x) in enumerate([("bud_s", c - 120), ("budL_s", c + 120)]):
            q = eio((t - .3 - i * .25) / 1.1)
            y = -150 + (c - 40 - -150) * q
            paste_c(cv, S[sp], x, y, 1 - clamp((q - .8) / .2), rot=(1 - q) * (20 if i else -20))
        if t > 1.6:
            r = 40 + ((t - 1.6) % 1.2) * 160
            d.ellipse((c - r, c + 240 - r, c + r, c + 240 + r), outline=GREEN + (int(255 * clamp(1 - (r - 40) / 190)),), width=10)
    elif kind == "heat":
        sx, sy, sr = c - 210, c - 230, 120
        for i in range(12):
            a = i * math.pi / 6 + t * .6
            d.line((sx + math.cos(a) * (sr + 30), sy + math.sin(a) * (sr + 30), sx + math.cos(a) * (sr + 80), sy + math.sin(a) * (sr + 80)), fill=ORANGE, width=18)
        d.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=ORANGE)
        paste_c(cv, S["bud"], c + 80, c + 110 + bob, 1, rot=-8, scale=1.2)
        for k in range(3):
            x = c - 110 + k * 120; ph = t * 4 + k
            pts = [(x + math.sin(ph + j * .5) * 18, c + 420 - j * 18) for j in range(14)]
            d.line(pts, fill=ORANGE + (180,), width=12, joint="curve")
        q = eback((t - 1.0) / .5)
        if q > 0:
            r = 470 * q
            d.ellipse((c - r, c + 60 - r, c + r, c + 60 + r), outline=RED, width=int(34 * q))
            a = math.radians(-45)
            d.line((c - math.cos(a) * r * .7, c + 60 - math.sin(a) * r * .7 * -1, c + math.cos(a) * r * .7, c + 60 + math.sin(a) * r * .7 * -1), fill=RED, width=int(34 * q))
    elif kind in ("battery", "hours"):
        if kind == "battery":
            lv = .2 + .6 * eio((t - .5) / 1.6)
            col = RED if lv < .3 else (GREEN if lv > .75 else ORANGE)
            battery(d, c, c - 40, lv, col, f"{int(round(lv * 100))}%")
            f = F2("bold", 64)
            for v, lab in ((.2, "20%"), (.8, "80%")):
                x = c - 380 + 42 + (760 - 84) * v
                d.line((x, c + 190, x, c + 250), fill=GRAY, width=8)
                d.text((x - f.getlength(lab) / 2, c + 270), lab, font=f, fill=GRAY)
        else:
            lv = eio((t - .3) / 1.8); hrs = int(round(30 * lv))
            battery(d, c, c - 40, lv, ACC, f"{hrs} soat")
            f = F2("bold", 64); lab = "quloqchin 6 + quti 24"
            d.text((c - f.getlength(lab) / 2, c + 230), lab, font=f, fill=GRAY + (int(255 * clamp((t - 1.8) / .4)),))
    elif kind == "tips":
        sizes = [(150, "S"), (195, "M"), (240, "L")]; xs = [c - 400, c, c + 400]
        for i, ((r, lab), x) in enumerate(zip(sizes, xs)):
            q = eback((t - .2 - i * .25) / .5)
            if q <= 0: continue
            rr = r * q; y = c - 60
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(214, 214, 220))
            d.ellipse((x - rr * .38, y - rr * .38, x + rr * .38, y + rr * .38), fill=(176, 176, 184))
            f = F2("black", 110); d.text((x - f.getlength(lab) / 2, c + 230), lab, font=f, fill=INK + (int(255 * clamp(q)),))
        if t > 1.4:
            pul = 1 + .05 * math.sin(t * 6); r = 230 * pul
            d.ellipse((c - r, c - 60 - r, c + r, c - 60 + r), outline=ACC, width=16)
    elif kind == "rotate":
        ang = math.sin(t * 2.4) * 16
        paste_c(cv, S["shadow"], c, c + 400, .8)
        paste_c(cv, S["bud"], c, c + bob * .3, 1, rot=ang, scale=1.45)
        q = eo((t - .3) / 1.0)
        if q > 0:
            box = (c - 440, c - 440, c + 440, c + 440)
            d.arc(box, start=200, end=200 + 120 * q, fill=ACC, width=26)
            a = math.radians(200 + 120 * q); hx, hy = c + 440 * math.cos(a), c + 440 * math.sin(a)
            tang = a + math.pi / 2
            d.polygon([(hx + 50 * math.cos(tang), hy + 50 * math.sin(tang)),
                       (hx + 38 * math.cos(tang + 2.3), hy + 38 * math.sin(tang + 2.3)),
                       (hx + 38 * math.cos(tang - 2.3), hy + 38 * math.sin(tang - 2.3))], fill=ACC)
    elif kind == "bass":
        n = 15; bw = 50; gap = 26; x0 = c - (n * bw + (n - 1) * gap) / 2
        for i in range(n):
            u = i / (n - 1)
            amp = (.35 + .65 * math.exp(-((u - .5) ** 2) / .08)) * p
            h = 80 + 560 * amp * (.55 + .45 * abs(math.sin(t * 5 + i * .7)))
            x = x0 + i * (bw + gap)
            d.rounded_rectangle((x, c - h / 2, x + bw, c + h / 2), radius=bw // 2, fill=ACC if abs(u - .5) < .3 else INK)
    elif kind == "volume":
        box = (c - 400, c - 420, c + 400, c + 380)
        d.arc(box, start=135, end=405, fill=LIGHT, width=70)
        q = eio((t - .3) / 1.5) * .6
        if q > 0.01: d.arc(box, start=135, end=135 + 270 * q, fill=ACC, width=70)
        lab = f"{int(round(q * 100))}%"; f = F2("black", 230)
        d.text((c - f.getlength(lab) / 2, c - 200), lab, font=f, fill=INK)
        f2 = F2("bold", 70); s2 = "60 daqiqa"
        d.text((c - f2.getlength(s2) / 2, c + 130), s2, font=f2, fill=GRAY + (int(255 * clamp((t - 1.6) / .4)),))
    elif kind == "noise":
        for k, (col, a) in enumerate([(INK, 1), (GRAY, .6), (LIGHT, .4)]):
            pts = sine_pts(80, IS - 80, c - 20 + (k - 1) * 30, 0, 1, 0, n=220, noise=jag(t * 1.4 + k, 11 + k, 260 * p * a))
            d.line(pts, fill=col, width=14 - k * 3, joint="curve")
        f = F2("black", 120); lab = "90 dB"
        d.text((c - f.getlength(lab) / 2, c + 330), lab, font=f, fill=RED + (int(255 * clamp((t - .8) / .4)),))
    elif kind in ("anc", "ancoff"):
        q = eio((t - .7) / 1.6)
        amt = 260 * (1 - q) * p
        pts = sine_pts(60, IS - 60, c, 26 * q, 3, t * 3, n=220, noise=jag(t * 1.4, 5, amt))
        col = tuple(int(INK[i] * (1 - q) + ACC[i] * q) for i in range(3))
        d.line(pts, fill=col, width=16, joint="curve")
        bud = S["bud_s"]
        r = 250; d.ellipse((c - r, c - r, c + r, c + r), fill=BG + (255,))
        d.ellipse((c - r, c - r, c + r, c + r), outline=ACC + (int(255 * q),), width=14)
        paste_c(cv, bud, c, c + bob * .4, 1, scale=1.25)
        f = F2("black", 90); lab = "ANC OFF" if kind == "ancoff" else "ANC ON"
        d.text((c - f.getlength(lab) / 2, c + 330), lab, font=f, fill=(GRAY if kind == "ancoff" else ACC) + (int(255 * clamp((t - 1.8) / .4)),))
    elif kind == "cloth":
        bud = S["bud"].copy()
        sh = Image.new("RGBA", bud.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        x = ((t * .7) % 1.4 - .2) * (bud.width + 400) - 200
        sd.polygon([(x, 0), (x + 90, 0), (x - 160, bud.height), (x - 250, bud.height)], fill=(255, 255, 255, 230))
        sd.polygon([(x + 130, 0), (x + 160, 0), (x - 90, bud.height), (x - 120, bud.height)], fill=(255, 255, 255, 200))
        a = ImageChops.multiply(sh.getchannel("A"), bud.getchannel("A")); sh.putalpha(a)
        sh2 = Image.new("RGBA", bud.size, (190, 170, 255, 0)); sh2.putalpha(a.point(lambda v: v * .5))
        bud.alpha_composite(sh2)
        paste_c(cv, S["shadow"], c, c + 400, .8)
        paste_c(cv, bud, c, c + bob * .3, 1, rot=-10, scale=1.45)
        rnd = random.Random(3)
        for i in range(5):
            st = .6 + i * .35; q = clamp((t - st) / .6)
            if 0 < q < 1:
                r = 60 * math.sin(q * math.pi)
                sparkle(d, c + rnd.uniform(-380, 380), c + rnd.uniform(-380, 300), r, ACC)
    elif kind == "brush":
        R_ = 330; d.ellipse((c - R_, c - R_ - 40, c + R_, c + R_ - 40), fill=(48, 48, 52))
        for gx in range(-8, 9):
            for gy in range(-8, 9):
                x, y = c + gx * 38, c - 40 + gy * 38
                if (x - c) ** 2 + (y - c + 40) ** 2 < (R_ - 30) ** 2:
                    d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(20, 20, 22))
        bx = c - 520 + ((t * .45) % 1) * 1040
        rnd = random.Random(7)
        for i in range(40):
            x = c + rnd.uniform(-280, 280); y = c - 40 + rnd.uniform(-280, 280)
            if (x - c) ** 2 + (y - c + 40) ** 2 > (R_ - 40) ** 2: continue
            cleaned = (t * .45) >= 1 or x < bx
            if not cleaned: d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=(196, 178, 140))
        d.rounded_rectangle((bx - 60, c - 40 - 420, bx + 60, c - 40 - 220), radius=30, fill=ACC)
        d.rounded_rectangle((bx - 30, c - 40 - 760, bx + 30, c - 40 - 420), radius=30, fill=INK)
        for k in range(-3, 4):
            d.line((bx + k * 16, c - 40 - 220, bx + k * 16, c - 40 - 150), fill=(150, 120, 255), width=10)
    elif kind == "drop":
        q = eback((t - .1) / .6); s = 300 * q
        if s > 1:
            cy = c - 60
            d.ellipse((c - s, cy - s * .3, c + s, cy + s * 1.7), fill=BLUE)
            d.polygon([(c, cy - s * 1.6), (c - s * .86, cy + s * .2), (c + s * .86, cy + s * .2)], fill=BLUE)
            d.ellipse((c - s * .55, cy + s * .2, c - s * .25, cy + s * .7), fill=(120, 190, 255))
        rnd = random.Random(2)
        for i in range(10):
            ph = (t * .6 + rnd.random()) % 1
            x = c + rnd.uniform(-480, 480) + math.sin(t * 2 + i) * 20; y = IS - 120 - ph * 1100; r = rnd.uniform(12, 30)
            d.ellipse((x - r, y - r, x + r, y + r), outline=BLUE + (int(200 * (1 - ph)),), width=6)
    elif kind == "transparent":
        paste_c(cv, S["bud"], c, c + bob * .3, 1, scale=1.25)
        for side in (-1, 1):
            for k in range(4):
                ph = ((t * .55 + k / 4) % 1)
                r = 600 - ph * 420
                a = int(255 * math.sin(ph * math.pi) * p)
                cx_ = c + side * 600
                box = (cx_ - r, c - r, cx_ + r, c + r)
                if side < 0: d.arc(box, -35, 35, fill=ACC + (a,), width=20)
                else: d.arc(box, 145, 215, fill=ACC + (a,), width=20)
    elif kind in ("situations", "places", "people"):
        xs = [c - 410, c, c + 410]
        labels = {"situations": ["Yo'l", "Kassa", "Suhbat"], "places": ["Transport", "Ofis", "Samolyot"],
                  "people": ["Talaba", "Hamkasb", "Ota-ona"]}[kind]
        for i, x in enumerate(xs):
            q = eback((t - .2 - i * .3) / .5)
            if q <= 0: continue
            r = 175 * q; y = c - 80
            d.ellipse((x - r, y - r, x + r, y + r), fill=(ACC if i == 1 else INK))
            s = q; col = WHITE
            g = (kind, i)
            if g == ("situations", 0):
                for k in range(-2, 3): d.rounded_rectangle((x - 80 * s, y + k * 38 * s - 12 * s, x + 80 * s, y + k * 38 * s + 12 * s), radius=8, fill=col)
            elif g == ("situations", 1):
                d.polygon([(x - 95 * s, y - 60 * s), (x + 95 * s, y - 60 * s), (x + 70 * s, y + 30 * s), (x - 70 * s, y + 30 * s)], fill=col)
                for wx in (-50, 50): d.ellipse((x + wx * s - 22 * s, y + 55 * s, x + wx * s + 22 * s, y + 99 * s), fill=col)
            elif g == ("situations", 2):
                d.rounded_rectangle((x - 100 * s, y - 75 * s, x + 100 * s, y + 55 * s), radius=40 * s, fill=col)
                d.polygon([(x - 50 * s, y + 50 * s), (x - 70 * s, y + 105 * s), (x - 5 * s, y + 50 * s)], fill=col)
                for k in (-1, 0, 1): d.ellipse((x + k * 48 * s - 14 * s, y - 24 * s, x + k * 48 * s + 14 * s, y + 4 * s), fill=ACC if i != 1 else INK)
            elif g == ("places", 0):
                d.rounded_rectangle((x - 100 * s, y - 90 * s, x + 100 * s, y + 70 * s), radius=30 * s, fill=col)
                d.rectangle((x - 75 * s, y - 60 * s, x + 75 * s, y - 5 * s), fill=INK)
                for wx in (-55, 55): d.ellipse((x + wx * s - 24 * s, y + 55 * s, x + wx * s + 24 * s, y + 103 * s), fill=col)
            elif g == ("places", 1):
                d.rectangle((x - 75 * s, y - 105 * s, x + 75 * s, y + 100 * s), fill=col)
                for gx in (-40, 0, 40):
                    for gy in (-70, -25, 20): d.rectangle((x + gx * s - 13 * s, y + gy * s - 13 * s, x + gx * s + 13 * s, y + gy * s + 13 * s), fill=ACC)
            elif g == ("places", 2):
                d.ellipse((x - 120 * s, y - 25 * s, x + 120 * s, y + 25 * s), fill=col)
                d.polygon([(x - 20 * s, y), (x + 40 * s, y), (x - 40 * s, y - 120 * s), (x - 80 * s, y - 120 * s)], fill=col)
                d.polygon([(x - 20 * s, y), (x + 40 * s, y), (x - 40 * s, y + 120 * s), (x - 80 * s, y + 120 * s)], fill=col)
                d.polygon([(x - 120 * s, y), (x - 95 * s, y), (x - 120 * s, y - 70 * s), (x - 140 * s, y - 70 * s)], fill=col)
            else:
                hs = [0.8, 1.0, 1.15][i] * s
                d.ellipse((x - 48 * hs, y - 100 * hs, x + 48 * hs, y - 4 * hs), fill=col)
                d.pieslice((x - 90 * hs, y + 10 * hs, x + 90 * hs, y + 190 * hs), 180, 360, fill=col)
            f = F2("bold", 62); lab = disp(labels[i])
            d.text((x - f.getlength(lab) / 2, c + 140), lab, font=f, fill=INK + (int(255 * clamp(q)),))
    elif kind == "micholes":
        rnd = random.Random(4)
        paste_c(cv, S["bud"], c, c + bob * .3, 1, scale=1.5)
        sc = 1.5
        bw, bh = S["bud"].size
        ox, oy = c - bw * sc / 2, c + bob * .3 - bh * sc / 2
        for (mx, my) in [(241, 139), (225, 480)]:
            x, y = ox + mx * sc, oy + my * sc
            r = 40 + 14 * math.sin(t * 6)
            d.ellipse((x - r, y - r, x + r, y + r), outline=ACC, width=12)
            for i in range(8):
                ph = (t * .8 + rnd.random()) % 1; a = rnd.uniform(0, 6.28)
                rr = 30 + ph * 220
                pr = 10 * (1 - ph)
                px, py = x + math.cos(a) * rr, y + math.sin(a) * rr
                d.ellipse((px - pr, py - pr, px + pr, py + pr), fill=(196, 178, 140, int(255 * (1 - ph))))
    elif kind == "stemdown":
        q = eio((t - .4) / 1.2)
        for yy in range(0, IS, 70): d.line((c, yy, c, yy + 36), fill=LIGHT, width=10)
        paste_c(cv, S["bud"], c, c - 60, 1, rot=50 * (1 - q), scale=1.4)
        if q > .95:
            check(d, c + 330, c - 330, 200, clamp((t - 1.6) / .5), GREEN, 34)
        ay = c + 420 + math.sin(t * 5) * 14
        d.polygon([(c - 60, ay), (c + 60, ay), (c, ay + 80)], fill=ACC)
    elif kind == "bluetooth":
        on = clamp((t - .9) / .3)
        for k in range(3):
            ph = ((t * .6 + k / 3) % 1)
            r = 220 + ph * 300
            if on > 0: d.ellipse((c - r, c - 120 - r, c + r, c - 120 + r), outline=ACC + (int(160 * (1 - ph) * on),), width=10)
        badge_circle(d, c, c - 120, 220, ACC if on > .5 else (150, 150, 158))
        bt_rune(d, c, c - 120, 150, WHITE, 26)
        tx, ty = c, c + 330
        bgc = tuple(int(LIGHT[i] * (1 - on) + GREEN[i] * on) for i in range(3))
        d.rounded_rectangle((tx - 150, ty - 80, tx + 150, ty + 80), radius=80, fill=bgc)
        kx = tx - 70 + 140 * on
        d.ellipse((kx - 66, ty - 66, kx + 66, ty + 66), fill=WHITE)
    elif kind == "forget":
        d.rounded_rectangle((c - 300, c - 520, c + 300, c + 520), radius=90, outline=INK, width=22)
        d.rounded_rectangle((c - 80, c - 480, c + 80, c - 450), radius=15, fill=INK)
        f = F2("semi", 52)
        rows = ["Pods Pro 3", "Soat", "Kolonka"]
        for i, lab in enumerate(rows):
            y = c - 330 + i * 150
            dx = 0; op = 1
            if i == 0:
                q = eio((t - 1.2) / .6); dx = -700 * q; op = 1 - q
                if t > .5 and q < .05:
                    d.rounded_rectangle((c - 250, y - 55, c + 250, y + 55), radius=30, fill=(ACC[0], ACC[1], ACC[2], 40))
            if op <= 0: continue
            d.rounded_rectangle((c - 240 + dx, y - 50, c + 240 + dx, y + 50), radius=28, outline=(200, 200, 206, int(255 * op)), width=6)
            bt_rune(d, c - 180 + dx, y, 34, ACC + (int(255 * op),), 8)
            d.text((c - 130 + dx, y - 30), lab, font=f, fill=INK + (int(255 * op),))
        if t > 1.0:
            q = eback((t - 1.0) / .4)
            fb = F2("bold", 56); lab = disp("Unutish")
            w_ = fb.getlength(lab) + 80
            d.rounded_rectangle((c - w_ / 2, c + 300, c + w_ / 2, c + 400), radius=50, fill=RED + (int(255 * clamp(q)),))
            d.text((c - fb.getlength(lab) / 2, c + 318), lab, font=fb, fill=WHITE + (int(255 * clamp(q)),))
    elif kind == "timer":
        rem = max(0, 30 - int(t * 6)) if t > .4 else 30
        frac = rem / 30
        box = (c - 420, c - 460, c + 420, c + 380)
        d.arc(box, 0, 360, fill=LIGHT, width=46)
        if frac > 0: d.arc(box, -90, -90 + 360 * frac, fill=ACC, width=46)
        f = F2("black", 260); lab = str(rem)
        d.text((c - f.getlength(lab) / 2, c - 250), lab, font=f, fill=INK)
        f2 = F2("bold", 64); s2 = "soniya"
        d.text((c - f2.getlength(s2) / 2, c + 80), s2, font=f2, fill=GRAY)
    elif kind == "charge":
        paste_c(cv, S["shadow"], c, c + 380, .8)
        paste_c(cv, S["case"], c, c + 130, 1, scale=1.2)
        lv = eio((t - .3) / 1.6)
        for i in range(4):
            on = lv > (i + .5) / 4
            x = c - 210 + i * 140
            d.rounded_rectangle((x - 50, c - 420, x + 50, c - 300), radius=24, fill=(GREEN if on else LIGHT))
        bx, by = c + 340, c - 120; s = 1 + .08 * math.sin(t * 6)
        d.polygon([(bx + 20 * s, by - 130 * s), (bx - 70 * s, by + 15 * s), (bx - 5 * s, by + 15 * s), (bx - 25 * s, by + 130 * s),
                   (bx + 70 * s, by - 20 * s), (bx + 5 * s, by - 20 * s)], fill=GOLD)
    elif kind == "shield":
        q = eback((t - .1) / .6); s = q
        pts = [(c, c - 430 * s), (c + 340 * s, c - 300 * s), (c + 320 * s, c + 40 * s), (c, c + 400 * s), (c - 320 * s, c + 40 * s), (c - 340 * s, c - 300 * s)]
        if s > .02:
            d.polygon(pts, fill=ACC); d.line(pts + [pts[0]], fill=ACC, width=60, joint="curve")
            check(d, c, c - 30, 340, clamp((t - .7) / .6), WHITE, 56)
        f = F2("black", 90); lab = "1 YIL"
        d.text((c - f.getlength(lab) / 2, c + 450), lab, font=f, fill=INK + (int(255 * clamp((t - 1.2) / .4)),))
    elif kind == "stars":
        for i in range(5):
            x = c - 480 + i * 240; y = c - 60
            q = eback((t - .3 - i * .18) / .4)
            d.polygon(star_poly(x, y, 105, 45), fill=LIGHT)
            if q > 0: d.polygon(star_poly(x, y, 105 * q, 45 * q), fill=GOLD)
        for i in range(3):
            q = eo((t - 1.3 - i * .2) / .5); y = c + 170 + i * 85
            if q > 0: d.rounded_rectangle((c - 420, y, c - 420 + (840 if i < 2 else 520) * q, y + 44), radius=22, fill=LIGHT)
    elif kind == "calendar":
        d.rounded_rectangle((c - 440, c - 420, c + 440, c + 420), radius=70, fill=WHITE, outline=LIGHT, width=8)
        d.rounded_rectangle((c - 440, c - 420, c + 440, c - 250), radius=70, fill=ACC)
        d.rectangle((c - 440, c - 320, c + 440, c - 250), fill=ACC)
        for i in range(28):
            gx, gy = i % 7, i // 7; x = c - 360 + gx * 120; y = c - 150 + gy * 135
            q = eback((t - .3 - i * .05) / .3)
            d.ellipse((x - 42, y - 42, x + 42, y + 42), fill=LIGHT)
            if q > 0:
                r = 42 * q; d.ellipse((x - r, y - r, x + r, y + r), fill=ACC)
                if q > .8: check(d, x, y, 48, 1, WHITE, 10)
    elif kind == "list":
        labs = ["ANC", "Batareya", "Kafolat"]
        f = F2("bold", 92)
        for i, lab in enumerate(labs):
            y = c - 300 + i * 260
            q = eo((t - .2 - i * .45) / .4)
            if q <= 0: continue
            x = c - 380 - (1 - q) * 80
            d.rounded_rectangle((x - 80, y - 80, x + 80, y + 80), radius=40, fill=ACC + (int(255 * q),))
            check(d, x, y, 100, clamp((t - .45 - i * .45) / .4), WHITE, 22)
            d.text((x + 140, y - 58), lab, font=f, fill=INK + (int(255 * q),))
    elif kind == "micwave":
        mx, my = c + 200, c - 60
        d.rounded_rectangle((mx - 100, my - 260, mx + 100, my + 70), radius=100, fill=INK)
        for k in range(-3, 4): d.line((mx - 70, my - 120 + k * 32, mx + 70, my - 120 + k * 32), fill=(70, 70, 76), width=8)
        d.arc((mx - 170, my - 160, mx + 170, my + 180), 0, 180, fill=INK, width=24)
        d.line((mx, my + 180, mx, my + 330), fill=INK, width=24)
        d.line((mx - 120, my + 330, mx + 120, my + 330), fill=INK, width=24)
        pts = sine_pts(60, mx - 160, my - 90, 0, 1, 0, n=140, noise=jag(t * 1.5, 9, 160 * p))
        d.line(pts, fill=RED, width=14, joint="curve")
        r = 140 + 20 * math.sin(t * 6)
        d.ellipse((mx - r - 60, my - 90 - r - 60, mx + r + 60, my - 90 + r + 60), outline=ACC + (int(255 * clamp((t - .8) / .4)),), width=12)
    elif kind == "inverse":
        q = eo((t - .2) / .8)
        ph = t * 3
        p1 = sine_pts(80, 80 + (IS - 160) * q, c - 230, 150, 3, ph)
        p2 = sine_pts(80, 80 + (IS - 160) * q, c + 230, -150, 3, ph)
        if len(p1) > 1:
            d.line(p1, fill=RED, width=18, joint="curve"); d.line(p2, fill=ACC, width=18, joint="curve")
        d.line((80, c, IS - 80, c), fill=LIGHT, width=6)
        f = F2("bold", 60)
        for lab, y, col in (("Shovqin", c - 470, RED), ("Teskari to'lqin", c + 400, ACC)):
            lab = disp(lab); d.text((c - f.getlength(lab) / 2, y), lab, font=f, fill=col + (int(255 * q),))
    elif kind == "cancel":
        q = eio((t - .3) / 1.4)
        ph = t * 3; off = 230 * (1 - q); amp = 150 * (1 - q * .15)
        if q < .98:
            d.line(sine_pts(80, IS - 80, c - off, amp, 3, ph), fill=RED + (int(255 * (1 - q * .9)),), width=18, joint="curve")
            d.line(sine_pts(80, IS - 80, c + off, -amp, 3, ph), fill=ACC + (int(255 * (1 - q * .9)),), width=18, joint="curve")
        flat = clamp((q - .7) / .3)
        if flat > 0:
            d.line((80, c, 80 + (IS - 160) * flat, c), fill=INK, width=22)
        f = F2("black", 110); lab = "= 0"
        d.text((c - f.getlength(lab) / 2, c + 300), lab, font=f, fill=INK + (int(255 * clamp((t - 1.8) / .4)),))

def icon_layer(kind, t):
    cv = Image.new("RGBA", (IS, IS), (0, 0, 0, 0))
    draw_icon(kind, cv, t)
    return cv.reduce(2)

# ---------------- audio ----------------
def tts(text, path):
    wav = path + ".wav"
    subprocess.run(["espeak-ng", "-v", "uz+m3", "-s", "178", "-p", "38", "-g", "2", "-w", wav, tts_text(text)], check=True)
    out = path + "_44.wav"
    # tozalash: past-chastotali shovqin, issiqroq tembr, kompressiya
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-af",
                    "highpass=f=90,lowpass=f=7500,equalizer=f=220:t=q:w=1:g=3,equalizer=f=3200:t=q:w=1.5:g=-2,"
                    "acompressor=threshold=-18dB:ratio=3:attack=5:release=80,aresample=44100",
                    "-ac", "1", "-f", "f32le", out], check=True)
    a = np.fromfile(out, dtype=np.float32)
    nz = np.nonzero(np.abs(a) > 0.01)[0]
    if len(nz): a = a[max(0, nz[0] - 400): nz[-1] + 2000]
    return (a / (np.abs(a).max() + 1e-9) * 0.9).astype(np.float32)

def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))

def sfx_whoosh(dur=.45, up=True):
    n = int(dur * SR); x = np.random.randn(n)
    out = np.zeros(n); hop = 512; win = np.hanning(hop * 2)
    for i in range(0, n - hop * 2, hop):
        u = i / n; fc = 300 + (3500 if up else 1500) * (u if up else 1 - u)
        seg = x[i:i + hop * 2] * win
        sp = np.fft.rfft(seg); fr = np.fft.rfftfreq(hop * 2, 1 / SR)
        sp *= np.exp(-((np.log(fr + 1) - math.log(fc)) ** 2) / .5)
        out[i:i + hop * 2] += np.fft.irfft(sp)
    e = np.sin(np.linspace(0, math.pi, n)) ** 2
    out = out * e; return out / (np.abs(out).max() + 1e-9) * .5

def sfx_pop(f0=520, f1=980, dur=.09):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f0 + (f1 - f0) * (tt / dur); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env_exp(n, .025) * .45

def sfx_click():
    n = int(.03 * SR); return (np.random.randn(n) * env_exp(n, .003) * .3 + np.sin(2 * np.pi * 2400 * np.arange(n) / SR) * env_exp(n, .006) * .3)

def sfx_ding():
    n = int(1.6 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1318.5 * tt) * .5 + np.sin(2 * np.pi * 1975.5 * tt) * .25 + np.sin(2 * np.pi * 2637 * tt) * .1) * env_exp(n, .35) * .5

def sfx_impact():
    n = int(.7 * SR); tt = np.arange(n) / SR
    f = 40 + 90 * np.exp(-tt / .05); ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * env_exp(n, .18) * .8 + np.random.randn(n) * env_exp(n, .02) * .15)

def sfx_riser(dur=1.2):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = 200 + 1200 * (tt / dur) ** 2; ph = 2 * np.pi * np.cumsum(f) / SR
    w = sfx_whoosh(dur, True)[:n]
    return (np.sin(ph) * .12 * (tt / dur) ** 2 + w * .6) * np.minimum(1, (dur - tt) / .05)

NOTE = lambda m: 440 * 2 ** ((m - 69) / 12)
PROGS = [[57, 53, 48, 55], [50, 46, 53, 48], [52, 48, 55, 50], [55, 52, 48, 50], [53, 50, 46, 48]]

def music(total, seed):
    rnd = random.Random(seed); bpm = 100 + rnd.choice([-6, 0, 4]); beat = 60 / bpm
    prog = PROGS[seed % len(PROGS)]; n = int(total * SR) + SR
    out = np.zeros(n)
    bar = beat * 4
    sos_pad = butter(2, 1400, "low", fs=SR, output="sos")
    nb = int(total / bar) + 2
    for b in range(nb):
        root = prog[b % 4]; st = int(b * bar * SR); ln = int(bar * SR)
        if st >= n: break
        tt = np.arange(ln) / SR
        chord = [root, root + (3 if (b % 4) in (0, 2) and seed % 2 else 4), root + 7, root + 12]
        pad = sum(np.sin(2 * np.pi * NOTE(m + 12) * tt * (1 + dt)) for m in chord for dt in (-.002, .002)) / 8
        envp = np.minimum(1, tt / .3) * np.minimum(1, (bar - tt) / .3)
        seg = pad * envp * .22
        bass = np.sin(2 * np.pi * NOTE(root - 12) * tt) * .35 * np.minimum(1, tt / .02) * np.exp(-tt / 1.2)
        seg = seg + bass
        e = min(n, st + ln); out[st:e] += seg[:e - st]
        # arpeggio pluck (8-lik)
        for k in range(8):
            m = chord[[0, 2, 1, 3, 2, 1, 3, 2][k]] + 24
            s0 = st + int(k * beat / 2 * SR); ln2 = int(.35 * SR)
            if s0 + ln2 >= n: break
            t2 = np.arange(ln2) / SR
            pl = (np.sin(2 * np.pi * NOTE(m) * t2) + .3 * np.sin(4 * np.pi * NOTE(m) * t2)) * np.exp(-t2 / .09) * .09
            out[s0:s0 + ln2] += pl
    out = sosfilt(sos_pad, out) * 1.0 + out * 0  # yumshoq
    # drums
    kick = sfx_impact()[: int(.4 * SR)] * .7; hat = np.random.randn(int(.05 * SR)) * env_exp(int(.05 * SR), .008)
    hat = sosfilt(butter(2, 7000, "high", fs=SR, output="sos"), hat) * .12
    clap = sosfilt(butter(2, [900, 4000], "band", fs=SR, output="sos"), np.random.randn(int(.15 * SR))) * env_exp(int(.15 * SR), .03) * .25
    nbeats = int(total / beat) + 1
    for i in range(nbeats):
        s0 = int(i * beat * SR)
        if s0 + len(kick) < n and i % 2 == 0: out[s0:s0 + len(kick)] += kick
        if s0 + len(clap) < n and i % 4 == 2: out[s0:s0 + len(clap)] += clap
        for hh in (0, .5):
            s1 = int((i + hh) * beat * SR)
            if s1 + len(hat) < n: out[s1:s1 + len(hat)] += hat * (1 if hh else .6)
    return out[: int(total * SR)] / (np.abs(out).max() + 1e-9) * .5


VOICE_DIR = "/home/user/ovozlar"

def find_user_voice(num):
    if not os.path.isdir(VOICE_DIR): return None
    for f in sorted(os.listdir(VOICE_DIR)):
        if re.match(rf"^0*{int(num)}\b|^0*{int(num)}[ ._-]", f) and not f.endswith((".txt", ".md")):
            return os.path.join(VOICE_DIR, f)
    return None

def load_user_voice(path):
    raw = path + ".f32" if False else os.path.join(TMP, "uv_" + os.path.basename(path) + ".f32")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-vn", "-af",
                    "highpass=f=80,afftdn=nr=10:nf=-45,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120,"
                    "aresample=44100", "-ac", "1", "-f", "f32le", raw], check=True)
    a = np.fromfile(raw, dtype=np.float32)
    return a / (np.percentile(np.abs(a), 99.9) + 1e-9) * 0.8


def norm_uz(s):
    s = s.lower()
    for a, b in (("ʻ", ""), ("’", ""), ("'", ""), ("`", ""), ("ç", "ch"), ("ş", "sh"), ("ı", "i"), ("q", "k"), ("x", "h"),
                 ("kh", "h"), ("o", "a"), ("u", "a"), ("e", "i"), ("y", "i"), ("w", "v"), ("ts", "ds")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9 ]", "", s)

def asr_boundaries(path, texts, T0, T1):
    import json, difflib
    jf = os.path.join("/tmp/asr", os.path.basename(path).split(".")[0] + ".json")
    if not os.path.exists(jf): jf = os.path.join("/tmp/asr", os.path.basename(path).split(".")[0][:2] + ".json")
    if not os.path.exists(jf): return None
    words = json.load(open(jf))
    words = [w for w in words if w[0] < T1 + .5]
    nW = len(words); N = len(texts)
    L = np.cumsum([len(x) for x in texts]); exp_ = [T0 + (T1 - T0) * L[k] / L[-1] for k in range(N - 1)]
    def score(k, i):
        ref = norm_uz(" ".join(texts[k + 1].split()[:3]))
        hyp = norm_uz(" ".join(w[2] for w in words[i:i + 4]))[:len(ref) + 2]
        sim = difflib.SequenceMatcher(None, ref, hyp).ratio()
        punct = 2.0 if words[i - 1][2].endswith((".", "?", "!", ",")) else 0
        punct += 0.5 if words[i - 1][2].endswith((".", "?", "!")) else 0
        gap = min(words[i][0] - words[i - 1][1], .6) * 3
        return sim * 6 + punct + gap - abs(words[i][0] - exp_[k]) / (T1 - T0) * 6
    INF = -1e18; best = np.full((N - 1, nW), INF); prv = np.zeros((N - 1, nW), int)
    for i in range(1, nW): best[0, i] = score(0, i)
    for k in range(1, N - 1):
        run, ri = INF, -1
        for i in range(1, nW):
            if best[k - 1, i - 1] > run: run, ri = best[k - 1, i - 1], i - 1
            if ri >= 0: best[k, i] = run + score(k, i); prv[k, i] = ri
    i = int(np.argmax(best[N - 2])); idx = [i]
    for k in range(N - 2, 0, -1): i = prv[k, i]; idx.append(i)
    idx = idx[::-1]
    cuts = [(words[i - 1][1] + words[i][0]) / 2 for i in idx]
    print("ASR", os.path.basename(path), [words[i][2] for i in idx], [round(c, 1) for c in cuts], flush=True)
    return cuts

def split_user_voice(path, texts, tmp):
    """Yozuvni pauzalar bo'yicha len(texts) qismga bo'ladi (DP: kutilgan joyga yaqin + uzun pauza)."""
    a = load_user_voice(path); hop = int(.02 * SR)
    rms = np.sqrt(np.convolve(a ** 2, np.ones(hop) / hop, "same")[::hop] + 1e-12)
    db = 20 * np.log10(rms + 1e-9); thr = max(np.percentile(db, 95) - 30, np.percentile(db, 15) + 6)
    sil = db < thr
    voiced = np.nonzero(~sil)[0]
    first, last = voiced[0], voiced[-1]
    gaps = []; i = first
    while i < last:
        if sil[i]:
            j = i
            while j < last and sil[j]: j += 1
            if (j - i) * .02 >= .12: gaps.append(((i + j) / 2 * .02, (j - i) * .02, i, j))
            i = j
        else: i += 1
    N = len(texts); T0, T1 = first * .02, last * .02
    asr_cuts = asr_boundaries(path, texts, T0, T1)
    if asr_cuts:
        # har bir so'z chegarasini eng yaqin pauzaga (±0.45s) suramiz
        cut_times = []
        for ct in asr_cuts:
            near = [g for g in gaps if abs(g[0] - ct) < .45]
            cut_times.append(min(near, key=lambda g: abs(g[0] - ct) - g[1])[0] if near else ct - .08)
        gaps = [(ct, 1, 0, 0) for ct in cut_times]

    L = np.cumsum([len(x) for x in texts]); exp_ = [T0 + (T1 - T0) * L[k] / L[-1] for k in range(N - 1)]
    m = len(gaps)
    if m < N - 1:
        raise SystemExit(f"{path}: pauzalar yetarli emas ({m} ta topildi, {N-1} ta kerak). Qismlar orasida 1 soniya to'xtang.")
    INF = 1e18; cost = np.full((N - 1, m), INF); prv = np.zeros((N - 1, m), int)
    def c(k, j): return abs(gaps[j][0] - exp_[k]) / (T1 - T0) * 12 - min(gaps[j][1], 1.2) * 5
    for j in range(m): cost[0, j] = c(0, j)
    for k in range(1, N - 1):
        best = INF; bj = -1
        for j in range(m):
            if j - 1 >= 0 and cost[k - 1, j - 1] < best: best, bj = cost[k - 1, j - 1], j - 1
            if bj >= 0: cost[k, j] = best + c(k, j); prv[k, j] = bj
    j = int(np.argmin(cost[N - 2])); cuts = [j]
    for k in range(N - 2, 0, -1): j = prv[k, j]; cuts.append(j)
    cuts = cuts[::-1]
    bounds = [first * hop] + [int(gaps[j][0] / .02 * hop) for j in cuts] + [last * hop + hop]
    segs = []
    for k in range(N):
        f0, f1 = bounds[k] // hop, bounds[k + 1] // hop
        nz = np.nonzero(~sil[f0:f1])[0]
        if len(nz): seg = a[max(0, (f0 + nz[0]) * hop - 2000): min(len(a), (f0 + nz[-1] + 1) * hop + 3500)]
        else: seg = a[bounds[k]:bounds[k + 1]]
        segs.append(seg.astype(np.float32))
    with open(os.path.join(tmp, "split.txt"), "w") as f:
        for k, sgm in enumerate(segs): f.write(f"{k}: {len(sgm)/SR:.2f}s  {texts[k][:50]}\n")
    print("SPLIT", path, [round(len(x) / SR, 1) for x in segs], flush=True)
    return segs

# ---------------- timeline ----------------
def build(v):
    sprites()
    slug = v["slug"]; np.random.seed(v["seed"]); tmp = os.path.join(TMP, slug); os.makedirs(tmp, exist_ok=True)
    scenes = []
    scenes.append(dict(type="hook", title=up(disp(v["hook"][0])), sub=disp(v["hook"][1]), voice=v["hook"][2]))
    for i, (ic, ti, su, vo) in enumerate(v["tips"]):
        scenes.append(dict(type="tip", icon=ic, title=up(disp(ti)), sub=disp(su), voice=vo, n=i + 1, of=len(v["tips"])))
    scenes.append(dict(type="product", features=[disp(f) for f in v["features"]], voice=v["product_voice"]))
    scenes.append(dict(type="cta", voice=CTA_VOICE))
    t = 0.0; voices = []
    ext = v.get("voice") or find_user_voice(v["slug"][:2])
    segs = split_user_voice(ext, [sc["voice"] for sc in scenes], tmp) if ext else None
    for k, sc in enumerate(scenes):
        a = segs[k] if segs else tts(sc["voice"], os.path.join(tmp, f"v{k}"))
        lead = .35 if sc["type"] != "hook" else .15
        dur = max(2.4, lead + len(a) / SR + (.3 if sc["type"] != "cta" else 1.0))
        if sc["type"] == "product": dur = max(dur, 4.2)
        sc.update(start=t, dur=dur, vstart=t + lead, vlen=len(a) / SR, caption=disp(sc["voice"]))
        voices.append((t + lead, a)); t += dur
    total = t
    # captions chunks
    for sc in scenes:
        words = sc["caption"].split(); chunks = []; cur = []
        for w_ in words:
            cur.append(w_)
            if len(" ".join(cur)) > 26 or w_.endswith((".", "!", "?", ",")) and len(cur) >= 2:
                chunks.append(" ".join(cur)); cur = []
        if cur: chunks.append(" ".join(cur))
        L = sum(len(c) + 3 for c in chunks); acc = 0; timed = []
        for c_ in chunks:
            s0 = sc["vstart"] + sc["vlen"] * acc / L; acc += len(c_) + 3
            timed.append((s0, sc["vstart"] + sc["vlen"] * acc / L, c_))
        sc["chunks"] = timed
    # ---- audio mix ----
    n = int(total * SR) + 1
    vo = np.zeros(n)
    for st, a in voices:
        s0 = int(st * SR); e = min(n, s0 + len(a)); vo[s0:e] += a[:e - s0]
    mu = music(total, v["seed"]); mu = np.pad(mu, (0, max(0, n - len(mu))))
    envv = np.convolve(np.abs(vo), np.ones(4410) / 4410, mode="same")
    envv = np.clip(envv / (envv.max() + 1e-9) * 3, 0, 1)
    duck = 0.62 - 0.42 * envv
    mix = vo * 1.0 + mu[:n] * duck
    def add(sig, at, g=1.0):
        s0 = int(at * SR)
        if s0 >= n: return
        e = min(n, s0 + len(sig)); mix[s0:e] += sig[:e - s0] * g
    add(sfx_impact(), 0, .7); add(sfx_whoosh(.5), 0, .5)
    for sc in scenes[1:]:
        if sc["type"] == "cta":
            add(sfx_riser(1.0), sc["start"] - 1.0, .45); add(sfx_impact(), sc["start"], .6); add(sfx_ding(), sc["start"] + .5, .5)
        else:
            add(sfx_whoosh(.4), sc["start"] - .12, .45)
        if sc["type"] == "tip":
            add(sfx_click(), sc["start"] + .25, .8); add(sfx_pop(), sc["start"] + .45, .6)
        if sc["type"] == "product":
            for j in range(4): add(sfx_pop(700, 1200), sc["start"] + 1.0 + j * .35, .5)
    hk = scenes[0]
    for j in range(len(hk["title"].split())): add(sfx_pop(400 + j * 60, 800 + j * 60, .07), .12 + j * .12, .35)
    mix = np.tanh(mix * 1.1) * .95
    # fade out
    fo = int(.6 * SR); mix[-fo:] *= np.linspace(1, 0, fo)
    wav = os.path.join(tmp, "mix.f32"); mix.astype(np.float32).tofile(wav)
    render_video(v, scenes, total, wav)

def caption_img(text):
    return pill(text, "semi", 46, CARD_FG, CARD + (235,), padx=36, pady=18)

@functools.lru_cache(maxsize=None)
def cached_caption(text): return caption_img(text)

@functools.lru_cache(maxsize=None)
def cta_caption(text): return pill(text, "semi", 46, CTA_BG, CTA_FG + (235,), padx=36, pady=18)

def draw_scene(sc, t, layer, total_t, v):
    S = sprites(); typ = sc["type"]; dur = sc["dur"]
    if typ == "hook":
        tag = pill(disp(v["tag"]), "xbold", 38, ACC_FG, ACC + (255,), track=4)
        q = eback((t - .05) / .4); put(layer, tag, W / 2, 470, clamp(q), .6 + .4 * q)
        words = sc["title"].split(); f = font("black", 112)
        lines = wrap(sc["title"], f, 930); y = 640; wi = 0
        for li, line in enumerate(lines):
            ws = line.split(); widths = [f.getlength(w_) for w_ in ws]; sp = f.getlength(" ")
            x = W / 2 - (sum(widths) + sp * (len(ws) - 1)) / 2
            for w_, ww in zip(ws, widths):
                q = eback((t - .12 - wi * .12) / .35)
                im = text_img(w_, "black", 112, INK if wi % 3 != 1 or len(words) < 3 else ACC, maxw=2000)
                put(layer, im, x + ww / 2, y + 60 + (1 - clamp(q)) * 40, clamp(q * 1.5), .7 + .3 * q)
                x += ww + sp; wi += 1
            y += 126
        q = eo((t - .35 - wi * .12) / .5)
        put(layer, text_img(sc["sub"], "med", 50, GRAY), W / 2, y + 70 + (1 - q) * 30, q)
        q2 = eo((t - .2) / .8)
        b = math.sin(t * 2.4) * 16
        put(layer, S["shadow_s"], W / 2, 1500, q2 * .9)
        im = S["bud_s"].rotate(-14 + math.sin(t * 1.6) * 6, Image.BICUBIC, expand=True)
        put(layer, im, W / 2 - 90, 1340 + b + (1 - q2) * 200, q2)
        im = S["budL_s"].rotate(14 - math.sin(t * 1.6) * 6, Image.BICUBIC, expand=True)
        put(layer, im, W / 2 + 90, 1340 - b + (1 - q2) * 200, q2)
    elif typ == "tip":
        q = eback((t - .15) / .4)
        put(layer, pill(f"{sc['n']} / {sc['of']}", "xbold", 40, BG, INK + (255,)), W / 2, 330, clamp(q), .6 + .4 * clamp(q))
        qi = eo((t - .1) / .5)
        put(layer, icon_layer(sc["icon"], t), W / 2, 760 + (1 - qi) * 60, qi)
        q = eo((t - .3) / .45)
        tim = text_img(sc["title"], "black", 92, INK, maxw=940)
        put(layer, tim, W / 2, 1140 + tim.height / 2 + (1 - q) * 40, q)
        q = eo((t - .5) / .45)
        put(layer, text_img(sc["sub"], "med", 48, GRAY, maxw=900), W / 2, 1150 + tim.height + 60 + (1 - q) * 30, q)
    elif typ == "product":
        q = eo((t - .05) / .5)
        put(layer, text_img("Pods Pro 3 ANC", "black", 104, INK), W / 2, 330 + (1 - q) * 30, q)
        q = eo((t - .2) / .5)
        put(layer, text_img("1 yil kafolat · Uzum Market", "med", 44, GRAY), W / 2, 420, q)
        qc = eo((t - .1) / .8); b = math.sin(t * 2.2) * 12
        put(layer, S["shadow"], W / 2, 1010, qc)
        put(layer, S["case"], W / 2, 830 + (1 - qc) * 80, qc)
        for i, (k, x) in enumerate((("bud_s", W / 2 - 150), ("budL_s", W / 2 + 150))):
            qb = eo((t - .3 - i * .1) / .8)
            im = S[k].rotate((-18 if i == 0 else 18) + math.sin(t * 1.5 + i) * 5, Image.BICUBIC, expand=True)
            put(layer, im, x, 560 + (b if i == 0 else -b) + (1 - qb) * 150, qb * .999)
        feats = sc["features"]
        for j, ft in enumerate(feats):
            qf = eback((t - 1.0 - j * .35) / .4)
            if qf <= 0: continue
            chip = feature_chip(ft, THEME.get("name"))
            cx = W / 2 + (-238 if j % 2 == 0 else 238); cy = 1170 + (j // 2) * 130
            put(layer, chip, cx, cy, clamp(qf), .7 + .3 * qf)
    elif typ == "cta":
        q = eo((t - .3) / .4)
        put(layer, pill("BUYURTMA BERING", "xbold", 36, CTA_BG, CTA_FG + (255,), track=4), W / 2, 420, q)
        q = eback((t - .35) / .45)
        put(layer, bag_icon(CTA_FG, CTA_BG), W / 2, 640 + math.sin(t * 2) * 10, clamp(q), .5 + .5 * q)
        q = eo((t - .5) / .45)
        put(layer, text_img("Uzum Market", "black", 128, CTA_FG), W / 2, 880 + (1 - q) * 40, q)
        q = eo((t - .65) / .45)
        put(layer, text_img(disp("“Airpods market” do'koni"), "bold", 62, CTA_FG), W / 2, 1000 + (1 - q) * 30, q)
        q = eback((t - .9) / .45)
        hp = pill("↑  Havola profilda", "black", 58, CTA_BG, CTA_FG + (255,), padx=48, pady=24)
        put(layer, hp, W / 2, 1210 - abs(math.sin(t * 3.5)) * 18, clamp(q), .7 + .3 * q)
        q = eo((t - 1.3) / .5)
        put(layer, text_img(disp("Saqlab qo'ying va do'stingizga yuboring"), "med", 42, CTA_SUB), W / 2, 1400, q)

@functools.lru_cache(maxsize=None)
def feature_chip(txt, _k=None):
    t = text_img(txt, "semi", 37, CARD_FG, maxw=360, lh=1.1)
    w, h = 455, 112
    im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), radius=56, fill=CARD + (255,), outline=LIGHT + (255,), width=3)
    d.ellipse((30, h - 34, 98, h + 34), fill=ACC)
    check(d, 64, h, 40, 1, ACC_FG, 8)
    im = im.resize((w, h), Image.LANCZOS)
    im.alpha_composite(t, (64 + (w - 64 - t.width) // 2 - 6, (h - t.height) // 2 + 2))
    return im

@functools.lru_cache(maxsize=None)
def bag_icon(fg=WHITE, bg=ACC):
    s = 2; im = Image.new("RGBA", (260 * s, 260 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((30 * s, 80 * s, 230 * s, 250 * s), radius=36 * s, fill=fg)
    d.arc((80 * s, 20 * s, 180 * s, 130 * s), 180, 360, fill=fg, width=16 * s)
    d.arc((80 * s, 120 * s, 180 * s, 200 * s), 0, 180, fill=bg, width=14 * s)
    return im.resize((260, 260), Image.LANCZOS)

@functools.lru_cache(maxsize=None)
def arrow_up():
    s = 2; im = Image.new("RGBA", (120 * s, 120 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(60 * s, 0), (120 * s, 60 * s), (0, 60 * s)], fill=WHITE); d.rectangle((44 * s, 55 * s, 76 * s, 120 * s), fill=WHITE)
    return im.resize((120, 120), Image.LANCZOS)

def render_video(v, scenes, total, wav):
    out = os.path.join(v.get("out", OUT), v["slug"] + ".mp4")
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", wav,
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", "-shortest", out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    bg_light = THEME["bgimg"]() if THEME.get("bgimg") else Image.new("RGBA", (W, H), BG + (255,))
    brand = text_img("AIRPODS MARKET", "semi", 28, GRAY, maxw=2000, track=6)
    brand_w = text_img("AIRPODS MARKET", "semi", 28, CTA_FG, maxw=2000, track=6)
    nf = int(total * FPS)
    for fi in range(nf):
        T = fi / FPS
        sc = next(s for s in reversed(scenes) if s["start"] <= T + 1e-6)
        t = T - sc["start"]
        cta = sc["type"] == "cta"
        base = THEME["base_fn"](sc, t, bg_light) if THEME.get("base_fn") else None
        if base is not None:
            frame = base
        else:
            frame = bg_light.copy()
            if cta:
                r = eio(t / .55) * 2300
                d = ImageDraw.Draw(frame); d.ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), fill=CTA_BG)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if not (THEME.get("scene_fn") and THEME["scene_fn"](sc, t, layer, v)):
            draw_scene(sc, t, layer, total, v)
        # sahna o'tishi: kirishda chapga siljish, chiqishda so'nish
        tin = eo(t / .32); tout = clamp((sc["dur"] - t) / .14) if sc is not scenes[-1] else 1
        first = sc is scenes[0] or cta
        tr = THEME.get("trans", "slide")
        dx = int((1 - tin) * 140) if (not first and tr == "slide") else 0
        dy = int((1 - tin) * 160) if (not first and tr == "up") else 0
        op = min(tout, 1.0)
        if not first and tr == "zoom" and tin < .999:
            sc_ = 1.12 - .12 * tin
            big = layer.resize((int(W * sc_), int(H * sc_)), Image.BILINEAR)
            layer = big.crop(((big.width - W) // 2, (big.height - H) // 2, (big.width - W) // 2 + W, (big.height - H) // 2 + H))
            op = min(op, tin)
        if not first and tr == "up": op = min(op, tin)
        if op < .999: layer.putalpha(layer.getchannel("A").point(lambda a: int(a * op)))
        frame.alpha_composite(layer, (dx, dy))
        d = ImageDraw.Draw(frame)
        # progress bar + brend
        d.rounded_rectangle((60, 96, W - 60, 104), radius=4, fill=CTA_SUB if cta else LIGHT)
        d.rounded_rectangle((60, 96, 60 + (W - 120) * (T / total), 104), radius=4, fill=CTA_FG if cta else ACC)
        frame.alpha_composite(brand_w if cta else brand, (60, 128))
        # subtitr
        for s0, s1, txt in sc["chunks"]:
            if THEME.get("cap_hide") and THEME["cap_hide"](sc, T - sc["start"]): break
            if s0 <= T < s1:
                im = cta_caption(txt) if cta else cached_caption(txt); qa = eo((T - s0) / .12)
                put(frame, im, W / 2, 1560 + (1 - qa) * 12, qa)
                break
        pr.stdin.write(frame.convert("RGB").tobytes())
    pr.stdin.close(); pr.wait()
    print("OK", out, round(total, 1), "s", flush=True)

if __name__ == "__main__":
    sel = sys.argv[1:]
    vids = [v for v in VIDEOS if not sel or any(v["slug"].startswith(s) for s in sel)]
    if len(vids) == 1: build(vids[0])
    else:
        from multiprocessing import Pool
        with Pool(4) as p: p.map(build, vids)
