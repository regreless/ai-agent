
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import Document, DocumentChunk, KnowledgeBase
from src.services.embedding.gateway import embedding_gateway
from src.services.rag.parser import parse_file, split_text
from src.services.vector.qdrant_store import vector_store


class RAGService:
    async def ingest_document(self,
                              db: AsyncSession,
                              tenant_id: str,
                              kb: KnowledgeBase,
                              file_path: str, filename: str,
                              content_type: str) -> dict:
        doc = Document(
            tenant_id=tenant_id,
            kb_id=kb.id,
            filename=filename,
            file_path=file_path,
            content_type=content_type,
            status="processing",
        )
        db.add(doc)
        await db.flush()
        text = parse_file(file_path)
        chunks = split_text(text)
        count = 0
        for index, chunk_text in enumerate(chunks):
            vector = await embedding_gateway.embed(chunk_text)
            payload = {
                "tenant_id": tenant_id,
                "kb_id": kb.id,
                "document_id": doc.id,
                "content": chunk_text,
                "source": f"{filename}#chunk-{index + 1}",
            }
            vector_id = await vector_store.upsert_chunk(vector, payload)
            chunk = DocumentChunk(
                tenant_id=tenant_id,
                kb_id=kb.id,
                document_id=doc.id,
                content=chunk_text,
                source=payload["source"],
                vector_id=vector_id,
                token_count=max(1, len(chunk_text) // 2),
            )
            db.add(chunk)
            count += 1
        doc.status = "ready"
        await db.commit()
        return {"document_id": doc.id, "chunks": count}

    async def retrieve(self,
                       tenant_id: str,
                       kb_ids: list[str],
                       query: str,
                       top_k: int = 5) -> list[dict]:
        vector = await embedding_gateway.embed(query)
        results = await vector_store.search(vector, tenant_id=tenant_id, kb_ids=kb_ids, limit=top_k)
        return results


rag_service = RAGService()
