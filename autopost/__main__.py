"""Buat video AI untuk satu produk Shopee lalu posting otomatis ke Facebook Page dan/atau YouTube Shorts.

Contoh:
    python -m autopost                    # produk berikutnya (bergiliran), lalu posting
    python -m autopost --dry-run          # buat video saja, tidak posting
    python -m autopost --product 2        # pilih produk ke-3 di products.json
    python -m autopost --writer template  # naskah gratis tanpa AI
    python -m autopost --platforms youtube   # hanya posting ke YouTube
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLATFORMS = ("facebook", "youtube")


def default_platforms() -> str:
    """Env PLATFORMS kalau ada, selain itu platform yang kredensialnya sudah diset."""
    if os.environ.get("PLATFORMS"):
        return os.environ["PLATFORMS"]
    found = []
    if os.environ.get("FB_PAGE_ID") and os.environ.get("FB_PAGE_TOKEN"):
        found.append("facebook")
    if os.environ.get("YT_REFRESH_TOKEN"):
        found.append("youtube")
    return ",".join(found)


def build_caption(script: dict, product: dict) -> str:
    parts = [script["caption"].strip()]
    if product.get("affiliate_link"):
        parts.append(f"🛒 {product['affiliate_link']}")
    tags = " ".join("#" + t.lstrip("#").replace(" ", "") for t in script.get("hashtags", []))
    if tags:
        parts.append(tags)
    return "\n\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--products", type=Path, default=ROOT / "products.json")
    ap.add_argument("--state", type=Path, default=ROOT / "autopost_state.json")
    ap.add_argument("--product", type=int, help="indeks produk (default: bergiliran)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "output")
    ap.add_argument("--script-file", type=Path, help="pakai naskah JSON ini, lewati penulis naskah")
    ap.add_argument("--writer", choices=["auto", "claude", "template"], default="auto",
                    help="penulis naskah: claude (berbayar), template (gratis), "
                         "auto = claude kalau ANTHROPIC_API_KEY ada, selain itu template")
    ap.add_argument("--voice", default=os.environ.get("TTS_VOICE", "id-ID-GadisNeural"))
    ap.add_argument("--no-voice", action="store_true", help="video tanpa narasi suara")
    ap.add_argument("--dry-run", action="store_true", help="buat video, jangan posting")
    ap.add_argument("--platforms", default=default_platforms(),
                    help="tujuan posting dipisah koma: facebook,youtube "
                         "(default: env PLATFORMS, atau yang kredensialnya sudah diset)")
    ap.add_argument("--yt-privacy", choices=["public", "unlisted", "private"],
                    default=os.environ.get("YT_PRIVACY") or "public")
    args = ap.parse_args()
    platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    unknown = set(platforms) - set(PLATFORMS)
    if unknown:
        ap.error(f"platform tidak dikenal: {', '.join(sorted(unknown))}")

    products = json.loads(args.products.read_text())["products"]
    state = json.loads(args.state.read_text()) if args.state.exists() else {"next_index": 0, "history": []}
    index = args.product if args.product is not None else state["next_index"] % len(products)
    product = products[index]
    print(f"[1/4] Produk #{index}: {product['name']}")

    if args.script_file:
        script = json.loads(args.script_file.read_text())
    elif args.writer == "claude" or (args.writer == "auto" and os.environ.get("ANTHROPIC_API_KEY")):
        from .script import write_script
        script = write_script(product)
    else:
        from .template_script import write_script
        script = write_script(product)
    print(f"[2/4] Naskah: {script['title']} ({len(script['scenes'])} adegan)")

    from .render import load_images, render_video

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    video = args.out_dir / f"video-{index}-{stamp}.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        audios = []
        if args.no_voice:
            audios = [None] * len(script["scenes"])
        else:
            from .voice import synthesize
            for i, scene in enumerate(script["scenes"]):
                audios.append(synthesize(scene["narration"], work / f"vo_{i}.mp3", args.voice))
        photos = load_images([str(ROOT / p) if not p.startswith("http") else p
                              for p in product.get("images", [])], work)
        render_video(script, product, photos, audios, video, work)
    caption = build_caption(script, product)
    (video.with_suffix(".txt")).write_text(caption)
    print(f"[3/4] Video: {video}")

    if args.dry_run:
        print("[4/4] --dry-run: tidak diposting.\n\n" + caption)
        return 0

    if not platforms:
        print("Tidak ada platform tujuan. Set FB_PAGE_ID/FB_PAGE_TOKEN dan/atau YT_REFRESH_TOKEN, "
              "atau pakai --platforms.", file=sys.stderr)
        return 1

    posted: dict[str, str | None] = {}
    failed = False
    for platform in platforms:
        try:
            if platform == "facebook":
                posted["facebook"] = post_facebook(video, caption, script["title"])
            else:
                posted["youtube"] = post_youtube(video, caption, script, args.yt_privacy)
            print(f"[4/4] Terposting ke {platform}: id={posted[platform]}")
        except Exception as exc:  # satu platform gagal jangan hentikan yang lain
            failed = True
            print(f"[4/4] Gagal posting ke {platform}: {exc}", file=sys.stderr)
    if not posted:
        return 1

    if args.product is None:
        state["next_index"] = (index + 1) % len(products)
    state["history"] = ([{
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "product": product["name"], "title": script["title"],
        **{f"{p}_id": vid for p, vid in posted.items()},
    }] + state.get("history", []))[:100]
    args.state.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    return 1 if failed else 0


def post_facebook(video: Path, caption: str, title: str) -> str | None:
    page_id = os.environ.get("FB_PAGE_ID")
    page_token = os.environ.get("FB_PAGE_TOKEN")
    if not page_id or not page_token:
        raise RuntimeError("FB_PAGE_ID / FB_PAGE_TOKEN belum diset")
    from .facebook import post_video
    return post_video(page_id, page_token, video, caption, title=title).get("id")


def post_youtube(video: Path, caption: str, script: dict, privacy: str) -> str | None:
    creds = [os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")]
    if not all(creds):
        raise RuntimeError("YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN belum diset")
    from .youtube import get_access_token, upload_video
    token = get_access_token(*creds)
    return upload_video(token, video, script["title"], caption + " #Shorts",
                        tags=script.get("hashtags", []), privacy=privacy).get("id")


if __name__ == "__main__":
    sys.exit(main())
