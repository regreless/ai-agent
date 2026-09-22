import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.dml import Delete
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.rag import database, index, service


class RagTests(unittest.TestCase):
    def setUp(self):
        test_app = FastAPI()
        test_app.include_router(index.router, prefix="/rag")
        self.client = TestClient(test_app)

    def test_invalid_requests(self):
        for path, payload in [
            ("load", {"documents": []}),
            ("load", {"documents": [{"id": "a", "content": "  "}]}),
            ("search", {"query": " "}),
            ("search", {"query": "退款", "top_k": 0}),
            ("query", {"question": "退款", "top_k": 1.5}),
        ]:
            with self.subTest(path=path, payload=payload):
                self.assertEqual(self.client.post(f"/rag/{path}", json=payload).status_code, 422)

    def test_load_splits_and_preserves_source(self):
        with patch.object(service, "embeddings") as embeddings, patch.object(database, "get_session") as get_session, patch.object(database.Base.metadata, "create_all"):
            embeddings.embed_documents.side_effect = lambda texts: [[1.0, 0.0] for text in texts]
            session = get_session.return_value.__enter__.return_value
            response = self.client.post("/rag/load", json={
                "documents": [{"id": "doc-1", "content": "a" * 1100}],
            })
        self.assertEqual(response.status_code, 200)
        chunks = session.add_all.call_args.args[0]
        self.assertEqual(response.json()["total_chunk"], len(chunks))
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk.content) <= 500 for chunk in chunks))
        self.assertTrue(all(chunk.doc_metadata == {"source": "doc-1", "doc_id": "doc-1"} for chunk in chunks))

    def test_query_filters_context_and_sources_before_rounding(self):
        rows = [
            {"content": "允许七天内退款", "metadata": {"source": "规则"}, "distance": 0.5},
            {"content": "无关资料", "metadata": {"source": "其他"}, "distance": 0.50001},
        ]
        prompts = []

        def answer(prompt):
            prompts.append(prompt.to_string())
            return AIMessage(content="七天内。[1]")

        with patch.object(service, "retrieve_documents", MagicMock(return_value=rows)), patch.object(service, "llm", RunnableLambda(answer)):
            response = self.client.post("/rag/query", json={"question": "退款期限"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["sources"]), 1)
        self.assertIn("[1] 允许七天内退款", prompts[0])
        self.assertNotIn("无关资料", prompts[0])

    def test_empty_query_skips_model(self):
        with patch.object(service, "retrieve_documents", MagicMock(return_value=[])), patch.object(service, "llm") as llm:
            response = self.client.post("/rag/query", json={"question": "退款期限"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sources"], [])
        llm.invoke.assert_not_called()

    def test_search_distance(self):
        rows = [{"content": "正文", "metadata": {"source": "资料"}, "distance": 0.123456}]
        with patch.object(service, "retrieve_documents", MagicMock(return_value=rows)):
            response = self.client.post("/rag/search", json={"query": "正文"})
        result = response.json()["results"][0]
        self.assertEqual(result["score"], 0.1235)
        self.assertEqual(result["similarity"], 0.8765)

    def test_clear_failure_rolls_back_session_context(self):
        session = MagicMock()

        def execute(statement, **kwargs):
            if isinstance(statement, Delete) and statement.table.name == "langchain_pg_collection":
                raise OperationalError("delete", {}, Exception("simulated failure"))
            return MagicMock()

        session.execute.side_effect = execute
        session_context = MagicMock()
        session_context.__enter__.return_value = session
        with patch.object(database, "get_engine"), patch.object(database, "Session", return_value=session_context), patch.object(database, "tables_exist", return_value=True):
            with self.assertRaises(OperationalError):
                self.client.delete("/rag/clear")
        self.assertIs(session.begin.return_value.__exit__.call_args.args[0], OperationalError)
        delete_calls = [call for call in session.execute.call_args_list if isinstance(call.args[0], Delete)]
        self.assertEqual(len(delete_calls), 2)
        self.assertTrue(all(database.COLLECTION_NAME in call.args[0].compile().params.values() for call in delete_calls))

    def test_uninitialized_status(self):
        with patch.object(database, "get_session"), patch.object(database, "tables_exist", return_value=False):
            response = self.client.get("/rag/status")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["loaded"])
        self.assertEqual(response.json()["vector_count"], 0)

    def test_vector_query_compiles_for_postgresql(self):
        with patch.object(database, "get_session") as get_session, patch.object(database, "tables_exist", return_value=True), patch.object(service, "embeddings") as embeddings:
            session = get_session.return_value.__enter__.return_value
            session.execute.return_value.mappings.return_value.all.return_value = []
            embeddings.embed_query.return_value = [1.0, 0.0]
            self.assertEqual(service.retrieve_documents("query", 3), [])
        statement = session.execute.call_args.args[0]
        compiled = statement.compile(dialect=postgresql.dialect())
        self.assertIn("<=>", str(compiled))
        self.assertIn("FROM langchain_pg_collection", str(compiled))
        self.assertIn(database.COLLECTION_NAME, compiled.params.values())
        self.assertIn(3, compiled.params.values())


if __name__ == "__main__":
    unittest.main()
