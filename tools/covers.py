import render as R
from render import *
COV = {
 "01": ("Batareya tez tugayaptimi?", "3 ta lifehak", "battery"),
 "02": ("Quloqdan tushib ketyaptimi?", "Muammo uchlikda", "tips"),
 "03": ("60 / 60 qoidasi", "Quloqni asrang", "volume"),
 "04": ("Suvda yuvmang!", "To'g'ri tozalash", "drop"),
 "05": ("ANC bilan ko'chada?", "Transparent rejim", "transparent"),
 "06": ("Sizni eshitishmayaptimi?", "3 ta yechim", "micholes"),
 "07": ("Olishdan oldin ko'ring!", "4 ta tekshiruv", "shield"),
 "08": ("Yangi yilga sovg'a", "Hamma yoqtiradi", "people"),
 "09": ("Ulanmayaptimi?", "4 qadamda hal qiling", "bluetooth"),
 "10": ("ANC qanday ishlaydi?", "Sehr emas — fizika", "inverse"),
}
TAGS = {v["slug"][:2]: v["tag"] for v in R.VIDEOS}
sprites()
for num, (title, sub, icon) in COV.items():
    im = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(im)
    # 3:4 xavfsiz zona: y 240..1680
    put(im, pill(disp(TAGS[num]), "xbold", 40, WHITE, ACC + (255,), track=4), W / 2, 330)
    words = disp(title).split(); fs = 128
    while max(font("black", fs).getlength(w_) for w_ in words) > 960: fs -= 4
    f = font("black", fs)
    lines = wrap(disp(title), f, 960); y = 420; wi = 0
    for line in lines:
        ws = line.split(); widths = [f.getlength(w_) for w_ in ws]; sp = f.getlength(" ")
        x = W / 2 - (sum(widths) + sp * (len(ws) - 1)) / 2
        for w_, ww in zip(ws, widths):
            col = ACC if (wi == len(words) - 1 and len(words) > 1) else INK
            put(im, text_img(w_, "black", fs, col, maxw=2000), x + ww / 2, y + 70)
            x += ww + sp; wi += 1
        y += int(fs * 1.11)
    put(im, text_img(disp(sub), "med", 56, GRAY), W / 2, y + 60)
    ic = icon_layer(icon, {"battery": 2.6, "inverse": 2.0}.get(icon, 3.2))
    top = y + 130
    put(im, ic, W / 2, top + 300, 1, .95)
    put(im, pill("Airpods market · Uzum Market", "semi", 36, INK, WHITE + (255,)), W / 2, 1590)
    d.rounded_rectangle((60, 96, W - 60, 104), radius=4, fill=LIGHT)
    im.alpha_composite(text_img("AIRPODS MARKET", "semi", 28, GRAY, maxw=2000, track=6), (60, 128))
    im.convert("RGB").save(f"/home/user/airpods_videos/obloshkalar/{num}_obloshka.jpg", quality=95)
print("ok")
