import os
import json
from datetime import datetime
from typing import Optional

OUTAGES_PATH = "data/outages.json"


def load_records() -> list[dict]:
    if not os.path.exists(OUTAGES_PATH):
        return []
    with open(OUTAGES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_records(records: list[dict]):
    os.makedirs(os.path.dirname(OUTAGES_PATH), exist_ok=True)
    with open(OUTAGES_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=4, ensure_ascii=False)


def _find_open(records: list[dict], url: str) -> Optional[dict]:
    for record in reversed(records):
        if record["url"] == url and record["end"] is None:
            return record
    return None


def open_records() -> dict[str, dict]:
    """還沒結束的當機紀錄，以 url 為 key (重啟時用來還原狀態)"""
    return {r["url"]: r for r in load_records() if r["end"] is None}


def start_outage(name: str, url: str, start: datetime, reason: Optional[str]):
    records = load_records()
    records.append({
        "name": name,
        "url": url,
        "start": start.isoformat(timespec="seconds"),
        "end": None,
        "duration_seconds": None,
        "reason": reason,
        "notified": False,  # 是否已發出「炸了」通知 (超過門檻才會發)
    })
    save_records(records)


def mark_notified(url: str):
    records = load_records()
    record = _find_open(records, url)
    if record:
        record["notified"] = True
        save_records(records)


def end_outage(url: str, end: datetime):
    records = load_records()
    record = _find_open(records, url)
    if record:
        record["end"] = end.isoformat(timespec="seconds")
        start = datetime.fromisoformat(record["start"])
        record["duration_seconds"] = int((end - start).total_seconds())
        save_records(records)
