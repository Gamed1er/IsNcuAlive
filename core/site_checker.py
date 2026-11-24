import time
import asyncio
import aiohttp
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

REQUEST_TIMEOUT = 10  # 單次請求逾時秒數


@dataclass
class CheckResult:
    ok: bool
    latency_ms: Optional[float] = None  # 失敗時為 None
    error: Optional[str] = None


@dataclass
class SiteState:
    name: str
    url: str
    is_up: Optional[bool] = None  # None = 還沒檢查過
    down_since: Optional[datetime] = None


async def ping_once(session: aiohttp.ClientSession, url: str) -> CheckResult:
    """發送一次 GET，只要伺服器有回應且不是 5xx 就算活著"""
    start = time.perf_counter()
    try:
        async with session.get(url, allow_redirects=True, ssl=False) as resp:
            latency = (time.perf_counter() - start) * 1000
            if resp.status >= 500:
                return CheckResult(False, latency, f"HTTP {resp.status}")
            return CheckResult(True, latency)
    except asyncio.TimeoutError:
        return CheckResult(False, error="逾時")
    except aiohttp.ClientError as e:
        return CheckResult(False, error=type(e).__name__)


async def ping(session: aiohttp.ClientSession, url: str, attempts: int = 2) -> CheckResult:
    """連續 ping 最多 attempts 次，全部失敗才算連接失敗"""
    result = CheckResult(False)
    for _ in range(attempts):
        result = await ping_once(session, url)
        if result.ok:
            return result
    return result


def new_session() -> aiohttp.ClientSession:
    return aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
        headers={"User-Agent": "Mozilla/5.0 (IsNcuDown monitor)"},
    )


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days} 天")
    if hours:
        parts.append(f"{hours} 小時")
    if minutes:
        parts.append(f"{minutes} 分鐘")
    if seconds or not parts:
        parts.append(f"{seconds} 秒")
    return " ".join(parts)
