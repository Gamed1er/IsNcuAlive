import os
import json
from typing import Optional

VERSION = "1.1.0"
VERSION_PATH = "data/version.json"

# 每次更新在最上面新增一筆，機器人重啟後會在通知頻道公告
CHANGELOG = {
    "1.1.0": [
        "網站炸超過 5 分鐘才會發出「炸了」通知，短暫抽風不再洗版",
        "只有發過「炸了」通知的網站，復活時才會通知",
        "每次當機都會記錄下來 (依舊每 1 分鐘檢查一次)",
        "機器人更新後會自動公告更新內容",
    ],
    "1.0.0": [
        "初版：每分鐘監測網站、/is_ncu_alive、/notify_channel_register",
    ],
}


def _parse(version: str) -> tuple[int, ...]:
    return tuple(int(x) for x in version.split("."))


def load_saved_version() -> Optional[str]:
    if not os.path.exists(VERSION_PATH):
        return None
    with open(VERSION_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("version")


def save_version():
    os.makedirs(os.path.dirname(VERSION_PATH), exist_ok=True)
    with open(VERSION_PATH, "w", encoding="utf-8") as f:
        json.dump({"version": VERSION}, f, indent=4)


def changes_since(old: Optional[str]) -> list[tuple[str, list[str]]]:
    """比 old 新的所有版本更新內容 (新到舊)；沒有舊版本紀錄時只回傳目前版本"""
    if old is None:
        return [(VERSION, CHANGELOG[VERSION])]
    return [
        (version, changes)
        for version, changes in CHANGELOG.items()
        if _parse(version) > _parse(old)
    ]
