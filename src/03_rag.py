import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

import config.index as config

#  rag 检索 增强 生成

prompt = ChatPromptTemplate.from_messages([
    ("system", "以提供参考资料为主,回答简洁,参考资料{content}"),
    ("human", '用户提问{input}')
])

model = ChatOpenAI(
    model=config.model,
    api_key=os.environ.get(config.api_key),
    base_url=config.base_url,
    extra_body={"thinking": {"type": "disabled"}},
)

embeddings = OpenAIEmbeddings(
    model=config.zp_model,  # 保持与你现有向量库使用的模型一致
    api_key=config.zp_api_key,
    base_url=config.zp_base_url,
    check_embedding_ctx_length=False,
    model_kwargs={"encoding_format": "float"},
    chunk_size=1,
)

vector_store = InMemoryVectorStore(
    embedding=embeddings
)

vector_store.add_texts([
    "每天早晨六点去公园跑步五公里",
    "周末去图书馆看历史类和科幻类书籍",
    "用单反相机拍摄城市夜景和星空",
    "学习弹奏古典吉他练习阿尔罕布拉宫的回忆",
    "每周三晚上参加羽毛球俱乐部双打比赛",
    "自己动手做欧式面包和法式甜点",
    "在河边骑行三十公里欣赏沿途风景",
    "收集世界各地的邮票和钱币",
    "用 Python 编写自动化脚本处理日常工作",
    "去不同城市品尝当地特色小吃和美食"
])

input_text = '哪个活动适合在家里完成'

result = vector_store.similarity_search(
    query=input_text,
    k=2
)
reference_text = '['

for doc in result:
    reference_text += doc.page_content + ','
reference_text += ']'
print(reference_text)

chain = prompt | model | StrOutputParser()
res = chain.invoke({"input": input_text, "content": reference_text})
print(res)
