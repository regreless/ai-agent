"""通用文档加载工具，不依赖模型配置或向量存储。"""

import csv
from pathlib import Path

from langchain_core.documents import Document


def load_csv(file_path: str | Path) -> list[Document]:
    """将带表头的 CSV 每一行转换为一个 Document。"""
    with open(file_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [
            Document(
                page_content="\n".join(
                    f"{key}: {value}"
                    for key, value in row.items()
                ),
                metadata={"source": str(file_path), "row": index},
            )
            for index, row in enumerate(reader)
        ]


def load_documents(file_path: str | Path) -> list[Document]:
    """按文件类型加载文档；复杂格式需要安装 langchain-docling。"""
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"文档不存在：{path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return load_csv(path)
    if suffix in {".txt", ".md"}:
        return [Document(
            page_content=path.read_text(encoding="utf-8-sig"),
            metadata={"source": str(path)},
        )]
    if suffix in {".pdf", ".docx", ".pptx", ".html", ".htm"}:
        try:
            from langchain_docling import DoclingLoader
        except ModuleNotFoundError as exc:
            if exc.name != "langchain_docling":
                raise
            raise ImportError(
                "加载此格式需要安装依赖：pip install -U langchain-docling"
            ) from exc
        return DoclingLoader(file_path=str(path)).load()

    raise ValueError(f"不支持的文档格式：{suffix or '无扩展名'}")
