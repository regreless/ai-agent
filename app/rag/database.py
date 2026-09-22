"""数据库：ORM 模型、会话和向量数据读写。"""

import os
from contextlib import contextmanager
from functools import cache
from pathlib import Path
from uuid import UUID, uuid4

from dotenv import load_dotenv
from fastapi import HTTPException
from pgvector.sqlalchemy import VECTOR
from sqlalchemy import DDL, ForeignKey, String, Text, create_engine, delete, func, inspect, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

COLLECTION_NAME = "rag-knowledge-base"


class Base(DeclarativeBase):
    pass


class RagCollection(Base):
    __tablename__ = "langchain_pg_collection"

    uuid: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    name: Mapped[str | None] = mapped_column(String)
    cmetadata: Mapped[dict | None] = mapped_column(JSONB)


class RagEmbedding(Base):
    __tablename__ = "langchain_pg_embedding"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    content: Mapped[str | None] = mapped_column(Text)
    # metadata 是 DeclarativeBase 的保留属性，映射时保留原数据库列名。
    doc_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    embedding: Mapped[list[float] | None] = mapped_column(VECTOR())
    collection_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("langchain_pg_collection.uuid", ondelete="CASCADE")
    )


COLLECTION_IDS = select(RagCollection.uuid).where(RagCollection.name == COLLECTION_NAME)
COLLECTION_FILTER = RagEmbedding.collection_id.in_(COLLECTION_IDS)


@cache
def get_engine():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(503, "请在环境变量或项目 .env 中配置 DATABASE_URL")
    url = make_url(database_url).set(drivername="postgresql+psycopg")
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})


@contextmanager
def get_session():
    # 普通 def 路由由 FastAPI 在线程池执行；会话自动提交或回滚。
    with Session(get_engine()) as session, session.begin():
        yield session


def tables_exist(session):
    inspector = inspect(session.connection())
    return all(inspector.has_table(table_name) for table_name in Base.metadata.tables)


def save_documents(chunks, vectors):
    with get_session() as session:
        session.execute(select(func.pg_advisory_xact_lock(73192021)))
        connection = session.connection()
        connection.execute(DDL("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(connection)
        collection_id = session.scalar(COLLECTION_IDS.limit(1))
        if collection_id is None:
            collection_id = uuid4()
            session.add(RagCollection(uuid=collection_id, name=COLLECTION_NAME))
            session.flush()
        session.add_all([
            RagEmbedding(
                content=chunk.page_content,
                doc_metadata=chunk.metadata,
                embedding=vector,
                collection_id=collection_id,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ])


def search_vectors(query_vector, top_k):
    with get_session() as session:
        if not tables_exist(session):
            return []
        distance = RagEmbedding.embedding.cosine_distance(query_vector).label("distance")
        statement = (
            select(
                RagEmbedding.content,
                RagEmbedding.doc_metadata.label("metadata"),
                distance,
            )
            .where(COLLECTION_FILTER, RagEmbedding.embedding.is_not(None))
            .order_by(distance, RagEmbedding.id)
            .limit(top_k)
        )
        return session.execute(statement).mappings().all()


def count_vectors():
    with get_session() as session:
        if not tables_exist(session):
            return 0
        return session.scalar(select(func.count()).select_from(RagEmbedding).where(COLLECTION_FILTER))


def clear_knowledge():
    with get_session() as session:
        session.execute(select(func.pg_advisory_xact_lock(73192021)))
        if tables_exist(session):
            session.execute(
                delete(RagEmbedding).where(COLLECTION_FILTER),
                execution_options={"synchronize_session": False},
            )
            session.execute(
                delete(RagCollection).where(RagCollection.name == COLLECTION_NAME)
            )
