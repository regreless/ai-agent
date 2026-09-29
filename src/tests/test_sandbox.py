"""沙箱文件操作与路径边界测试，不调用模型。"""

import tempfile
import unittest
from pathlib import Path

from src.sandbox import SandboxConfig, create_sandbox


class SandboxTests(unittest.TestCase):
    def test_file_operations(self):
        """验证子目录、中文、覆盖、列表及不存在的文件。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = create_sandbox(SandboxConfig(temp_dir, verbose=False))
            self.assertEqual(sandbox.list_files(), [])
            file_path = sandbox.write_file("reports/note.md", "中文内容")
            self.assertEqual(Path(file_path), Path(temp_dir).resolve() / "output/reports/note.md")
            self.assertEqual(sandbox.read_file("reports/note.md"), "中文内容")
            sandbox.write_file("reports/note.md", "更新")
            self.assertEqual(sandbox.read_file("reports/note.md"), "更新")
            self.assertEqual(sandbox.list_files(), ["reports/note.md"])
            self.assertIsNone(sandbox.read_file("missing.md"))
            self.assertIsNone(sandbox.read_file("reports"))

    def test_path_escape(self):
        """拒绝父目录、相同前缀的兄弟目录、外部绝对路径及备用数据流。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = create_sandbox(SandboxConfig(temp_dir, verbose=False))
            outside_path = Path(temp_dir) / "private.txt"
            outside_path.write_text("unchanged", encoding="utf-8")
            for filename in ("../private.txt", "../output-other/file.txt", outside_path, "note.txt:stream"):
                with self.subTest(filename=filename):
                    self.assertFalse(sandbox.is_path_safe(filename))
                    self.assertIsNone(sandbox.read_file(filename))
                    with self.assertRaises(ValueError):
                        sandbox.write_file(filename, "changed")
            self.assertEqual(outside_path.read_text(encoding="utf-8"), "unchanged")
            self.assertTrue(sandbox.is_path_safe("reports/../note.md"))

    def test_output_directory_escape(self):
        """输出目录配置不能越出工作区，也不能直接使用工作区根目录。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            for output_dir in ("..", ".", "../outside"):
                with self.subTest(output_dir=output_dir), self.assertRaises(ValueError):
                    create_sandbox(SandboxConfig(temp_dir, output_dir, False))

    def test_symlink_escape(self):
        """拒绝通过已存在的符号链接读写输出目录外的文件。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = create_sandbox(SandboxConfig(temp_dir, verbose=False))
            outside_path = Path(temp_dir) / "outside"
            outside_path.mkdir()
            (outside_path / "private.txt").write_text("private", encoding="utf-8")
            try:
                (sandbox.output_path / "link").symlink_to(outside_path, target_is_directory=True)
            except OSError:
                self.skipTest("当前环境不允许创建符号链接")
            self.assertFalse(sandbox.is_path_safe("link/private.txt"))
            self.assertIsNone(sandbox.read_file("link/private.txt"))
            with self.assertRaises(ValueError):
                sandbox.write_file("link/new.txt", "blocked")
            self.assertEqual(sandbox.list_files(), [])
            self.assertFalse((outside_path / "new.txt").exists())


if __name__ == "__main__":
    unittest.main()
