import asyncio, base64, hashlib, hmac, json, logging, os, time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from urllib.parse import parse_qsl

import edge_tts, httpx, uvicorn
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (BufferedInputFile, CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, MenuButtonWebApp, Message, WebAppInfo)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from dialects import STYLES, convert_rules, normalize, public_styles

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sheva")

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
WEBAPP_URL = os.getenv("WEBAPP_URL") or (
    f"https://{os.environ['RAILWAY_PUBLIC_DOMAIN']}" if os.getenv("RAILWAY_PUBLIC_DOMAIN") else "")
MAX_CHARS = 1500
VOICES = {"f": "uz-UZ-MadinaNeural", "m": "uz-UZ-SardorNeural"}

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
http: httpx.AsyncClient
LAST: dict[int, str] = {}
VOICE_PREF: dict[int, str] = {}
HITS: dict[int, deque] = defaultdict(deque)


# ---------------- konvertatsiya + ovoz ----------------
async def gemini_convert(text: str, key: str) -> str | None:
    st = STYLES[key]
    prompt = (
        "Quyidagi o'zbekcha matnni berilgan uslubga o'tkaz. Ma'nosi va uzunligini saqla, "
        "faqat lotin yozuvida, faqat natija matnini yoz (izoh, tirnoq, sarlavha yo'q). "
        "So'zlarni ovoz chiqarib o'qishga mos yoz.\n"
        f"Uslub: {st['name']}. Xususiyatlari: {st['desc']}\n\nMatn:\n{text}"
    )
    r = await http.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        params={"key": GEMINI_KEY},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 0.4}})
    r.raise_for_status()
    out = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    return out[: MAX_CHARS * 2] or None


async def convert(text: str, key: str) -> str:
    text = normalize(text)[:MAX_CHARS]
    if GEMINI_KEY:
        try:
            out = await gemini_convert(text, key)
            if out:
                return out
        except Exception as e:
            log.warning("Gemini xato, qoidalarga o'tildi: %s", e)
    return convert_rules(text, key)


async def synth(text: str, voice: str, rate: str, pitch: str) -> bytes:
    buf = bytearray()
    async for ch in edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).stream():
        if ch["type"] == "audio":
            buf += ch["data"]
    if not buf:
        raise RuntimeError("TTS bo'sh javob qaytardi")
    return bytes(buf)


async def make_audio(text: str, key: str, voice_code: str):
    st = STYLES[key]
    converted = await convert(text, key)
    audio = await synth(converted, VOICES[voice_code], st["rate"], st["pitch"])
    return converted, audio


# ---------------- Telegram bot ----------------
def style_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for k, v in STYLES.items():
        kb.button(text=("📜 " if v["kind"] == "tarixiy" else "📍 ") + v["name"], callback_data=f"st:{k}")
    kb.adjust(2)
    return kb.as_markup()


@dp.message(CommandStart())
async def start(m: Message):
    rows = []
    if WEBAPP_URL:
        rows.append([InlineKeyboardButton(text="🎧 Mini ilovani ochish", web_app=WebAppInfo(url=WEBAPP_URL))])
    await m.answer(
        "Assalomu alaykum! Menga matn yuboring, so'ng viloyat shevasi yoki tarixiy uslubni "
        "(Navoiy, Ulug'bek, Qodiriy) tanlang — men uni shu ohangda ovozga aylantiraman.\n\n"
        "/ovoz — ayol/erkak ovozini almashtirish",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows) if rows else None)


@dp.message(Command("ovoz"))
async def toggle_voice(m: Message):
    cur = VOICE_PREF.get(m.from_user.id, "f")
    new = "m" if cur == "f" else "f"
    VOICE_PREF[m.from_user.id] = new
    await m.answer("Ovoz: " + ("erkak (Sardor)" if new == "m" else "ayol (Madina)"))


@dp.message(F.text & ~F.text.startswith("/"))
async def on_text(m: Message):
    LAST[m.from_user.id] = m.text[:MAX_CHARS]
    note = f"\n(Matn {MAX_CHARS} belgigacha qisqartirildi.)" if len(m.text) > MAX_CHARS else ""
    await m.answer("Qaysi sheva yoki uslubda o'qilsin?" + note, reply_markup=style_keyboard())


@dp.callback_query(F.data.startswith("st:"))
async def on_style(cb: CallbackQuery):
    key, uid = cb.data[3:], cb.from_user.id
    text = LAST.get(uid)
    if key not in STYLES or not text:
        await cb.answer("Avval matn yuboring", show_alert=True)
        return
    if not allow(uid):
        await cb.answer("Juda tez. Bir oz kuting.", show_alert=True)
        return
    await cb.answer("Ovoz tayyorlanmoqda…")
    try:
        converted, audio = await make_audio(text, key, VOICE_PREF.get(uid, "f"))
    except Exception:
        log.exception("audio xato")
        await cb.message.answer("Ovoz yaratib bo'lmadi. Birozdan so'ng qayta urinib ko'ring.")
        return
    await cb.message.answer_audio(BufferedInputFile(audio, f"{key}.mp3"),
                                  title=STYLES[key]["name"], caption=converted[:1000])


# ---------------- Web API (mini app) ----------------
def allow(uid: int, limit: int = 12, window: int = 60) -> bool:
    now, q = time.time(), HITS[uid]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


def verify_init_data(init_data: str):
    try:
        data = dict(parse_qsl(init_data, strict_parsing=True))
        got = data.pop("hash")
        check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, got) or time.time() - int(data["auth_date"]) > 86400:
            return None
        return json.loads(data["user"])["id"]
    except Exception:
        return None


class TTSReq(BaseModel):
    text: str
    style: str
    voice: str = "f"
    initData: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http
    http = httpx.AsyncClient(timeout=30)
    if WEBAPP_URL:
        try:
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Ovoz", web_app=WebAppInfo(url=WEBAPP_URL)))
        except Exception as e:
            log.warning("menu button: %s", e)
    task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    yield
    task.cancel()
    await bot.session.close()
    await http.aclose()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/styles")
async def styles():
    return public_styles()


@app.post("/api/tts")
async def tts(req: TTSReq):
    uid = verify_init_data(req.initData)
    if uid is None:
        raise HTTPException(401, "Telegram ichida oching")
    if req.style not in STYLES or req.voice not in VOICES or not req.text.strip():
        raise HTTPException(400, "Noto'g'ri so'rov")
    if not allow(uid):
        raise HTTPException(429, "Juda tez, bir oz kuting")
    try:
        converted, audio = await make_audio(req.text, req.style, req.voice)
    except Exception:
        log.exception("tts xato")
        raise HTTPException(502, "Ovoz yaratib bo'lmadi")
    return {"text": converted, "audio": base64.b64encode(audio).decode()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
