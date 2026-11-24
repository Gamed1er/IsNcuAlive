import os
import json

CHANNELS_PATH = "data/notify_channels.json"


def load_channels() -> list[int]:
    if not os.path.exists(CHANNELS_PATH):
        return []
    with open(CHANNELS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_channels(channels: list[int]):
    os.makedirs(os.path.dirname(CHANNELS_PATH), exist_ok=True)
    with open(CHANNELS_PATH, "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=4)


def toggle_channel(channel_id: int) -> bool:
    """註冊 / 取消註冊頻道，回傳切換後是否為已註冊"""
    channels = load_channels()
    if channel_id in channels:
        channels.remove(channel_id)
        registered = False
    else:
        channels.append(channel_id)
        registered = True
    save_channels(channels)
    return registered
