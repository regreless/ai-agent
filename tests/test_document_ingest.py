import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.entities import Document, DocumentChunk
from src.services.rag.service import RAGService


class DocumentIngestTests(unittest.IsolatedAsyncioTestCase):
    async def test_ingest_text_document(self):
        db = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        text = "七天无理由退货，商品须符合完好要求。"
        with tempfile.TemporaryDirectory() as upload_dir:
            file_path = Path(upload_dir) / "tk.txt"
            file_path.write_text(text, encoding="utf-8")
            with (
                patch("src.services.rag.service.embedding_gateway.embed", new_callable=AsyncMock) as embed,
                patch("src.services.rag.service.vector_store.upsert_chunk", new_callable=AsyncMock) as upsert_chunk,
            ):
                embed.return_value = [1.0, 0.0]
                upsert_chunk.return_value = "vector_a"
                result = await RAGService().ingest_document(
                    db, "tenant_a", SimpleNamespace(id="kb_a"),
                    str(file_path), "tk.txt", "text/plain",
                )

        self.assertEqual(result["chunks"], 1)
        embed.assert_awaited_once_with(text)
        vector, payload = upsert_chunk.await_args.args
        self.assertEqual(vector, [1.0, 0.0])
        self.assertEqual(payload["content"], text)
        self.assertEqual(payload["kb_id"], "kb_a")
        document = db.add.call_args_list[0].args[0]
        chunk = db.add.call_args_list[1].args[0]
        self.assertIsInstance(document, Document)
        self.assertEqual(document.status, "ready")
        self.assertIsInstance(chunk, DocumentChunk)
        self.assertEqual(chunk.vector_id, "vector_a")
        db.commit.assert_awaited_once()
