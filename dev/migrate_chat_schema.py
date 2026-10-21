"""Upgrade legacy PostgreSQL chat tables without removing historical data."""
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.session import engine


async def migrate_chat_schema():
    try:
        async with engine.begin() as connection:
            await connection.execute(text(
                'ALTER TABLE conversations ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64), '
                'ADD COLUMN IF NOT EXISTS agent_id VARCHAR(64)'
            ))
            await connection.execute(text(
                'ALTER TABLE messages ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP'
            ))
            await connection.execute(text(
                'UPDATE messages SET updated_at = created_at WHERE updated_at IS NULL'
            ))
            await connection.execute(text(
                'UPDATE conversations AS conversation SET tenant_id = account.tenant_id '
                'FROM users AS account WHERE conversation.user_id = account.id '
                'AND conversation.tenant_id IS NULL'
            ))
            legacy_defaults = {
                'conversations': {'status': "'active'"},
                'messages': {'prompt_tokens': '0', 'completion_tokens': '0', 'total_tokens': '0'},
            }
            for table_name, defaults in legacy_defaults.items():
                columns = set((await connection.execute(text(
                    'SELECT column_name FROM information_schema.columns '
                    "WHERE table_schema = current_schema() AND table_name = :table_name"
                ), {'table_name': table_name})).scalars())
                for column_name, default_value in defaults.items():
                    if column_name in columns:
                        await connection.execute(text(
                            f'ALTER TABLE {table_name} ALTER COLUMN {column_name} '
                            f'SET DEFAULT {default_value}'
                        ))
        print('Chat schema migration complete.')
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(
        migrate_chat_schema(),
        loop_factory=asyncio.SelectorEventLoop if sys.platform == 'win32' else None,
    )
