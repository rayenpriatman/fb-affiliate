"""Tulis naskah video pendek (hook, adegan, caption) dengan Claude."""

from __future__ import annotations

import json

import anthropic

MODEL = "claude-opus-5-5"

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "narration": {"type": "string"},
                    "on_screen_text": {"type": "string"},
                },
                "required": ["narration", "on_screen_text"],
                "additionalProperties": False,
            },
        },
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "scenes", "caption", "hashtags"],
    "additionalProperties": False,
}

SYSTEM = """Kamu copywriter video pendek (Reels/Facebook) untuk afiliasi Shopee di Indonesia.
Tulis dalam Bahasa Indonesia santai, jujur, tanpa klaim berlebihan atau janji yang tidak bisa dibuktikan.

Aturan naskah:
- 4 sampai 6 adegan. Total narasi dibaca sekitar 20-40 detik.
- Adegan pertama adalah hook kuat (pertanyaan atau masalah yang relate).
- Adegan terakhir ajakan bertindak: cek link di caption/komentar.
- on_screen_text maksimal 6 kata per adegan, tanpa emoji.
- caption 1-3 kalimat, boleh emoji, JANGAN tulis link (link ditambahkan otomatis).
- hashtags 3-6 item, tanpa tanda #."""


def write_script(product: dict) -> dict:
    """Kembalikan dict sesuai SCRIPT_SCHEMA untuk satu produk."""
    client = anthropic.Anthropic()
    brief = {
        "nama_produk": product["name"],
        "harga": product.get("price", ""),
        "poin_jual": product.get("selling_points", []),
        "target_pembeli": product.get("audience", ""),
        "gaya": product.get("tone", "santai dan meyakinkan"),
    }
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": SCRIPT_SCHEMA},
        },
        messages=[{
            "role": "user",
            "content": "Buat naskah video untuk produk ini:\n"
            + json.dumps(brief, ensure_ascii=False, indent=2),
        }],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude menolak membuat naskah: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Naskah terpotong (max_tokens).")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
