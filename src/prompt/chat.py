from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

import os
from langchain_openai import ChatOpenAI
import config.index as config

llm = ChatOpenAI(
    model=config.model,
    api_key=os.environ.get(config.api_key),
    base_url=config.base_url,
    extra_body={"thinking": {"type": "disabled"}},
)

chat_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "你是目前市场上的面试人员,回答简单务实，不用长篇大论"),
    MessagesPlaceholder('history'),
    ("human", '现在的面试考察什么')
])

history_data = [
    ("human", '学习6年的前端现在技术栈锁紧，提前离职准备了'),
    ("ai", "目前主要看各方面的能力，逻辑思维，业务判断，编码能力"),
    ("human", '目前开始接触大模型应用开发，做一个多边形展战士'),
    ("ai", "除去学历背景，企业真正需要的是解决问题的能力")
]

prompt_text = chat_prompt_template.invoke({"history": history_data}).to_string()


res = llm.invoke(prompt_text)
print(res.content)