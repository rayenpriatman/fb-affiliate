"""Suara narasi AI (Microsoft Edge TTS, gratis, tanpa API key)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

DEFAULT_VOICE = "id-ID-GadisNeural"  # alternatif: id-ID-ArdiNeural (pria)


async def _synthesize(text: str, out: Path, voice: str, rate: str) -> None:
    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def synthesize(text: str, out: Path, voice: str = DEFAULT_VOICE, rate: str = "+8%") -> Path:
    asyncio.run(_synthesize(text, out, voice, rate))
    return out
