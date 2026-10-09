"""PostgreSQL 连接配置"""
import os

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "bc8c8696bf6d4a9db92093fff0c2f974")
PG_DATABASE = os.getenv("PG_DATABASE", "postgres")

# psycopg3 连接串，供 langchain_postgres PGVector 使用
PG_CONNECTION_STRING = (
    f"postgresql+psycopg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
)
