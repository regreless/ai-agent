import os
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder
import config.index as config
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnableLambda

# 创建大语言模型
llm = ChatOpenAI(
    model=config.model,
    api_key=os.environ.get(config.api_key),
    base_url=config.base_url,
    extra_body={"thinking": {"type": "disabled"}},
)

# 提示词模板
chat_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "你是目前市场上的面试人员,回答简单务实，不用长篇大论"),
    MessagesPlaceholder('history'),
    ("human", '现在的面试考察什么')
])

# json_parse 提示词必须按照要求返回
# first_prompt = PromptTemplate.from_template(
#     "现在的互联网赛道，{work}就业最吃香，封装成json，格式key是work,value是当前的行业"
# )

first_prompt = PromptTemplate.from_template(
    "现在的互联网赛道，{work}就业最吃香,回答简洁务实"
)

second_prompt = PromptTemplate.from_template(
    "解释下{work}就业为什么吃香，回答简洁务实"
)

# 创建解析器
str_parse = StrOutputParser()
json_parse = JsonOutputParser()

messages = [
    ("human", '学习6年的前端市场没课，考虑转型，离职了可以考虑哪个方向'),
    ("ai", "目前主要看各方面的能力，逻辑思维，业务判断，编码能力"),
    ("human", '目前开始接触大模型应用开发，做一个多边形展战士'),
    ("ai", "除去学历背景，企业真正需要的是解决问题的能力")
]

# AiMessage -> dict
runnable = RunnableLambda(lambda ai_msg: {"work": ai_msg.content})

def my_func(msg):
    return {"work": msg.content}

# json_parse解析器的实际应用
# chain = first_prompt | llm | json_parse | second_prompt | llm | str_parse

# 自定义解析器
chain = first_prompt | llm | runnable | second_prompt | llm | str_parse

res = chain.stream({"work": "大模型应用开发"})
for chunk in res:
    print(chunk, end="")

# 一次输出
# chain = chat_prompt_template | llm
# res = chain.invoke({"history": messages})
# print(res.content)

# stream输出
# chain = chat_prompt_template | llm
# res = chain.stream({"history": messages})
# for chunk in res:
#     print(chunk.content, end='')
