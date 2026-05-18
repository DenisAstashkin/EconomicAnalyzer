import redis
import json
import hashlib
import time
from typing import Optional
from datetime import datetime, timezone

_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        try:
            from src.config import REDIS_URL
            _redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
            _redis_client.ping()
            print(f"[REDIS] Connected")
        except Exception as e:
            print(f"[REDIS] Connection failed: {e}")
            raise
    return _redis_client

def get_candle_hash(candle) -> str:
    if candle is None:
        return "no_candle"
    dt = getattr(candle, 'date_time', '')
    if dt and len(dt) >= 16:
        dt_minute = dt[:16]
    else:
        dt_minute = dt
    candle_data = f"{dt_minute}:{candle.close}:{candle.volume}"
    return hashlib.md5(candle_data.encode()).hexdigest()[:16]

def get_prediction_cache_key(ticket: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"invest_ai:{ticket}:daily:{today}"

def get_verdict_cache_key(ticket: str) -> str:
    hour = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
    return f"invest_ai:{ticket}:verdict:{hour}"

def get_news_cache_key(ticket: str) -> str:
    hour = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
    return f"invest_ai:{ticket}:news:{hour}"

def get_cached_prediction(ticket: str, cache_key: str) -> Optional[dict]:
    try:
        client = get_redis_client()
        print(f"[REDIS] GET: {cache_key}")
        data = client.get(cache_key)
        if data:
            print(f"[REDIS] HIT: {cache_key}")
            return json.loads(data)
        else:
            print(f"[REDIS] MISS: {cache_key}")
    except Exception as e:
        print(f"[REDIS] Get error: {e}")
    return None

def set_cached_prediction(ticket: str, cache_key: str, prediction, verdict: str, reason: str, ttl: int = 60) -> bool:
    try:
        client = get_redis_client()
        payload = {
            "prediction": prediction,
            "verdict": verdict,
            "reason": reason,
            "cached_at": time.time()
        }
        client.setex(cache_key, ttl, json.dumps(payload, ensure_ascii=False))
        print(f"[REDIS] SET: {cache_key} (TTL={ttl}s)")
        return True
    except Exception as e:
        print(f"[REDIS] Set error: {e}")
        import traceback
        traceback.print_exc()
    return False