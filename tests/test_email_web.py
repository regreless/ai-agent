import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from streamlit.testing.v1 import AppTest

from app.graph import email_approval, index


class EmailWebTests(unittest.TestCase):
    def test_approval_page_flow(self):
        test_app = FastAPI()
        test_app.include_router(index.router, prefix="/graph")
        client = TestClient(test_app)
        model = Mock(ainvoke=AsyncMock(side_effect=[
            AIMessage(content='{"subject":"邀请","recipient":"demo@example.com","body":"开会"}'),
            AIMessage(content='{"subject":"邀请","recipient":"demo@example.com","body":"请参加会议"}'),
            AIMessage(content="普通文本草稿"),
        ]))
        page_path = Path(__file__).resolve().parents[1] / "app/graph/web.py"

        def request_api(method, url, **kwargs):
            kwargs.pop("timeout", None)
            self.assertFalse(kwargs.pop("trust_env"))
            response = client.request(method, url, **kwargs)
            return httpx.Response(
                response.status_code, content=response.content,
                request=httpx.Request(method, url),
            )

        with (
            patch.object(email_approval, "graph", email_approval.build_graph()),
            patch.object(email_approval, "llm", model),
            patch("httpx.request", side_effect=request_api),
        ):
            page = AppTest.from_file(str(page_path)).run()

            def click_button(label):
                next(button for button in page.button if button.label == label).click().run()
                self.assertFalse(page.exception)

            click_button("起草邮件")
            self.assertEqual(page.warning[0].value, "请填写邮件需求。")
            page.text_area[0].input("邀请开会")
            click_button("起草邮件")
            self.assertEqual(page.session_state.email_result["status"], "waiting_for_approval")
            click_button("修改并重新起草")
            self.assertEqual(page.warning[0].value, "请填写修改意见。")
            page.text_area[1].input("礼貌些")
            click_button("修改并重新起草")
            self.assertEqual(page.session_state.email_result["current_state"]["revision_count"], 1)
            self.assertIn("请参加会议", [item.value for item in page.text])
            click_button("查询 / 刷新状态")
            click_button("批准（模拟发送）")
            self.assertIn("未发送真实邮件", page.success[0].value)
            self.assertFalse(any(button.label == "批准（模拟发送）" for button in page.button))
            previous_thread = page.session_state.thread_id
            click_button("新建审批")
            self.assertIsNone(page.session_state.email_result)
            self.assertNotEqual(page.session_state.thread_id, previous_thread)
            page.text_area[0].input("重新起草")
            click_button("起草邮件")
            click_button("驳回")
            self.assertEqual(page.success[0].value, "邮件已取消，未发送")
            page.text_input(key="thread_id").input(previous_thread).run()
            click_button("查询 / 刷新状态")
            self.assertEqual(page.session_state.email_result["current_state"]["approval_status"], "approved")
            page.text_input(key="thread_id").input("missing-thread").run()
            click_button("查询 / 刷新状态")
            self.assertIn("404", page.error[0].value)
            self.assertIsNone(page.session_state.email_result)
            self.assertEqual(model.ainvoke.await_count, 3)
