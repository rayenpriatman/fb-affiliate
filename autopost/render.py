"""Render video vertikal 9:16 dari foto produk + teks + narasi, pakai Pillow & ffmpeg."""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
PALETTES = [((32, 36, 31), (62, 110, 82)), ((173, 122, 38), (32, 36, 31)), ((162, 58, 44), (32, 36, 31))]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def load_images(sources: list[str], workdir: Path) -> list[Image.Image]:
    """Ambil foto produk dari URL atau path lokal."""
    images = []
    for i, src in enumerate(sources):
        if src.startswith(("http://", "https://")):
            resp = requests.get(src, timeout=60)
            resp.raise_for_status()
            path = workdir / f"src_{i}"
            path.write_bytes(resp.content)
        else:
            path = Path(src)
        images.append(Image.open(path).convert("RGB"))
    return images


def _gradient(index: int) -> Image.Image:
    top, bottom = PALETTES[index % len(PALETTES)]
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def _background(photo: Image.Image | None, index: int) -> Image.Image:
    """Foto produk utuh di tengah, dengan versi blur-nya sebagai latar 9:16."""
    if photo is None:
        return _gradient(index)
    cover = photo.copy()
    scale = max(W / cover.width, H / cover.height)
    cover = cover.resize((int(cover.width * scale) + 1, int(cover.height * scale) + 1))
    left, top = (cover.width - W) // 2, (cover.height - H) // 2
    bg = cover.crop((left, top, left + W, top + H)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.35)
    fit = photo.copy()
    fit.thumbnail((W - 80, int(H * 0.62)))
    bg.paste(fit, ((W - fit.width) // 2, int(H * 0.16)))
    return bg


def _overlay(text: str, header: str, footer: str) -> Image.Image:
    """Layer transparan berisi teks layar."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    if header:
        f = _font(44)
        draw.rounded_rectangle((40, 70, W - 40, 170), radius=24, fill=(0, 0, 0, 150))
        draw.text((W // 2, 120), header, font=f, fill="white", anchor="mm")

    big = _font(84)
    lines = textwrap.wrap(text.upper(), width=16) or [""]
    line_h = 104
    block_h = line_h * len(lines) + 60
    y0 = int(H * 0.80) - block_h // 2
    draw.rounded_rectangle((50, y0, W - 50, y0 + block_h), radius=32, fill=(255, 214, 0, 235))
    for i, line in enumerate(lines):
        draw.text((W // 2, y0 + 30 + line_h * i + line_h // 2), line, font=big, fill=(20, 20, 20), anchor="mm")

    if footer:
        draw.text((W // 2, H - 70), footer, font=_font(38), fill="white", anchor="mm",
                  stroke_width=3, stroke_fill="black")
    return layer


def _duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg gagal:\n{proc.stderr[-2000:]}")


def render_scene(index: int, bg: Image.Image, overlay: Image.Image, audio: Path | None,
                 fallback_seconds: float, workdir: Path) -> Path:
    bg_path = workdir / f"bg_{index}.png"
    ov_path = workdir / f"ov_{index}.png"
    out = workdir / f"scene_{index}.mp4"
    bg.save(bg_path)
    overlay.save(ov_path)

    seconds = (_duration(audio) + 0.35) if audio else fallback_seconds
    frames = int(seconds * FPS) + 1
    audio_input = ["-i", str(audio)] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    # Zoom in / zoom out bergantian supaya tiap adegan terasa hidup (efek Ken Burns).
    zoom = "min(zoom+0.0009,1.12)" if index % 2 == 0 else "if(eq(on,0),1.12,max(zoom-0.0009,1.0))"
    _run([
        "ffmpeg", "-y", "-i", str(bg_path), "-i", str(ov_path), *audio_input,
        "-filter_complex",
        f"[0]scale={int(W * 1.1)}:{int(H * 1.1)},"
        f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}[bg];"
        f"[bg][1]overlay=0:0,format=yuv420p[v]",
        "-map", "[v]", "-map", "2:a", "-t", f"{seconds:.2f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        str(out),
    ])
    return out


def render_video(script: dict, product: dict, photos: list[Image.Image], audios: list[Path | None],
                 out: Path, workdir: Path) -> Path:
    header = product.get("name", "")[:40]
    footer = "Link ada di caption"
    if product.get("price"):
        footer = f"{product['price']}  •  {footer}"

    clips = []
    for i, scene in enumerate(script["scenes"]):
        photo = photos[i % len(photos)] if photos else None
        words = len(scene["narration"].split())
        clips.append(render_scene(
            i, _background(photo, i), _overlay(scene["on_screen_text"], header, footer),
            audios[i], max(2.5, words * 0.42), workdir,
        ))

    listing = workdir / "concat.txt"
    listing.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
          "-c", "copy", "-movflags", "+faststart", str(out)])
    return out
