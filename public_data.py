# -*- coding: utf-8 -*-
"""Load curated public bidding notices from docs/data/notices.json."""

import json
import os
from datetime import datetime

from config import BASE_DIR

DEFAULT_NOTICES_PATH = os.path.join(BASE_DIR, "docs", "data", "notices.json")

REQUIRED_FIELDS = ("notice_id", "title", "publish_date", "source_url", "category")


def notices_json_path() -> str:
    return DEFAULT_NOTICES_PATH


def load_notices_file(path: str = None) -> dict:
    path = path or DEFAULT_NOTICES_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("notices"), list):
        raise ValueError("notices.json must be an object with a notices array")
    return data


def validate_notices(data: dict) -> list:
    """Return validation error strings; empty list means OK."""
    errors = []
    seen_ids = set()
    seen_urls = set()
    notices = data.get("notices") or []
    for i, n in enumerate(notices):
        prefix = f"notices[{i}]"
        if not isinstance(n, dict):
            errors.append(f"{prefix} is not an object")
            continue
        for field in REQUIRED_FIELDS:
            if not n.get(field):
                errors.append(f"{prefix}.{field} is required")
        url = n.get("source_url") or ""
        if url and not url.startswith("http"):
            errors.append(f"{prefix}.source_url must be an http(s) URL")
        nid = n.get("notice_id")
        if nid:
            if nid in seen_ids:
                errors.append(f"duplicate notice_id: {nid}")
            seen_ids.add(nid)
        if url:
            if url in seen_urls:
                errors.append(f"duplicate source_url: {url}")
            seen_urls.add(url)
        date = n.get("publish_date") or ""
        if date:
            try:
                datetime.strptime(date[:10], "%Y-%m-%d")
            except ValueError:
                errors.append(f"{prefix}.publish_date is not YYYY-MM-DD: {date}")
    return errors


def to_db_records(data: dict = None, path: str = None) -> list:
    """Convert curated JSON into scraper/db notice dicts."""
    if data is None:
        data = load_notices_file(path)
    errors = validate_notices(data)
    if errors:
        raise ValueError("invalid notices.json:\n" + "\n".join(errors))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    for n in data["notices"]:
        records.append({
            "notice_id": n["notice_id"],
            "title": n["title"],
            "source": n.get("source") or "public",
            "source_url": n["source_url"],
            "notice_type": n.get("notice_type") or "招标公告",
            "project_name": n.get("project_name") or n["title"],
            "project_code": n.get("project_code") or "",
            "region": n.get("region") or "广东省",
            "budget": float(n.get("budget") or 0),
            "publish_date": n["publish_date"][:10],
            "deadline_date": n.get("deadline_date") or "",
            "tenderer": n.get("tenderer") or "",
            "agency": n.get("agency") or "",
            "winner": n.get("winner") or "",
            "win_amount": float(n.get("win_amount") or 0),
            "content": n.get("content") or "",
            "collected_at": now,
        })
    return records
