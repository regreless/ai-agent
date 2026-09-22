import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.graph import article, chat, code_review, email_approval, index
from app.graph import parallel, pipeline, react_agent, routing, supervisor


def make_model(*responses):
    return Mock(ainvoke=AsyncMock(side_effect=[AIMessage(content=text) for text in responses]))


class GraphTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_memory_isolation(self):
        with patch.object(chat, "llm", make_model("第一轮", "第二轮", "其他线程")) as model:
            thread_id = str(uuid4())
            await chat.memory_chat(thread_id, "我叫小明")
            await chat.memory_chat(thread_id, "我叫什么")
            self.assertEqual(len(model.ainvoke.call_args.args[0]), 4)
            history = await chat.get_history(thread_id)
            self.assertEqual([item["role"] for item in history], ["user", "assistant", "user", "assistant"])
            await chat.memory_chat(str(uuid4()), "你好")
            self.assertEqual(len(model.ainvoke.call_args.args[0]), 2)
            self.assertEqual(await chat.get_history(str(uuid4())), [])

    async def test_article_passes_keywords_and_preserves_log(self):
        with patch.object(article, "llm", make_model("Python，编程, AI", "文章摘要")) as model:
            result = await article.process("文章正文")
        self.assertEqual(result["keywords"], ["Python", "编程", "AI"])
        self.assertEqual(result["summary"], "文章摘要")
        self.assertEqual(len(result["log"]), 2)
        self.assertIn("Python、编程、AI", model.ainvoke.call_args.args[0][0].content)

    async def test_routing_valid_and_fallback(self):
        for category, expected in [("TECHNICAL", "technical"), ("pricing", "pricing"), ("invalid", "general")]:
            with self.subTest(category=category), patch.object(routing, "llm", make_model(category, "回答")):
                result = await routing.route_chat("问题")
            self.assertEqual(result["category"], expected)
            self.assertEqual(result["response"], "回答")

    async def test_pipeline_carries_previous_results(self):
        with patch.object(pipeline, "llm", make_model("素材", "大纲", "初稿", "定稿")) as model:
            result = await pipeline.process("主题")
        self.assertEqual(result["article"], "定稿")
        self.assertEqual(len(result["progress"]), 4)
        writer_prompt = model.ainvoke.call_args_list[2].args[0][0].content
        self.assertIn("素材", writer_prompt)
        self.assertIn("大纲", writer_prompt)
        self.assertIn("初稿", model.ainvoke.call_args.args[0][0].content)

    async def test_parallel_waits_for_all_tasks_before_merge(self):
        started_tasks = set()
        all_started = asyncio.Event()
        merge_prompts = []

        async def invoke(messages):
            prompt = messages[0].content
            if prompt.startswith("把以下任务"):
                return AIMessage(content="任务甲\n任务乙\n任务丙")
            if prompt.startswith("请完成"):
                task = prompt.splitlines()[-1]
                started_tasks.add(task)
                if len(started_tasks) == 3:
                    all_started.set()
                await asyncio.wait_for(all_started.wait(), timeout=2)
                return AIMessage(content=f"完成{task}")
            merge_prompts.append(prompt)
            return AIMessage(content="综合报告")

        with patch.object(parallel, "llm", Mock(ainvoke=invoke)):
            result = await parallel.parallel_chat("复杂任务")
        self.assertEqual(len(result["results"]), 3)
        self.assertEqual(result["final_report"], "综合报告")
        self.assertEqual(len(merge_prompts), 1)
        for task in started_tasks:
            self.assertIn(f"完成{task}", merge_prompts[0])

    async def test_parallel_empty_split_falls_back(self):
        with patch.object(parallel, "llm", make_model("\n", "处理结果", "报告")):
            result = await parallel.parallel_chat("原始任务")
        self.assertEqual(result["sub_tasks"], ["原始任务"])
        self.assertEqual(result["final_report"], "报告")

    async def test_supervisor_finishes_and_returns_worker_output(self):
        with patch.object(supervisor, "llm", make_model("researcher", "资料", "writer", "最终文章", "FINISH")):
            result = await supervisor.run("写文章")
        self.assertEqual(result["final_response"], "最终文章")
        self.assertEqual(result["completed_agents"], ["researcher", "writer"])
        with patch.object(supervisor, "llm", make_model("analyst", "分析结果", "analyst")):
            result = await supervisor.run("分析")
        self.assertEqual(result["final_response"], "分析结果")
        self.assertEqual(result["completed_agents"], ["analyst"])

    async def test_review_merges_valid_and_invalid_results(self):
        with patch.object(code_review, "llm", make_model(
            '```json\n{"issues":[],"score":8}\n```',
            '{"issues":["循环过多"],"score":6}',
            'invalid json', "改进建议",
        )) as model:
            result = await code_review.review("print('hello')", "Python")
        self.assertEqual(len(result["review_results"]), 3)
        self.assertEqual(sum(item["score"] is None for item in result["review_results"]), 1)
        self.assertIn("7.0/10", result["report"])
        self.assertEqual(model.ainvoke.await_count, 4)

    async def test_react_executes_tool_then_returns_to_model(self):
        bound_model = Mock(ainvoke=AsyncMock(side_effect=[
            AIMessage(content="", tool_calls=[{"name": "calculator", "args": {"a": 2, "b": 3, "operation": "+"}, "id": "calc-1"}]),
            AIMessage(content="", tool_calls=[{"name": "calculator", "args": {"a": 5, "b": 4, "operation": "*"}, "id": "calc-2"}]),
            AIMessage(content="答案为 20"),
        ]))
        model = Mock(bind_tools=Mock(return_value=bound_model))
        with patch.object(react_agent, "llm", model):
            result = await react_agent.chat(str(uuid4()), "计算 (2+3)*4")
        self.assertEqual(result["answer"], "答案为 20")
        self.assertEqual(bound_model.ainvoke.await_count, 3)
        first_result = bound_model.ainvoke.call_args_list[1].args[0][-1]
        self.assertEqual(first_result.tool_call_id, "calc-1")
        self.assertIn("= 5.0", first_result.content)
        tool_message = bound_model.ainvoke.call_args.args[0][-1]
        self.assertEqual(tool_message.type, "tool")
        self.assertIn("20", tool_message.content)


