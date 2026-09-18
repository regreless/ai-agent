"""Ollama + PostgreSQL/pgvector 知识库，同步调用。

依赖：pip install langchain-ollama langchain-text-splitters "psycopg[binary,pool]"
数据库连接、集合名称和模型配置直接在构造方法中设置。
数据库需提前创建 pgvector 扩展、langchain_pg_collection 和 langchain_pg_embedding 表。
本文件只负责数据读写，向量模型必须与已有数据一致。

用法：
    rag = RagDbService()
    try:
        rag.load_documents([{"id": "faq", "content": "订单支持七天无理由退货。"}])
        print(rag.query("如何退货？"))
    finally:
        rag.close()
"""

import json

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from psycopg import Error
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool, PoolTimeout

SYSTEM_PROMPT = """你是知识库问答助手，严格基于参考资料回答。
1. 只根据参考资料内容回答，不能使用资料外的知识。
2. 资料中没有相关信息，回答“知识库中暂无相关内容”。
3. 回答简洁准确，使用中文。
参考资料：
{context}
"""
MAX_DISTANCE = 0.5


class RagDbService:
    def __init__(self):
        self.collection_name = "rag-knowledge-base"
        base_url = "http://localhost:11434"
        self.embeddings = OllamaEmbeddings(
            model="tmxbai-embed-large:latest",
            base_url=base_url,
        )
        model = ChatOllama(
            model="qwen3.5:0.8b",
            base_url=base_url, temperature=0.3, reasoning=False, num_predict=512,
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT), ("human", "{question}"),
        ])
        self.chain = prompt | model | StrOutputParser()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=50,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""],
        )
        self.pg_pool = ConnectionPool(
            'postgresql://postgres:bc8c8696bf6d4a9db92093fff0c2f974@127.0.0.1:5432/postgres', min_size=0, max_size=10, max_idle=30,
            timeout=2, kwargs={"connect_timeout": 2}, open=True,
        )

    def load_documents(self, documents: list[dict]) -> dict:
        chunks = self.splitter.create_documents(
            [document["content"] for document in documents],
            [{"source": document.get("source") or document["id"], "doc_id": document["id"]}
             for document in documents],
        )
        if chunks:
            vectors = self.embeddings.embed_documents([chunk.page_content for chunk in chunks])
            with self.pg_pool.connection() as connection:
                # 同一集合的导入和清空串行执行，防止重复创建集合或中途删除。
                connection.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (self.collection_name,))
                row = connection.execute(
                    "SELECT uuid FROM langchain_pg_collection WHERE name = %s LIMIT 1",
                    (self.collection_name,),
                ).fetchone()
                collection_id = row[0] if row else connection.execute(
                    "INSERT INTO langchain_pg_collection (name) VALUES (%s) RETURNING uuid",
                    (self.collection_name,),
                ).fetchone()[0]
                with connection.cursor() as cursor:
                    cursor.executemany("""
                        INSERT INTO langchain_pg_embedding (content, metadata, embedding, collection_id)
                        VALUES (%s, %s, %s::vector, %s)
                    """, [(chunk.page_content, Jsonb(chunk.metadata), json.dumps(vector), collection_id)
                          for chunk, vector in zip(chunks, vectors, strict=True)])
        return {
            "success": True, "original_docs": len(documents), "total_chunk": len(chunks),
            "message": f"加载 {len(documents)} 篇文档，共 {len(chunks)} 个块",
        }

    def _retrieve(self, query: str, top_k: int) -> list[dict]:
        if not query.strip():
            raise ValueError("查询内容不能为空")
        if type(top_k) is not int or top_k <= 0:
            raise ValueError("top_k 必须是正整数")
        vector = json.dumps(self.embeddings.embed_query(query))
        with self.pg_pool.connection() as connection:
            rows = connection.execute("""
                SELECT content, metadata, embedding <=> %s::vector AS distance
                FROM langchain_pg_embedding
                WHERE collection_id IN (
                    SELECT uuid FROM langchain_pg_collection WHERE name = %s
                ) AND embedding IS NOT NULL
                ORDER BY distance LIMIT %s
            """, (vector, self.collection_name, top_k)).fetchall()
        return [{"content": content, "source": (metadata or {}).get("source"),
                 "raw_distance": float(distance)} for content, metadata, distance in rows]

    @staticmethod
    def _format_result(result: dict) -> dict:
        distance = round(result["raw_distance"], 4)
        return {**result, "score": distance, "raw_distance": distance,
                "similarity": f"{1 - distance:.4f}"}

    def search(self, query: str, top_k: int = 3) -> dict:
        return {"query": query, "results": [self._format_result(result)
                for result in self._retrieve(query, top_k)]}

    def query(self, question: str, top_k: int = 3) -> dict:
        # 用原始距离过滤，不能先四舍五入再判断阈值。
        results = [result for result in self._retrieve(question, top_k)
                   if result["raw_distance"] <= MAX_DISTANCE]
        if not results:
            return {"question": question, "answer": "知识库中没有找到相关的内容", "sources": []}
        context = "\n\n".join(f"[{index}] {result['content']}"
                              for index, result in enumerate(results, 1))
        answer = self.chain.invoke({"context": context, "question": question})
        return {"question": question, "answer": answer,
                "sources": [self._format_result(result) for result in results]}

    def get_status(self) -> dict:
        vector_count = 0
        try:
            with self.pg_pool.connection() as connection:
                vector_count = connection.execute("""
                    SELECT COUNT(*) FROM langchain_pg_embedding
                    WHERE collection_id IN (
                        SELECT uuid FROM langchain_pg_collection WHERE name = %s
                    )
                """, (self.collection_name,)).fetchone()[0]
            message = f"已加载 {vector_count} 个向量块" if vector_count else "知识库为空"
        except (Error, PoolTimeout):
            vector_count = 0
            message = "获取状态失败，请检查数据库连接和 pgvector 扩展"
        return {"mode": "pgvector", "loaded": vector_count > 0,
                "vector_count": vector_count, "collection": self.collection_name, "message": message}

    def clear_knowledge(self) -> dict:
        with self.pg_pool.connection() as connection:
            connection.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (self.collection_name,))
            # 已建外键 ON DELETE CASCADE，删除集合时自动清除对应向量。
            connection.execute("DELETE FROM langchain_pg_collection WHERE name = %s",
                               (self.collection_name,))
        return {"success": True, "message": "知识库已经清空"}

    def close(self):
        self.pg_pool.close()
