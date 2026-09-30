# Sheva ovozi — Telegram bot + Mini App

Matn yuborasiz → viloyat shevasi (12 viloyat) yoki tarixiy uslub (Navoiy, Ulug'bek, Qodiriy) tanlaysiz → audio olasiz.

**Bepul qismlar:** ovoz — `edge-tts` (Microsoft `uz-UZ-MadinaNeural` / `SardorNeural`, kalitsiz); sheva matni — offline qoidalar, ixtiyoriy Gemini bepul API.

## Muhim cheklov
Hozircha dunyoda o'zbek shevalari uchun alohida TTS ovozi yo'q, faqat standart o'zbek (Madina, Sardor). Bot matnni shevaga *yozma shaklda* o'giradi (masalan Xorazm: `borayapman → borovman`, `yo'q → yo'x`), so'ng standart ovoz o'qiydi. Talaffuz aksenti to'liq sheva bo'lmaydi. Qoidalar taxminiy — `dialects.py` ni sheva egalari bilan yaxshilang. `GEMINI_API_KEY` qo'shsangiz natija ancha tabiiy chiqadi.

## Ishga tushirish
1. @BotFather → `/newbot` → token oling.
2. Repo'ni GitHub'ga push qiling.
3. Railway → New Project → Deploy from GitHub repo.
4. Variables: `BOT_TOKEN` (majburiy), `GEMINI_API_KEY` (ixtiyoriy).
5. Settings → Networking → **Generate Domain** (mini app uchun HTTPS kerak; `WEBAPP_URL` avtomatik olinadi). Domain yaratgach qayta deploy qiling.
6. Botga `/start` yuboring.

Lokal: `pip install -r requirements.txt && BOT_TOKEN=... python main.py`

Eslatma: Railway'da doimiy bepul tarif yo'q — sinov krediti, keyin taxminan $5/oy.
