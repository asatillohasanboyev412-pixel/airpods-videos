from content import CTA_VOICE

# Har bir video o'z dizayn mavzusiga ega (render_yt.THEMES)
YT = [
 dict(slug="yt1_3_xato", tag="XATO", seed=21, theme="midnight",
  hook=("Quloqchiningizni shu 3 xato buzadi", "Ko'pchilik har kuni qiladi",
        "To'xtang! Siz ham har kuni shu uchta xatoni qilyapsizmi? Quloqchiningizni aynan shular buzadi."),
  tips=[
   ("case", "Qutisiz cho'ntakda", "Chang kiradi, tushib sinadi",
    "Birinchi xato. Quloqchinni qutisiz cho'ntakda olib yurish. Chang kiradi, tushib sinadi."),
   ("drop", "Dushda taqish", "IPX4 — sachrashga, suvga emas",
    "Ikkinchi xato. Dushda yoki hovuzda taqish. Terga chidamli degani, suvga chidamli degani emas."),
   ("battery", "Faqat bitta tomoni", "Batareyalar notekis eskiradi",
    "Uchinchi xato. Doim faqat bitta quloqchinni ishlatish. Uning batareyasi ikkinchisidan tezroq eskiradi."),
  ],
  features=["Aktiv ANC", "IPX4 — terga chidamli", "30 soatgacha", "1 yil kafolat"],
  product_voice="Pods Pro 3 ANC esa terga chidamli, quti bilan o'ttiz soatgacha ishlaydi va bir yil kafolatga ega."),

 dict(slug="yt2_yoqotdingizmi", tag="LIFEHAK", seed=22, theme="mint",
  hook=("Quloqchinni yo'qotdingizmi?", "Topishning 3 ta oson usuli",
        "Quloqchinni yo'qotib qo'ydingizmi? Xavotir olmang. Uni topishning uchta oson usuli bor."),
  tips=[
   ("bluetooth", "Bluetooth'ga qarang", "Ulansa — u yaqin atrofda",
    "Birinchi. Telefonda Bluetooth'ni oching. Agar quloqchin ulansa, demak u yaqin atrofda."),
   ("bass", "Musiqani baland qo'ying", "Jim turib tovushga quloq soling",
    "Ikkinchi. Ulangan zahoti musiqani eng baland ovozda qo'ying va jim turib tovushga quloq soling."),
   ("transparent", "Signal kuchini kuzating", "Bluetooth skaner ilovasi yordam beradi",
    "Uchinchi. Bluetooth skaner ilovasini o'rnating. Quloqchinga yaqinlashganingiz sari signal kuchayadi."),
  ],
  features=["Tez ulanish", "Aktiv ANC", "30 soatgacha", "1 yil kafolat"],
  product_voice="Pods Pro 3 ANC tez ulanadi va qutisi bilan o'ttiz soatgacha ishlaydi."),

 dict(slug="yt3_qimmat_yaxshimi", tag="BOZOR TAHLILI", seed=23, theme="yellow",
  hook=("Qimmat quloqchin = yaxshi?", "Bozordagi haqiqat",
        "Qimmat quloqchin har doim yaxshimi? Bozorni o'rganib chiqdik. Mana haqiqat."),
  tips=[
   ("stars", "Narxda brend ham bor", "Siz logotip uchun ham to'laysiz",
    "Birinchi. Narxning katta qismi brend uchun. Siz ko'pincha logotip uchun ham to'laysiz."),
   ("list", "Muhimi — 3 narsa", "ANC · Batareya · Kafolat",
    "Ikkinchi. Kundalik hayotda muhimi uch narsa: shovqinni bostirish, batareya va kafolat."),
   ("shield", "Kafolatsiz olmang", "Kafolat — sotuvchining ishonchi",
    "Uchinchi. Arzon bo'lsa ham, kafolatsiz olmang. Kafolat, bu sotuvchining o'z mahsulotiga ishonchi."),
  ],
  features=["Aktiv ANC", "Ichki + tashqi mikrofon", "30 soatgacha", "1 yil kafolat"],
  product_voice="Pods Pro 3 ANC aynan shu narsalarni beradi: shovqinni bostirish, uzoq batareya va bir yil kafolat."),

 dict(slug="yt4_2x_batareya", tag="SIR", seed=24, theme="navy",
  hook=("Batareyani 2 barobar uzaytiring", "Ko'pchilik bilmaydigan hiyla",
        "Quloqchin batareyasini ikki barobar uzaytirish mumkin. Ko'pchilik bu hiylani bilmaydi."),
  tips=[
   ("case", "Bittasini qutiga soling", "Qo'ng'iroqqa bittasi yetadi",
    "Birinchi. Qo'ng'iroq yoki podkast tinglaganda faqat bitta quloqchinni taqing. Ikkinchisi qutida zaryadlanib turadi."),
   ("charge", "Navbat bilan almashtiring", "Biri ishlaydi, biri zaryadlanadi",
    "Ikkinchi. Biri tugaganda, almashtiring. Shunday qilib, deyarli to'xtovsiz ishlatasiz."),
   ("ancoff", "Jim joyda ANC'ni o'chiring", "Shovqin yo'q joyda — quvvatni tejang",
    "Uchinchi. Jim joyda shovqinni bostirishni o'chiring. Bu ham batareyani tejaydi."),
  ],
  features=["6 soat — quloqchin", "30 soat — quti bilan", "Qi simsiz zaryad", "Aktiv ANC"],
  product_voice="Pods Pro 3 ANC quloqchinda olti soat, qutisi bilan o'ttiz soatgacha ishlaydi."),

 dict(slug="yt5_ovoz_past", tag="YECHIM", seed=25, theme="cream",
  hook=("Quloqchinda ovoz pastmi?", "4 ta sabab va yechim",
        "Quloqchinda ovoz past chiqyaptimi? Sababi siz o'ylagan narsa emas."),
  tips=[
   ("brush", "Setka kirlangan", "Quruq cho'tka bilan tozalang",
    "Birinchi. Dinamik setkasi kirlangan. Uni quruq, yumshoq cho'tka bilan tozalang."),
   ("tips", "Uchlik mos emas", "Zich o'tirmasa — ovoz qochadi",
    "Ikkinchi. Uchlik o'lchami mos emas. Zich o'tirmasa, ovoz va bass qochib ketadi."),
   ("volume", "iPhone'da cheklov", "Sozlamalar → Tovushlar → Quloqchin xavfsizligi",
    "Uchinchi. iPhone'da quloqchin xavfsizligi sozlamasi ovozni cheklab qo'ygan bo'lishi mumkin. Uni tekshiring."),
   ("bluetooth", "Android'da absolyut ovoz", "Dasturchi sozlamalarida o'chirib ko'ring",
    "To'rtinchi. Android'da dasturchi sozlamalaridan absolyut ovoz balandligini o'chirib ko'ring."),
  ],
  features=["Tiniq stereo ovoz", "Chuqur tovush", "Aktiv ANC", "3 o'lchamdagi uchlik"],
  product_voice="Pods Pro 3 ANC tiniq stereo ovoz va uch o'lchamdagi uchliklar bilan keladi."),
]

def parts(v):
    return [v["hook"][2]] + [t[3] for t in v["tips"]] + [v["product_voice"], CTA_VOICE]

# ElevenLabs uchun: qismlar orasida [pause], hook hayajonli
def eleven_prompt(v):
    p = parts(v)
    return "[excited] " + p[0] + " [pause] " + " [pause] ".join(p[1:])

if __name__ == "__main__":
    for v in YT:
        print(v["slug"], len(eleven_prompt(v)))
        print(eleven_prompt(v)); print()
