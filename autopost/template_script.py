"""Penulis naskah gratis tanpa AI: merangkai template dari data produk.

Hasilnya mengikuti format yang sama dengan script.write_script(), jadi bisa langsung dirender.
"""

from __future__ import annotations

import random
import re

HOOKS = [
    ("Masih bingung cari {short} yang bagus?", "Cari {short} yang bagus?"),
    ("Jujur, aku nyesel nggak beli {short} ini dari dulu.", "Nyesel nggak beli dari dulu"),
    ("Stop scroll dulu! Ini {short} yang lagi rame dibahas.", "Stop scroll dulu!"),
    ("Buat kamu {audience}, ini wajib lihat.", "Wajib lihat ini!"),
    ("Kalau kamu sering kesal soal ini, coba deh {short} ini.", "Coba deh yang satu ini"),
]
CTAS = [
    ("Link-nya aku taruh di caption ya, cek sebelum kehabisan!", "Cek link di caption"),
    ("Mau juga? Klik link di caption, sekalian cek promonya.", "Klik link di caption"),
    ("Langsung cek link di caption, siapa tahu lagi ada diskon.", "Link ada di caption"),
]
CAPTIONS = [
    "Nemu {short} yang worth it banget {emoji}",
    "Racun hari ini: {short} {emoji}",
    "Yang lagi cari {short}, ini rekomendasiku {emoji}",
]
EMOJIS = ["✨", "🔥", "😍", "👌", "💯"]


def _short_name(name: str) -> str:
    """'Contoh: Botol Minum Tumbler 1 Liter' -> 'botol minum tumbler'."""
    name = re.sub(r"^[^:]*:\s*", "", name)
    words = [w for w in re.split(r"\s+", name) if not re.search(r"\d", w)]
    return " ".join(words[:3]).lower() or "produk"


def _screen_text(point: str, limit: int = 6) -> str:
    words = point.split()
    return " ".join(words[:limit]).rstrip(",.")


def write_script(product: dict, seed: int | None = None) -> dict:
    rnd = random.Random(seed)
    short = _short_name(product["name"])
    audience = product.get("audience") or "yang lagi butuh"
    points = list(product.get("selling_points", []))[:3] or ["kualitasnya bagus", "harganya ramah di kantong"]

    hook_say, hook_show = rnd.choice(HOOKS)
    scenes = [{"narration": hook_say.format(short=short, audience=audience),
               "on_screen_text": hook_show.format(short=short)}]

    intros = ["Pertama,", "Terus,", "Yang paling aku suka,"]
    for intro, point in zip(intros, points):
        scenes.append({"narration": f"{intro} {point}.", "on_screen_text": _screen_text(point).capitalize()})

    if product.get("price"):
        scenes.append({"narration": f"Harganya cuma {product['price']}, menurutku worth it banget.",
                       "on_screen_text": f"Cuma {product['price']}"})

    cta_say, cta_show = rnd.choice(CTAS)
    scenes.append({"narration": cta_say, "on_screen_text": cta_show})

    tags = ["racunshopee", "shopeeaffiliate", "rekomendasi"]
    tags.append(re.sub(r"[^a-z0-9]", "", short.replace(" ", "")) or "produk")
    return {
        "title": hook_show.format(short=short),
        "scenes": scenes,
        "caption": rnd.choice(CAPTIONS).format(short=short, emoji=rnd.choice(EMOJIS)),
        "hashtags": tags,
    }
