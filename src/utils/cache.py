import time


class MemoryCache:
    def __init__(self):
        self.data = {}

    async def get(self, k):
        v = self.data.get(k)
        if not v:
            return None
        if v[1] and v[1] < time.time():
            self.data.pop(k, None)
            return None
        return v[0]

    async def set(self, k, v, ttl=300):
        self.data[k] = (v, time.time() + ttl if ttl else None)


cache = MemoryCache()
