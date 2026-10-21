import unittest
from types import SimpleNamespace

from qdrant_client import AsyncQdrantClient

from src.services.vector.qdrant_store import QdrantVectorStore


class VectorSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_with_installed_qdrant_client(self):
        vector_store = QdrantVectorStore.__new__(QdrantVectorStore)
        vector_store.settings = SimpleNamespace(qdrant_collection='test', vector_dim=2)
        vector_store.client = AsyncQdrantClient(':memory:')
        try:
            await vector_store.upsert_chunk([1.0, 0.0], {
                'tenant_id': 'tenant_a', 'kb_id': 'kb_a', 'content': 'matched',
            })
            await vector_store.upsert_chunk([1.0, 0.0], {
                'tenant_id': 'tenant_b', 'kb_id': 'kb_a', 'content': 'other tenant',
            })
            result = await vector_store.search([1.0, 0.0], 'tenant_a', ['kb_a'])
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['payload']['content'], 'matched')
        finally:
            await vector_store.client.close()
