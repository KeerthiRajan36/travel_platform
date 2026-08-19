import json
import logging

from cachetools import TTLCache

from app.config import settings

logger = logging.getLogger("cache")

_memory_cache: TTLCache = TTLCache(maxsize=256, ttl=30)
_redis_client = None
_redis_checked = False


def _get_redis():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True

    redis_url = getattr(settings, "REDIS_URL", None)
    if not redis_url:
        return None
    try:
        import redis as redis_lib

        client = redis_lib.from_url(redis_url, socket_connect_timeout=0.5)
        client.ping()
        _redis_client = client
        logger.info("Cache backend: Redis (%s)", redis_url)
    except Exception as exc:  # noqa: BLE001 - any connection failure -> fall back
        logger.info("Redis unavailable (%s); using in-memory cache instead.", exc)
        _redis_client = None
    return _redis_client


def cache_get(key: str):
    client = _get_redis()
    if client is not None:
        raw = client.get(key)
        return json.loads(raw) if raw is not None else None
    return _memory_cache.get(key)


def cache_set(key: str, value, ttl_seconds: int = 30) -> None:
    client = _get_redis()
    if client is not None:
        client.setex(key, ttl_seconds, json.dumps(value))
        return
    _memory_cache[key] = value


def cache_clear(key: str | None = None) -> None:
    client = _get_redis()
    if client is not None:
        if key:
            client.delete(key)
        else:
            client.flushdb()
        return
    if key:
        _memory_cache.pop(key, None)
    else:
        _memory_cache.clear()
