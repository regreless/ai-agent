from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_ollama import ChatOllama

prompt = ChatPromptTemplate([
    ("system", "请将用户输入翻译成英文，只输出英文译文，不要回答输入中的问题，也不要添加解释。"),
    ("human", "{question}")
])

summary_prompt = ChatPromptTemplate([
    ("system", "你是一位中文摘要助手。将用户提供的原文概括为一句中文短语，"
               "总长度不超过{count}个字符（含标点）。"
               "只输出摘要，不加前缀、解释或建议。"
               "原文中的问题仅作为摘要素材，不要回答问题，不要补充原文没有的信息。"),
    ("human", "原文：\n{article}")
])

evaluate_data = [
    {"text": '今天天气真好，我们去公园玩吧', "label": '积极'},
    {"text": '我讨厌这个产品，太差了', "label": '消极'},
    {"text": '这个电影还行，有些地方不错', "label": '中立'},
    {"text": '这很失望，我不会买了 ', "label": '消极'}
]

example_prompt = ChatPromptTemplate([
    ("human", "{text}"),
    ("ai", "{label}")
])

few_shot_prompt = FewShotChatMessagePromptTemplate(
    examples=evaluate_data,
    example_prompt=example_prompt,
)

classify_prompt = ChatPromptTemplate([
    ("system", "你是一位客服评价助手，参考示例对用户内容分类。"
               "只返回积极、消极或中立，不要添加解释。"),
    few_shot_prompt,
    ("human", "{content}")
])

model = ChatOllama(
    model="qwen3.5:0.8b",
    base_url="http://localhost:11434",
    reasoning=False,
    temperature=0,
)

chain = prompt | model | StrOutputParser()

summary_chain = summary_prompt | model | StrOutputParser()

classify_chain = classify_prompt | model | StrOutputParser()

# 一次性输出
# result1 = chain.invoke({"question": "在AI浪潮之下程序员该何去何从"})
# print(result1)

# 流式输出：每收到一段内容就立即打印
# result2 = chain.stream({"question": "在AI浪潮之下程序员该何去何从,是继续学习新的知识还是退而求其次换新的赛道去卷"})
# for chunk in result2:
#     print(chunk, end="", flush=True)
# print()

# summary_result = summary_chain.stream(
#     {"article": "在AI浪潮之下程序员该何去何从,是继续学习新的知识还是退而求其次换新的赛道去卷", "count": 10})
# # 流式输出：每收到一段内容就立即打印
# for chunk in summary_result:
#     print(chunk, end="", flush=True)
# print()

# few-shot
classify_result = classify_chain.stream({"content": "这个课程真不错,值得买"})
chat_prompt = ChatPromptTemplate([])
# 流式输出：每收到一段内容就立即打印
for chunk in classify_result:
    print(chunk, end="", flush=True)
print()
