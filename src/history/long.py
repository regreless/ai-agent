import os, json
from typing import Sequence

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

import config.index as config
from langchain_core.messages import messages_to_dict, messages_from_dict, BaseMessage
from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory,
)

model = ChatOpenAI(
    model=config.model,
    api_key=os.environ.get(config.api_key),
    base_url=config.base_url,
    extra_body={"thinking": {"type": "disabled"}},
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "根据当前的历史会话,回答问题"),
        MessagesPlaceholder("chat_history"),
        ("human", "请回答下面的问题，{input}"),
    ]
)


class FileChatMessageHistory(BaseChatMessageHistory):

    def __init__(self, session_id, storage_path):
        self.session_id = session_id  # 会话id
        self.storage_path = storage_path  # 会话id存储文件所在的文件夹
        self.file_path = os.path.join(
            self.storage_path, self.session_id
        )  # 完整文件路径
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)  # 确保文件夹存在

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        """
         FIX: add_messages 接收消息序列；不能在 add_message 中对单个
         BaseMessage 使用 extend，否则会把它展开成字段 tuple，导致
         message_to_dict 报 "'tuple' object has no attribute type
        :param messages:
        :return: None
        """
        all_messages = list(self.messages)  # 已有消息列表
        all_messages.extend(messages)  # 融合成一个列表

        # 将数据同步写入本地文件中
        # 类写入文件 -> 二进制
        # 将BaseMessage -> dict,借助json -> json存储
        # FIX: messages_to_dict 将 BaseMessage 序列转换成可 JSON 存储的字典列表

        new_messages = messages_to_dict(all_messages)

        # 将数据写入文件
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(new_messages, f, ensure_ascii=False, indent=4)

    def add_message(self, message: BaseMessage) -> None:
        # FIX: 保留标准的单条消息接口，并包装成列表交给批量写入方法。
        self.add_messages([message])

    @property  # 将message方法变成成员属性使用
    def messages(self) -> Sequence[BaseMessage]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                messages_data = json.load(f)  # list[dict]
                return messages_from_dict(messages_data)  # list[AIMessage]
        except FileNotFoundError:
            return []

    def clear(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)


str_parser = StrOutputParser()
base_chain = prompt | model | str_parser


def get_history(session_id):
    return FileChatMessageHistory(session_id, "./chat_history")


# 创建新链 附加历史功能
conversion_chain = RunnableWithMessageHistory(
    base_chain,
    get_history,  # 通过会话id获取InMemoryChatMessageHistory
    input_messages_key="input",
    history_messages_key="chat_history",
)

if __name__ == "__main__":
    session_config = {"configurable": {"session_id": "user_007"}}
    # res = conversion_chain.invoke({"input": "小明有一只猫"}, session_config)
    # print("第1次", res)
    # res = conversion_chain.invoke({"input": "小明有两只狗"}, session_config)
    # print("第2次", res)
    res = conversion_chain.invoke({"input": "小明一共有几个宠物"}, session_config)
    print("第3次", res)
