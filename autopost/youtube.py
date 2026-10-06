"""Upload video ke YouTube (Shorts) lewat YouTube Data API v3.

Autentikasi memakai OAuth refresh token milik channel. Dapatkan sekali lewat:
    python -m autopost.youtube_auth
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
CATEGORY_PEOPLE_BLOGS = "22"


def get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    resp = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=60)
    body = resp.json() if resp.content else {}
    if not resp.ok:
        raise RuntimeError(f"Gagal refresh token YouTube: {body.get('error_description') or body.get('error') or resp.status_code}")
    return body["access_token"]


def _clean(text: str) -> str:
    # YouTube menolak tanda < dan > di judul/deskripsi.
    return text.replace("<", "").replace(">", "")


def _shorts_title(title: str) -> str:
    title = _clean(title).strip()
    suffix = " #Shorts"
    return title[: 100 - len(suffix)].rstrip() + suffix


def _truncate_bytes(text: str, limit: int) -> str:
    data = text.encode("utf-8")
    return text if len(data) <= limit else data[:limit].decode("utf-8", "ignore")


def upload_video(
    access_token: str,
    video: Path,
    title: str,
    description: str,
    tags: list[str] | None = None,
    privacy: str = "public",
) -> dict:
    """Upload video (resumable). Kembalikan JSON resource video dari YouTube."""
    tags = [_clean(t.lstrip("#")) for t in (tags or [])]
    # Batas total tag 500 karakter.
    while tags and len(",".join(tags)) > 450:
        tags.pop()
    metadata = {
        "snippet": {
            "title": _shorts_title(title),
            "description": _truncate_bytes(_clean(description), 4900),
            "tags": tags,
            "categoryId": CATEGORY_PEOPLE_BLOGS,
            "defaultLanguage": "id",
            "defaultAudioLanguage": "id",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    size = video.stat().st_size
    headers = {"Authorization": f"Bearer {access_token}"}

    last_error = None
    for attempt in range(3):
        init = requests.post(
            UPLOAD_URL,
            params={"uploadType": "resumable", "part": "snippet,status"},
            headers={**headers, "Content-Type": "application/json; charset=UTF-8",
                     "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
            data=json.dumps(metadata),
            timeout=60,
        )
        if init.ok:
            with video.open("rb") as fh:
                resp = requests.put(init.headers["Location"], headers={**headers, "Content-Type": "video/mp4"},
                                    data=fh, timeout=900)
        else:
            resp = init
        body = resp.json() if resp.content else {}
        if resp.ok:
            return body
        last_error = body.get("error", {}).get("message") or f"HTTP {resp.status_code}"
        if resp.status_code < 500:
            break
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Gagal upload ke YouTube: {last_error}")
