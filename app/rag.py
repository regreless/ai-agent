from uuid import uuid4

from langchain_core.messages import SystemMessage

from file_history_store import create_chat, get_history
from vector_stores import VectorStoreService
from utils.index import model

class RagService:
    def __init__(self, session_id=None):
        self.session_id = session_id or str(uuid4())
        self.retriever = VectorStoreService().get_retriever()
        self.chat_model = model

    def get_history(self):
        """将 LangChain 消息转换成页面使用的 user/ai 消息。"""
        roles = {"human": "user", "ai": "ai"}
        return [
            {"role": roles[msg.type], "content": msg.text}
            for msg in get_history(self.session_id)
            if msg.type in roles
        ]

    def invoke(self, input: str) -> str:
        """传入问题，返回回答；同一实例自动延续历史。"""
        with create_chat(self.reply) as chat:
            return chat(input, self.session_id)

    def stream(self, input: str):
        """逐段返回回答；消费完迭代器后，本轮完整回答保存到历史。"""
        with create_chat(self.reply, stream=True) as chat:
            yield from chat(input, self.session_id)

    def reply(self, messages):
        """接收历史和本轮问题，检索资料后返回 AIMessage。"""
        docs = self.retriever.invoke(messages[-1].text)
        context = "\n\n".join(
            f"文档片段:{doc.page_content}\n文档元数据:{doc.metadata}"
            for doc in docs
        ) or "暂无相关资料"

        system = SystemMessage(content=f"以提供参考资料为主,回答简洁,不要长篇大论,参考资料{context}")
        return self.chat_model.invoke([system, *messages])


if __name__ == "__main__":
    rag = RagService(session_id="clothing_demo")
    print(rag.invoke(input="体重60kg,身高170,只要夏天穿衣推荐,回答简洁,直接告诉我一个最合适的选择"))
