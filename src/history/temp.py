import os

from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_openai import ChatOpenAI
import config.index as config

model = ChatOpenAI(
    model=config.model,
    api_key=os.environ.get(config.api_key),
    base_url=config.base_url,
    extra_body={"thinking": {"type": "disabled"}},
)

# prompt = PromptTemplate.from_template(
#     "根据当前的历史会话，对话历史{chat_history}，用户提问{input}，回答问题"
# )

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "根据当前的历史会话,回答问题"),
        MessagesPlaceholder("chat_history"),
        ("human","请回答下面的问题，{input}")
    ]

)

# 存储session_id的历史记录
store = {}
str_parser = StrOutputParser()
base_chain = prompt | model | str_parser


def get_history(session_id):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]


# 创建新链 附加历史功能
conversion_chain = RunnableWithMessageHistory(
    base_chain,
    get_history,  # 通过会话id获取InMemoryChatMessageHistory
    input_messages_key="input",
    history_messages_key="chat_history",
)

if __name__ == '__main__':
    session_config = {
        "configurable": {
            "session_id": "user_007"
        }
    }
    res = conversion_chain.invoke({"input": "小明有一只猫"}, session_config)
    print("第1次", res)
    res = conversion_chain.invoke({"input": "小明有两只狗"}, session_config)
    print("第2次", res)
    res = conversion_chain.invoke({"input": "小明一共有几个宠物"}, session_config)
    print("第3次", res)
