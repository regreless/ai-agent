"""验证交互命令、历史、拒绝执行和错误恢复，不请求真实 API。"""

import tempfile
import unittest
from unittest.mock import patch

from src.agent import create_dw_agent
from src.config import AgentConfig
from src.index import main
from src.sandbox import SandboxConfig


class IndexTests(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.agent = create_dw_agent(
            config=AgentConfig(api_key="test-key"),
            sandbox=SandboxConfig(temp_dir.name, verbose=False),
        )

    def test_commands_and_history(self):
        inputs = [" ", "第一条", "第二条", "FILES", "CLEAR", "新消息", "EXIT"]
        responses = ["```filename:note.md\n内容\n```", "第二条回复", "新回复"]
        with patch("src.index.create_dw_agent", return_value=self.agent), patch("builtins.input", side_effect=inputs), patch("builtins.print") as print_mock:
            with patch.object(self.agent, "_request", side_effect=responses) as request_mock:
                main()
        self.assertEqual(request_mock.call_count, 3)
        self.assertEqual([len(call.args[0]) for call in request_mock.call_args_list], [2, 4, 2])
        self.assertTrue(all(call.args[1] for call in request_mock.call_args_list))
        self.assertEqual(len(self.agent.conversation_history), 2)
        self.assertEqual(self.agent.sandbox.read_file("note.md"), "内容")
        print_mock.assert_any_call("output/note.md")

    def test_rejection_and_error_recovery(self):
        inputs = ["删除所有文件", "n", "测试超时", "继续", "exit"]
        with patch("src.index.create_dw_agent", return_value=self.agent), patch("builtins.input", side_effect=inputs), patch("builtins.print"):
            with patch.object(self.agent, "_request", side_effect=[TimeoutError("timeout"), "成功"]) as request_mock:
                main()
        self.assertEqual(request_mock.call_count, 2)
        self.assertEqual([item["content"] for item in self.agent.conversation_history], ["继续", "成功"])

    def test_input_end(self):
        for error in (EOFError, KeyboardInterrupt):
            with self.subTest(error=error), patch("src.index.create_dw_agent", return_value=self.agent), patch("builtins.input", side_effect=error), patch("builtins.print"):
                main()


if __name__ == "__main__":
    unittest.main()
