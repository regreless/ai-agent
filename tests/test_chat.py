import unittest
from unittest.mock import patch

import httpx
from openai import APIConnectionError, APITimeoutError

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.deps import get_current_user
from src.api.v1.chat import router
from src.db.session import Base, get_db
from src.models.entities import Agent, Conversation, Message, ModelProvider, ToolDefinition, User
from src.services.llm.gateway import LLMResult
from src.services.workflow.engine import llm_gateway, rag_service


class AsyncSessionAdapter:
    def __init__(self, session):
        self.session = session

    async def execute(self, statement):
        return self.session.execute(statement)

    def add(self, entity):
        self.session.add(entity)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            'sqlite://', poolclass=StaticPool,
            connect_args={'check_same_thread': False},
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        self.session.add_all([
            ModelProvider(id='model_a', tenant_id='tenant_a', provider='mock',
                          model_name='mock', display_name='Mock'),
            ToolDefinition(id='tool_a', tenant_id='tenant_a', name='query_order'),
            Agent(id='agent_a', tenant_id='tenant_a', name='Agent', code='agent',
                  model_provider_id='model_a', tool_ids=['tool_a']),
        ])
        self.session.commit()
        self.db = AsyncSessionAdapter(self.session)
        app = FastAPI()
        app.include_router(router, prefix='/api/v1/chat')

        async def override_db():
            yield self.db

        async def override_user():
            return User(id='user_a', tenant_id='tenant_a')

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = override_user
        self.client = TestClient(app)
        self.rag_patch = patch.object(rag_service, 'retrieve', autospec=True, return_value=[])
        self.rag_mock = self.rag_patch.start()
        self.llm_patch = patch.object(
            llm_gateway, 'chat', autospec=True,
            return_value=LLMResult(content='助手回复', input_tokens=10, output_tokens=5, raw={}),
        )
        self.llm_mock = self.llm_patch.start()

    def tearDown(self):
        self.llm_patch.stop()
        self.rag_patch.stop()
        self.client.close()
        self.session.close()
        self.engine.dispose()

    def test_first_message_creates_conversation_and_saves_answer(self):
        response = self.client.post('/api/v1/chat', json={
            'agent_id': 'agent_a', 'message': '订单 10001',
        })
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()['data']
        conversation = self.session.get(Conversation, data['conversation_id'])
        self.assertEqual(conversation.user_id, 'user_a')
        messages = self.session.execute(select(Message)).scalars().all()
        self.assertEqual(len(messages), 2)
        self.assertTrue(all(item.conversation_id == conversation.id for item in messages))
        self.assertEqual({item.role: item.content for item in messages},
                         {'user': '订单 10001', 'assistant': '助手回复'})
        self.assertEqual(data['tool_results'][0]['order_id'], '10001')
        self.rag_mock.assert_awaited_once_with('tenant_a', [], '订单 10001', top_k=5)
        self.assertIn('query_order', self.llm_mock.call_args.args[1][1]['content'])

    def test_explicit_null_creates_conversation(self):
        response = self.client.post('/api/v1/chat', json={
            'agent_id': 'agent_a', 'message': '你好', 'conversation_id': None,
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['data']['conversation_id'])

    def test_existing_conversation_is_reused(self):
        self.session.add(Conversation(id='conv_a', tenant_id='tenant_a',
                                      user_id='user_a', agent_id='agent_a'))
        self.session.commit()
        response = self.client.post('/api/v1/chat', json={
            'agent_id': 'agent_a', 'message': '继续', 'conversation_id': 'conv_a',
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['data']['conversation_id'], 'conv_a')
        self.assertEqual(len(self.session.execute(select(Conversation)).scalars().all()), 1)

    def test_model_failures_return_explicit_status(self):
        request = httpx.Request('POST', 'https://model.invalid/chat/completions')
        for error, status_code in (
            (APITimeoutError(request=request), 504),
            (APIConnectionError(request=request), 502),
        ):
            with self.subTest(status_code=status_code):
                with patch.object(llm_gateway, 'chat', side_effect=error):
                    response = self.client.post('/api/v1/chat', json={
                        'agent_id': 'agent_a', 'message': '10001',
                    })
                self.assertEqual(response.status_code, status_code, response.text)
                self.session.rollback()
