import os

import hashlib

from langchain_core.documents import Document
from pypdf import PdfReader

from agent.utils.logger_handler import logger


def get_file_md5_hex(filepath):
    if not os.path.exists(filepath):
        logger.error(f"[md5计算]文件{filepath}不存在")
        return

    if not os.path.isfile(filepath):
        logger.error(f"[md5计算]路径{filepath}不是文件")
        return

    md5_obj = hashlib.md5()

    chunk_size = 4096  # 4KB分片，避免文件过大爆内存

    try:
        with open(filepath, "rb") as f:  # 必须二进制读取
            while chunk := f.read(chunk_size):
                md5_obj.update(chunk)

            """
            chunk = f.read(chunk_size)
            while chunk:
                md5_obj.update(chunk)
                chunk = f.read(chunk_size)
            """

            md5_hex = md5_obj.hexdigest()
            return md5_hex
    except Exception as e:
        logger.error(f"计算文件{filepath}md5失败，{str(e)}")
        return None


def listdir_with_allowed_type(path: str, allowed_types: tuple[str]):
    files = []

    if not os.path.isdir(path):
        logger.error(f"[listdir_with_allowed_type]{path}不是文件夹")
        return allowed_types

    for f in os.listdir(path):
        if f.endswith(allowed_types):
            files.append(os.path.join(path, f))

    return tuple(files)


def pdf_loader(path: str, password: str | None = None) -> list[Document]:
    """提取 PDF 文本，每页返回一个文档；page 从 0 开始，不包含 OCR。"""
    with open(path, "rb") as f:
        reader = PdfReader(f, password=password)
        total_pages = len(reader.pages)
        return [
            Document(
                page_content=page.extract_text() or "",
                metadata={
                    "source": str(path),
                    "page": page_number,
                    "total_pages": total_pages,
                },
            )
            for page_number, page in enumerate(reader.pages)
        ]


def text_loader(path: str, encoding: str = "utf-8-sig") -> list[Document]:
    """读取整个文本文件，默认兼容带 BOM 的 UTF-8；读取失败时抛出异常。"""
    with open(path, "r", encoding=encoding) as f:
        return [
            Document(
                page_content=f.read(),
                metadata={"source": str(path)},
            )
        ]
