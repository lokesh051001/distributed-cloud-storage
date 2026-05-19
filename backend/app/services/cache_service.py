import time


class InMemoryCache:
    def __init__(self):
        self._store = {}

    def set(self, key: str, value, ttl_seconds: int = 60):
        self._store[key] = (value, time.time() + ttl_seconds)

    def get(self, key: str):
        item = self._store.get(key)
        if not item:
            return None
        value, expires_at = item
        if time.time() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def delete(self, key: str):
        self._store.pop(key, None)


metadata_cache = InMemoryCache()
