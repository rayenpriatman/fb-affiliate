"""Upload video ke Facebook Page lewat Graph API."""

from __future__ import annotations

import time
from pathlib import Path

import requests

GRAPH_VERSION = "v25.0"
GRAPH_VIDEO_BASE = f"https://graph-video.facebook.com/{GRAPH_VERSION}"


def post_video(
    page_id: str,
    page_token: str,
    video: Path,
    description: str,
    title: str = "",
    scheduled_publish_time: int | None = None,
) -> dict:
    """Publish (atau jadwalkan) video ke Page. Kembalikan JSON respons Graph API."""
    data = {"access_token": page_token, "description": description}
    if title:
        data["title"] = title
    if scheduled_publish_time:
        data["published"] = "false"
        data["scheduled_publish_time"] = str(scheduled_publish_time)

    last_error = None
    for attempt in range(3):
        with video.open("rb") as fh:
            resp = requests.post(
                f"{GRAPH_VIDEO_BASE}/{page_id}/videos",
                data=data,
                files={"source": (video.name, fh, "video/mp4")},
                timeout=600,
            )
        body = resp.json() if resp.content else {}
        if resp.ok:
            return body
        last_error = body.get("error", {}).get("message") or f"HTTP {resp.status_code}"
        if resp.status_code < 500:
            break
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Gagal upload ke Facebook: {last_error}")
