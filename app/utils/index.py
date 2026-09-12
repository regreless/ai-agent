"""集中创建聊天模型和向量模型，供 app 内各模块复用。"""

import os

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
import config_data as config

model = ChatOpenAI(
    model=config.model,
    api_key=os.environ.get(config.api_key),
    base_url=config.base_url,
    extra_body={"thinking": {"type": "disabled"}},
)

embeddings = OpenAIEmbeddings(
    model=config.zp_model,
    api_key=config.zp_api_key,
    base_url=config.zp_base_url,
    check_embedding_ctx_length=False,
    model_kwargs={"encoding_format": "float"},
    chunk_size=1,
)