class GraphApiTests(unittest.TestCase):
    def setUp(self):
        test_app = FastAPI()
        test_app.include_router(index.router, prefix="/graph")
        self.client = TestClient(test_app)
        email_approval.graph.checkpointer = InMemorySaver()

    def test_rejects_blank_inputs(self):
        for path, payload in [
            ("memory-chat", {"message": " ", "thread_id": "chat-1"}),
            ("memory-chat", {"message": "你好", "thread_id": " "}),
            ("article", {"article": " "}), ("route", {"input": " "}),
            ("parallel", {"task": " "}), ("pipeline", {"topic": " "}),
            ("supervisor", {"input": " "}), ("code-review", {"code": " "}),
            ("email/start", {"request": "起草邮件", "thread_id": " "}),
            ("email/test/modify", {"feedback": " "}),
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.post(f"/graph/{path}", json=payload).status_code, 422)

    def test_email_modify_approve_and_duplicate_actions(self):
        draft = '{"subject":"邀请","recipient":"demo@example.com","body":"开会"}'
        revised_draft = '{"subject":"邀请","recipient":"demo@example.com","body":"请参加会议"}'
        with patch.object(email_approval, "llm", make_model(draft, revised_draft)) as model:
            response = self.client.post("/graph/email/start", json={"thread_id": "email-1", "request": "邀请开会"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "waiting_for_approval")
            self.assertEqual(response.json()["current_state"]["revision_count"], 0)
            duplicate = self.client.post("/graph/email/start", json={"thread_id": "email-1", "request": "重复"})
            self.assertEqual(duplicate.status_code, 409)
            modified = self.client.post("/graph/email/email-1/modify", json={"feedback": "礼貌些"})
            self.assertEqual(modified.json()["status"], "waiting_for_approval")
            self.assertEqual(modified.json()["review_data"]["draft"]["body"], "请参加会议")
            self.assertEqual(modified.json()["current_state"]["revision_count"], 1)
            self.assertIn("礼貌些", model.ainvoke.call_args.args[0][0].content)
            status = self.client.get("/graph/email/email-1/status").json()
            self.assertEqual(status["status"], "waiting_for_approval")
            approved = self.client.post("/graph/email/email-1/approve").json()
            self.assertEqual(approved["status"], "completed")
            self.assertEqual(approved["current_state"]["approval_status"], "approved")
            self.assertIn("未发送真实邮件", approved["current_state"]["final_status"])
            self.assertEqual(self.client.post("/graph/email/email-1/approve").status_code, 409)
            self.assertEqual(model.ainvoke.await_count, 2)

    def test_email_reject_and_missing_thread(self):
        with patch.object(email_approval, "llm", make_model("无法输出 JSON 的草稿")):
            started = self.client.post("/graph/email/start", json={"thread_id": "reject-1", "request": "起草"})
        self.assertEqual(started.json()["review_data"]["draft"]["recipient"], "未知")
        rejected = self.client.post("/graph/email/reject-1/reject").json()
        self.assertEqual(rejected["current_state"]["approval_status"], "rejected")
        self.assertEqual(rejected["status"], "completed")
        self.assertEqual(self.client.get("/graph/email/missing/status").status_code, 404)
        self.assertEqual(self.client.post("/graph/email/missing/approve").status_code, 404)

    def test_calculator_operations_and_weather_is_marked_mock(self):
        for operation, expected in [("+", 7.0), ("-", 3.0), ("*", 10.0), ("/", 2.5)]:
            with self.subTest(operation=operation):
                result = react_agent.calculator.invoke({"a": 5, "b": 2, "operation": operation})
                self.assertTrue(result.endswith(f"= {expected}"))
        self.assertIn("不支持的运算符", react_agent.calculator.invoke({"a": 2, "b": 3, "operation": "**"}))
        self.assertIn("除数不能为零", react_agent.calculator.invoke({"a": 1, "b": 0, "operation": "/"}))
        self.assertIn("模拟天气", react_agent.get_weather.invoke({"city": "北京"}))


if __name__ == "__main__":
    unittest.main()
