"""O'zbek shevalari (12 viloyat) va tarixiy uslublar (Navoiy, Ulug'bek, Qodiriy).

Ikki daraja:
  1) convert_rules  - offline, qoidalarga asoslangan (har doim ishlaydi, taxminiy)
  2) main.py dagi Gemini - ixtiyoriy, bepul API kalit bo'lsa ancha tabiiy natija beradi
`desc` maydoni Gemini promptiga beriladi.
"""
import re

_APOS = str.maketrans({"ʻ": "'", "’": "'", "ʼ": "'", "`": "'", "‘": "'"})


def normalize(text: str) -> str:
    return text.translate(_APOS).strip()


def _compile(rules):
    out = []
    for pat, rep in rules:
        rx = re.compile(pat, re.IGNORECASE)

        def fn(m, rep=rep):
            new = m.expand(rep)
            s = m.group(0)
            if len(s) > 1 and s.isupper():
                return new.upper()
            if s[:1].isupper():
                return new[:1].upper() + new[1:]
            return new

        out.append((rx, fn))
    return out


# ---- umumiy qoidalar bloklari -------------------------------------------
_TOSH = [
    (r"\bbola", "bala"),
    (r"\bkel(?:a)?yapti\b", "kevotti"),
    (r"\b(\w+?)a?yapti\b", r"\1otti"),
    (r"\b(\w+?)a?yapman\b", r"\1otman"),
    (r"\bshunday", "shunaqa"),
    (r"\bqanday", "qanaqa"),
    (r"\bonam\b", "oyim"),
]
_FARG = [
    (r"\bosh(?=(?:ni|ga|dan|ing|im)?\b)", "ash"),
    (r"\b(\w+?)a?yapti\b", r"\1votti"),
    (r"\b(\w+?)a?yapman\b", r"\1votman"),
    (r"\b(\w+san)mi\b", r"\1mi yo'q"),
    (r"\bshunday", "shunaqa"),
    (r"\bqanday", "qanaqa"),
]
_SAMBUX = [
    (r"\bbola", "bacha"),
    (r"\bshunday", "shundoq"),
    (r"\bqanday", "qandoq"),
]
_JLOV = [
    (r"\by(?=[aeoiu'])", "j"),
    (r"\bsigir", "siyir"),
    (r"\b(\w+?)a?yapti\b", r"\1yotti"),
    (r"\b(\w+?)a?yapman\b", r"\1yotman"),
    (r"\bshunday", "shundoq"),
    (r"\bqanday", "qandoq"),
]

