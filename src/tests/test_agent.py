"""模拟模型响应，验证历史、流式回复、审批和文件输出。"""

import io
import json
import tempfile
import unittest
from unittest.mock import patch

from src.agent import create_dw_agent
from src.config import AgentConfig
from src.hitl import HitlConfig
from src.sandbox import SandboxConfig


def model_response(content):
    """构造普通响应，不请求网络。"""
    return io.BytesIO(json.dumps({"choices": [{"message": {"content": content}}]}).encode())


def stream_response(content, done=True):
    """逐字构造 SSE，可模拟连接中断。"""
    lines = ["data: " + json.dumps({"choices": []})]
    for text in content:
        lines.append("data: " + json.dumps({"choices": [{"delta": {"content": text}}]}))
    if done:
        lines.append("data: [DONE]")
    return io.BytesIO(("\n\n".join(lines) + "\n\n").encode())


class AgentTests(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.agent = create_dw_agent(
            config=AgentConfig(api_key="test-key"),
            sandbox=SandboxConfig(temp_dir.name, verbose=False),
            hitl=HitlConfig(enabled=False),
        )

    def test_history_and_prompt(self):
        with patch("src.agent.urlopen", side_effect=[model_response("第一条回复"), model_response("第二条回复")]) as request_mock:
            first_result = self.agent.invoke("第一条消息")
            self.agent.invoke("第二条消息")
        payload = json.loads(request_mock.call_args.args[0].data)
        self.assertEqual([item["role"] for item in payload["messages"]], ["system", "user", "assistant", "user"])
        for skill in self.agent.get_skills():
            self.assertIn(skill.script, payload["messages"][0]["content"])
        self.assertEqual(len(first_result.messages), 2)
        first_result.messages[0]["content"] = "外部修改"
        self.assertEqual(self.agent.conversation_history[0]["content"], "第一条消息")
        self.agent.clear_history()
        self.assertEqual(self.agent.conversation_history, [])

    def test_cancel_and_failure(self):
        with patch("src.agent.hitl_checkpoint", return_value=False), patch("src.agent.urlopen") as request_mock:
            result = self.agent.invoke("删除所有文件")
            self.assertEqual(result.files_written, [])
            request_mock.assert_not_called()
        with patch("src.agent.urlopen", side_effect=TimeoutError), self.assertRaises(TimeoutError):
            self.agent.invoke("测试")
        with self.assertRaises(ValueError):
            self.agent.invoke(" ")
        self.assertEqual(self.agent.conversation_history, [])

    def test_stream_and_files(self):
        content = '````filename:report.md\n# 报告\n```python\nprint("你好")\n```\n````\n```file:../escape.txt\n禁止\n```'
        with patch("src.agent.urlopen", return_value=stream_response(content)), patch("builtins.print"):
            result = self.agent.invoke_stream("生成报告")
        self.assertEqual(result.content, content)
        self.assertEqual(result.files_written, ["report.md"])
        self.assertEqual(self.agent.get_sandbox().read_file("report.md"), '# 报告\n```python\nprint("你好")\n```')
        self.assertFalse((self.agent.sandbox.workspace_path / "escape.txt").exists())

    def test_incomplete_stream(self):
        content = "```filename:partial.md\n内容\n```"
        with patch("src.agent.urlopen", return_value=stream_response(content, done=False)), patch("builtins.print"):
            with self.assertRaises(ValueError):
                self.agent.invoke_stream("生成文件")
        self.assertEqual(self.agent.conversation_history, [])
        self.assertEqual(self.agent.sandbox.list_files(), [])

    def test_file_approval(self):
        self.agent.hitl = HitlConfig(extra_keywords=["写入文件"])
        with patch("src.hitl.wait_for_confirmation", return_value=False), patch("builtins.print"):
            with patch("src.agent.urlopen", return_value=model_response("```filename:note.md\n内容\n```")):
                result = self.agent.invoke("生成文件")
        self.assertEqual(result.files_written, [])
        self.assertEqual(self.agent.sandbox.list_files(), [])

    def test_truncated_response(self):
        response = io.BytesIO(json.dumps({"choices": [{"finish_reason": "length", "message": {"content": "部分内容"}}]}).encode())
        with patch("src.agent.urlopen", return_value=response), self.assertRaises(ValueError):
            self.agent.invoke("生成内容")
        self.assertEqual(self.agent.conversation_history, [])


if __name__ == "__main__":
    unittest.main()
