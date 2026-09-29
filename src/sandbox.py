"""文件工作区：默认将文件操作限制在 src/output，不提供代码执行隔离。"""

from dataclasses import dataclass
from pathlib import Path

WORKSPACE_PATH = Path(__file__).resolve().parent


@dataclass
class SandboxConfig:
    workspace_path: str | Path = WORKSPACE_PATH
    output_dir: str = "output"
    verbose: bool = True


class SandboxContext:
    def __init__(self, config: SandboxConfig):
        """初始化输出目录；输出目录必须位于工作区内部。"""
        self.workspace_path = Path(config.workspace_path).resolve()
        self.output_path = (self.workspace_path / config.output_dir).resolve()
        self.verbose = config.verbose
        if self.workspace_path not in self.output_path.parents:
            raise ValueError("输出目录必须是工作区内的子目录")
        self.output_path.mkdir(parents=True, exist_ok=True)
        if self.verbose:
            print(f"[Sandbox] 输出目录：{self.output_path}")

    def _resolve_path(self, target_path: str | Path) -> Path:
        """解析真实路径，拒绝越界路径及 Windows 备用数据流路径。"""
        file_path = Path(target_path)
        # 排除盘符后检查冒号，例如 C:\\output\\note.txt:stream。
        if ":" in str(file_path).removeprefix(file_path.drive):
            raise ValueError("文件名不能包含冒号")
        resolved_path = (self.output_path / file_path).resolve()
        if not resolved_path.is_relative_to(self.output_path):
            raise ValueError(f"路径越界：{target_path}")
        return resolved_path

    def is_path_safe(self, target_path: str | Path) -> bool:
        """检查解析后的路径是否在输出目录内，包括符号链接的真实目标。"""
        try:
            self._resolve_path(target_path)
            return True
        except (ValueError, OSError, RuntimeError):
            return False

    def write_file(self, filename: str | Path, content: str) -> str:
        """写入 UTF-8 文件，自动创建子目录；同名文件覆盖，返回绝对路径。"""
        target_path = self._resolve_path(filename)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        if self.verbose:
            print(f"[Sandbox] 已写入：{target_path.relative_to(self.output_path)}")
        return str(target_path)

    def read_file(self, filename: str | Path) -> str | None:
        """读取 UTF-8 文件；越界、文件不存在或目标是目录时返回 None。"""
        try:
            target_path = self._resolve_path(filename)
        except (ValueError, OSError, RuntimeError):
            if self.verbose:
                print(f"[Sandbox] 拒绝读取：{filename}")
            return None
        return target_path.read_text(encoding="utf-8") if target_path.is_file() else None

    def list_files(self) -> list[str]:
        """递归列出相对输出目录的文件名；跳过目录链接，避免越界和循环。"""
        files = []

        def walk(directory: Path):
            for file_path in directory.iterdir():
                if not self.is_path_safe(file_path):
                    continue
                if file_path.is_dir():
                    if not file_path.is_symlink() and not file_path.is_junction():
                        walk(file_path)
                elif file_path.is_file():
                    files.append(file_path.relative_to(self.output_path).as_posix())

        if self.output_path.exists():
            walk(self.output_path)
        return sorted(files)


def create_sandbox(config: SandboxConfig | None = None) -> SandboxContext:
    """创建文件工作区；不传配置时使用 src/output。"""
    return SandboxContext(config or SandboxConfig())
