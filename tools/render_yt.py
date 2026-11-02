import sys, os, numpy as np
from PIL import Image, ImageDraw, ImageFilter
import render as R
from content_yt import YT

W, H = R.W, R.H
def bg_dots(base, dot):
    def f():
        im = Image.new("RGBA", (W, H), base + (255,)); d = ImageDraw.Draw(im)
        for x in range(30, W, 60):
            for y in range(30, H, 60): d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=dot)
        return im
    return f
def bg_grad(top, bot):
    def f():
        g = np.linspace(0, 1, H)[:, None, None]
        a = (np.array(top) * (1 - g) + np.array(bot) * g).astype(np.uint8).repeat(W, 1)
        return Image.fromarray(a, "RGB").convert("RGBA")
    return f
def bg_blob(base, blob):
    def f():
        im = Image.new("RGB", (W, H), base); d = ImageDraw.Draw(im)
        d.ellipse((W - 520, -260, W + 380, 640), fill=blob); d.ellipse((-420, H - 560, 420, H + 280), fill=blob)
        return im.filter(ImageFilter.GaussianBlur(60)).convert("RGBA")
    return f
def bg_frame(base, border):
    def f():
        im = Image.new("RGBA", (W, H), base + (255,)); d = ImageDraw.Draw(im)
        d.rectangle((24, 24, W - 25, H - 25), outline=border, width=14); return im
    return f
def bg_grain(base):
    def f():
        rng = np.random.default_rng(1); a = np.array(base, float)[None, None] + rng.normal(0, 4, (H, W, 1))
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8).repeat(1, 2) if False else np.clip(a.repeat(3, 2) if a.shape[2] == 1 else a, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    return f

THEMES = {
 "midnight": dict(BG=(11, 11, 14), INK=(245, 245, 247), GRAY=(150, 150, 160), LIGHT=(40, 40, 48), ACC=(190, 255, 60), ACC_FG=(11, 11, 14),
                  CARD=(28, 28, 34), CARD_FG=(245, 245, 247), CTA_BG=(190, 255, 60), CTA_FG=(11, 11, 14), CTA_SUB=(60, 80, 20),
                  trans="zoom", bgimg=bg_dots((11, 11, 14), (34, 34, 40, 255))),
 "mint": dict(BG=(226, 248, 238), INK=(6, 44, 32), GRAY=(70, 115, 98), LIGHT=(190, 230, 214), ACC=(0, 168, 107), ACC_FG=(255, 255, 255),
              CARD=(255, 255, 255), CARD_FG=(6, 44, 32), CTA_BG=(0, 140, 90), CTA_FG=(255, 255, 255), CTA_SUB=(190, 240, 215),
              trans="up", bgimg=bg_blob((226, 248, 238), (190, 238, 216))),
 "yellow": dict(BG=(255, 214, 0), INK=(12, 12, 12), GRAY=(95, 78, 0), LIGHT=(240, 190, 0), ACC=(220, 30, 60), ACC_FG=(255, 255, 255),
                CARD=(12, 12, 12), CARD_FG=(255, 214, 0), CTA_BG=(12, 12, 12), CTA_FG=(255, 214, 0), CTA_SUB=(180, 150, 0),
                GOLD=(12, 12, 12), trans="slide", upper=True, bgimg=bg_frame((255, 214, 0), (12, 12, 12, 255))),
 "navy": dict(BG=(10, 20, 46), INK=(240, 246, 255), GRAY=(140, 162, 205), LIGHT=(36, 54, 96), ACC=(0, 214, 255), ACC_FG=(6, 14, 34),
              CARD=(22, 36, 70), CARD_FG=(240, 246, 255), CTA_BG=(0, 214, 255), CTA_FG=(6, 14, 34), CTA_SUB=(0, 120, 150),
              trans="up", bgimg=bg_grad((8, 14, 36), (20, 42, 92))),
 "cream": dict(BG=(250, 243, 233), INK=(34, 22, 14), GRAY=(135, 112, 95), LIGHT=(234, 222, 206), ACC=(255, 94, 30), ACC_FG=(255, 255, 255),
               CARD=(255, 255, 255), CARD_FG=(34, 22, 14), CTA_BG=(255, 94, 30), CTA_FG=(255, 255, 255), CTA_SUB=(255, 200, 170),
               trans="zoom", bgimg=bg_grain((250, 243, 233))),
}

def apply(name):
    th = dict(THEMES[name]); th["name"] = name
    for k in ("BG", "INK", "GRAY", "LIGHT", "ACC", "ACC_FG", "CARD", "CARD_FG", "CTA_BG", "CTA_FG", "CTA_SUB", "GOLD"):
        if k in th: setattr(R, k, th[k])
    R.THEME = th

PLANS = {
 "yt1": dict(hook=("c1", 0.0, 1.0), product=("c6", 27.0, 1.0)),
 "yt2": dict(hook=("c5", 0.3, 1.0), product=("c4", 0.0, 0.6)),
 "yt3": dict(hook=("c6", 1.0, 1.3), product=("c1", 3.0, 1.0)),
 "yt4": dict(hook=("c5", 8.0, 1.0), product=("c6", 15.5, 1.0)),
 "yt5": dict(hook=("c1", 5.5, 1.0), product=("c6", 20.0, 1.0)),
}

def build(v):
    apply(v["theme"]); v = dict(v)
    import footage
    fo = footage.Footage(PLANS[v["slug"][:3]])
    R.THEME["base_fn"] = fo.base; R.THEME["scene_fn"] = fo.scene
    R.THEME["cap_hide"] = lambda sc, t: sc["type"] == "cta" and t > 1.8; v["out"] = "/home/user/airpods_videos/youtube_shorts_v2"
    os.makedirs(v["out"], exist_ok=True)
    vf = f"/home/user/ovozlar_yt/{v['slug'][:3]}.mp3"
    if os.path.exists(vf): v["voice"] = vf
    R.build(v)

if __name__ == "__main__":
    sel = sys.argv[1:]
    vids = [v for v in YT if not sel or any(v["slug"].startswith(s) for s in sel)]
    from multiprocessing import Pool
    with Pool(min(4, len(vids))) as p: p.map(build, vids)
