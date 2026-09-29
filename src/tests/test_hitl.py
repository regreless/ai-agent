"""人工确认测试，模拟输入，不执行实际危险操作。"""

import unittest
from unittest.mock import patch

from src.hitl import HitlConfig, hitl_checkpoint, is_high_risk_operation, wait_for_confirmation


class HitlTests(unittest.TestCase):
    def test_keywords(self):
        """检查大小写、中文、自定义关键词和普通输入。"""
        self.assertTrue(is_high_risk_operation("DROP TABLE users"))
        self.assertTrue(is_high_risk_operation("请删除所有文件"))
        self.assertTrue(is_high_risk_operation("Deploy", ["deploy"]))
        self.assertFalse(is_high_risk_operation("生成文档"))

    def test_confirmation(self):
        """只有明确同意才放行，输入中断也拒绝。"""
        for answer, expected in [("y", True), (" YES ", True), ("n", False), ("", False), ("继续", False)]:
            with self.subTest(answer=answer), patch("builtins.input", return_value=answer):
                self.assertEqual(wait_for_confirmation(), expected)
        for error in (EOFError, KeyboardInterrupt):
            with patch("builtins.input", side_effect=error):
                self.assertFalse(wait_for_confirmation())

    @patch("builtins.print")
    @patch("src.hitl.wait_for_confirmation")
    def test_checkpoint(self, confirm_mock, print_mock):
        """普通操作、关闭检查和自动批准不询问；危险操作使用确认结果。"""
        self.assertTrue(hitl_checkpoint("生成文档"))
        self.assertTrue(hitl_checkpoint("rm -rf", HitlConfig(enabled=False)))
        self.assertTrue(hitl_checkpoint("rm -rf", HitlConfig(auto_approve=True)))
        confirm_mock.assert_not_called()
        for approved in (True, False):
            confirm_mock.return_value = approved
            self.assertEqual(hitl_checkpoint("rm -rf"), approved)
        confirm_mock.return_value = False
        self.assertFalse(hitl_checkpoint("发布", HitlConfig(extra_keywords=["发布"])))
        self.assertEqual(confirm_mock.call_count, 3)


if __name__ == "__main__":
    unittest.main()
