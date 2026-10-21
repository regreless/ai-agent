import uuid
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from src.core.config import get_settings


class QdrantVectorStore:
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncQdrantClient(url=self.settings.qdrant_url)

    async def ensure_collection(self):
        collections = await self.client.get_collections()
        names = [c.name for c in collections.collections]
        if self.settings.qdrant_collection not in names:
            await self.client.create_collection(
                collection_name=self.settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=self.settings.vector_dim, distance=Distance.COSINE
                )
            )

    async def upsert_chunk(self, vector: list[float], payload: dict) -> str:
        await self.ensure_collection()
        point_id = str(uuid.uuid4())
        await self.client.upsert(
            collection_name=self.settings.qdrant_collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return point_id

    async def search(self,
                     vector: list[float],
                     tenant_id: str,
                     kb_ids: list[str],
                     limit: int = 5) -> list[dict]:
        await self.ensure_collection()
        flt = Filter(
            must=[
                FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
            ]
        )
        result = await self.client.query_points(
            collection_name=self.settings.qdrant_collection,
            query=vector,
            query_filter=flt,
            limit=limit,
            with_payload=True,
        )
        items = []
        for point in result.points:
            payload = point.payload or {}
            if kb_ids and payload["kb_id"] not in kb_ids:
                continue
            items.append(
                {"id": str(point.id), "score": point.score, "payload": payload}
            )
        return  items



vector_store = QdrantVectorStore()