STYLES = {
    # ---------------- 12 viloyat ----------------
    "toshkent": dict(
        name="Toshkent", kind="viloyat", hint="bala, kevotti, -la", rate="+0%", pitch="+0Hz",
        desc="Toshkent shevasi: bola->bala, kelayapti->kevotti, ko'plik -lar o'rniga -la, shunaqa, qanaqa, oyim.",
        rules=_TOSH + [(r"\b(\w{3,})lar\b", r"\1la")]),
    "sirdaryo": dict(
        name="Sirdaryo", kind="viloyat", hint="Qurama shevasi: bala, kevotti", rate="+0%", pitch="+0Hz",
        desc="Sirdaryo (Qurama) shevasi, Toshkent shevasiga yaqin: bola->bala, kelyapti->kevotti, shunaqa.",
        rules=_TOSH),
    "toshkent_v": dict(
        name="Toshkent viloyati", kind="viloyat", hint="Qurama: bala, borotti", rate="+0%", pitch="+0Hz",
        desc="Toshkent viloyati qishloq (Qurama) shevasi: bola->bala, boryapti->borotti, shunaqa, qanaqa.",
        rules=_TOSH),
    "fargona": dict(
        name="Farg'ona", kind="viloyat", hint="ash, kelvotti, borasanmi yo'q", rate="+0%", pitch="+0Hz",
        desc="Farg'ona shevasi: osh->ash, boryapti->borvotti, Borasanmi? -> Borasanmi yo'q?, shunaqa, qanaqa.",
        rules=_FARG),
    "andijon": dict(
        name="Andijon", kind="viloyat", hint="ash, ketvotti, aydi", rate="+2%", pitch="+0Hz",
        desc="Andijon shevasi (Farg'ona vodiysi): osh->ash, ketyapti->ketvotti, aytdi->aydi, shunaqa, qanaqa.",
        rules=_FARG + [(r"\baytdi\b", "aydi")]),
    "namangan": dict(
        name="Namangan", kind="viloyat", hint="ash, kelvotti", rate="+0%", pitch="+0Hz",
        desc="Namangan shevasi (Farg'ona vodiysi): osh->ash, kelyapti->kelvotti, Borasanmi yo'q?, shunaqa.",
        rules=_FARG),
    "xorazm": dict(
        name="Xorazm", kind="viloyat", hint="yo'x, borovman, bovotti", rate="+4%", pitch="+0Hz",
        desc="Xorazm shevasi: yo'q->yo'x, borayapman->borovman, kelayapti->kevotti, bo'layapti->bovotti, "
             "so'z oxiridagi q->x, ko'plik -lar->-la, Borasanmi?->Borasan-a?",
        rules=[
            (r"\bbo'la?yapti\b", "bovotti"),
            (r"\bkel(?:a)?yapti\b", "kevotti"),
            (r"\b(\w+?)a?yapman\b", r"\1ovman"),
            (r"\b(\w+?)a?yapsan\b", r"\1ovsan"),
            (r"\b(\w+?)a?yapti\b", r"\1ovotti"),
            (r"\b(\w+san)mi\b", r"\1-a"),
            (r"\b(\w{3,})lar\b", r"\1la"),
            (r"q\b", "x"),
        ]),
    "samarqand": dict(
        name="Samarqand", kind="viloyat", hint="bacha, shundoq (tojik ta'siri)", rate="+0%", pitch="+0Hz",
        desc="Samarqand-Buxoro shevasi (tojik tili ta'siri, unlilar buzilgan): bola->bacha, shundoq, qandoq, kelyapman shakli saqlanadi.",
        rules=_SAMBUX),
    "buxoro": dict(
        name="Buxoro", kind="viloyat", hint="bacha, darkor, shundoq", rate="-3%", pitch="+0Hz",
        desc="Buxoro shevasi (tojik tili ta'siri): bola->bacha, kerak->darkor, shundoq, qandoq.",
        rules=_SAMBUX + [(r"\bkerak\b", "darkor")]),
    "navoiy_v": dict(
        name="Navoiy viloyati", kind="viloyat", hint="bacha, shundoq", rate="+0%", pitch="+0Hz",
        desc="Navoiy viloyati shevasi (Samarqand-Buxoro guruhi): bola->bacha, kelyapti (kevotti emas), shundoq, qandoq.",
        rules=_SAMBUX),
    "jizzax": dict(
        name="Jizzax", kind="viloyat", hint="jaxshi, jo'l, boryotti", rate="+2%", pitch="+0Hz",
        desc="Jizzax shevasi (j-lovchi): so'z boshidagi y->j (yaxshi->jaxshi, yo'l->jo'l), boryapti->boryotti.",
        rules=_JLOV),
    "qashqadaryo": dict(
        name="Qashqadaryo", kind="viloyat", hint="qipchoq: boryotti, shundoq", rate="+2%", pitch="-2Hz",
        desc="Qashqadaryo qipchoq/qarluq shevalari: q va g' tovushlari saqlanadi, boryapti->boryotti, shundoq, qandoq.",
        rules=[r for r in _JLOV if not r[0].startswith(r"\by")]),
    "surxondaryo": dict(
        name="Surxondaryo", kind="viloyat", hint="j-lovchi: jaxshi, jigit, siyir", rate="+3%", pitch="-2Hz",
        desc="Surxondaryo (j-lovchi, qipchoq): y->j (yigit->jigit, yaxshi->jaxshi), sigir->siyir, boryapti->boryotti.",
        rules=_JLOV),
    # ---------------- tarixiy uslublar ----------------
    "navoiy": dict(
        name="Alisher Navoiy", kind="tarixiy", hint="chig'atoy: ul, andoq, ne, ko'ngul", rate="-15%", pitch="-4Hz",
        desc="Alisher Navoiy davri eski o'zbek (chig'atoy) tili: ul, manga, sanga, anga, andoq, mundoq, ne, nechun, "
             "erdi, ersa, ko'ngul, ishq, yor, kishi, jahon, nihoyat, zero, ammo, gar.",
        rules=[
            (r"\bshuning uchun\b", "shul sabab"),
            (r"\bmenga\b", "manga"), (r"\bsenga\b", "sanga"), (r"\bunga\b", "anga"),
            (r"\bshunday", "andoq"), (r"\bbunday", "mundoq"),
            (r"\bu\b", "ul"), (r"\bedi\b", "erdi"),
            (r"\bnima\b", "ne"), (r"\bnega\b", "nechun"),
            (r"\bjuda\b", "nihoyat"), (r"\bsevgi", "ishq"),
            (r"\bdo'st", "yor"), (r"\bodam", "kishi"), (r"\bdunyo", "jahon"),
            (r"\byurak", "ko'ngul"), (r"\bko'ngil", "ko'ngul"),
            (r"\bchunki\b", "zero"), (r"\blekin\b", "ammo"), (r"\bagar\b", "gar"),
        ]),
    "ulugbek": dict(
        name="Mirzo Ulug'bek", kind="tarixiy", hint="Temuriylar davri ilmiy uslub", rate="-12%", pitch="-3Hz",
        desc="Mirzo Ulug'bek davri (XV asr Temuriylar) ilmiy-adabiy uslub: fors-arab ilmiy atamalar "
             "(kavkab, falak, rasad, zij, miqyos, olam), ul, andoq, ne, erdi, -dur.",
        rules=[
            (r"\byulduz", "kavkab"), (r"\bosmon", "falak"),
            (r"\bkuzatish", "rasad"), (r"\bjadval", "zij"),
            (r"\bo'lchov", "miqyos"), (r"\bdunyo", "olam"),
            (r"\bodam", "kishi"), (r"\bshunday", "andoq"),
            (r"\bu\b", "ul"), (r"\bedi\b", "erdi"), (r"\bnima\b", "ne"),
            (r"\bjuda\b", "g'oyat"), (r"(?<=\w)dir\b", "dur"),
        ]),
    "qodiriy": dict(
        name="Abdulla Qodiriy", kind="tarixiy", hint="jadid uslubi: g'oyat, biroq, shundoq", rate="-8%", pitch="+0Hz",
        desc="Abdulla Qodiriy ('O'tkan kunlar', 'Mehrobdan chayon') jadid davri nasri: g'oyat, biroq, shundoq, mundoq, "
             "endi, rost, kayf, so'ng, uzun sharqona jumlalar, 'edi/ekan' ko'p ishlatiladi.",
        rules=[
            (r"\bjuda\b", "g'oyat"), (r"\blekin\b", "biroq"),
            (r"\bshunday", "shundoq"), (r"\bbunday", "bundoq"), (r"\bunday", "undoq"),
            (r"\bhozir\b", "endi"), (r"\bhaqiqat", "rost"),
            (r"\bkayfiyat", "kayf"), (r"\bkeyin\b", "so'ng"), (r"\bkatta\b", "ulug'"),
        ]),
}

_COMPILED = {k: _compile(v["rules"]) for k, v in STYLES.items()}


def convert_rules(text: str, key: str) -> str:
    text = normalize(text)
    for rx, fn in _COMPILED[key]:
        text = rx.sub(fn, text)
    return text


def public_styles():
    return [dict(key=k, name=v["name"], kind=v["kind"], hint=v["hint"]) for k, v in STYLES.items()]
