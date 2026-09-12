import datetime
import os
import hashlib

from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config_data as config
from utils.index import embeddings


def check_md5(md5_str):
    if not os.path.exists(config.md5_path):
        open(config.md5_path, 'w', encoding="utf-8").close()
        return False
    else:
        for line in open(config.md5_path, 'r', encoding="utf-8").readlines():
            line = line.strip()
            if line == md5_str:
                return True
        return False


def save_md5(md5_str):
    with open(config.md5_path, 'a', encoding="utf-8") as f:
        f.write(md5_str + '\n')


def get_string_md5(input_str, encoding="utf-8"):
    # 1. 将字符串转换为字节
    str_bytes = input_str.encode(encoding)

    # 2. 创建 MD5 计算对象
    md5_obj = hashlib.md5()

    # 3. 传入要计算的内容
    md5_obj.update(str_bytes)

    # 4. 得到 32 位十六进制字符串
    md5_hex = md5_obj.hexdigest()
    return md5_hex


class KnowledgeBaseService():
    def __init__(self):
        # 文件及不存在就创建 有就跳过
        os.makedirs(config.persist_directory, exist_ok=True)

        self.chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function=embeddings,
            persist_directory=config.persist_directory,
        )

        # 文本分割器
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,  # 连续文本段之间字符重叠数量
            separators=config.separators,
            length_function=len
        )

    def upload_by_str(self, data, file_name):
        # 将传入的str -> 向量化 -> 数据库
        md5_hex = get_string_md5(data)
        if check_md5(md5_hex):
            return "[跳过]内容已经存在知识库"
        if len(data) > config.max_split_char_number:
            knowledge_chunk: list[str] = self.spliter.split_text(data)
        else:
            knowledge_chunk = [data]

        metadata = {
            "source": file_name,
            "create_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operator": "小北"
        }

        self.chroma.add_texts(
            knowledge_chunk,
            metadatas=[metadata for _ in knowledge_chunk]
        )

        save_md5(md5_hex)

        return "内容上传成功,载入向量库"


if __name__ == '__main__':
    service = KnowledgeBaseService()
    r = service.upload_by_str('周杰伦', 'test_file')
    print(r)
