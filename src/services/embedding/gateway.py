import hashlib
import math
import httpx
from src.core.config import get_settings


class EmbeddingGateway:
    def _hash_embedding(self, text: str, dim: int) -> list[float]:
        vec = [0.0] * dim
        tokens = list(text) if text else ["empty"]
        for token in tokens:
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            vec[h % dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    async def embed(self, text: str) -> list[float]:
        settings = get_settings()
        dim = settings.qwen_embedding_dim
        if not settings.qwen_embedding_api_key:
            return self._hash_embedding(text, dim)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.qwen_embedding_base_url}/embeddings",
                headers={"Authorization": f"Bearer {settings.qwen_embedding_api_key}"},
                json={
                    "model": settings.qwen_embedding_model,
                    "input": text,
                    "dimensions": dim,
                }
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]


embedding_gateway = EmbeddingGateway()
