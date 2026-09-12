from abc import ABC, abstractmethod
import os

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from agent.utils.config_handler import rag_conf


class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Embeddings | BaseChatModel:
        pass


class ChatModelFactory(BaseModelFactory):
    def generator(self) -> BaseChatModel:
        return ChatOpenAI(
            model=rag_conf.chat_model_name,
            api_key=os.environ.get(rag_conf.chat_api_key),
            base_url=rag_conf.chat_base_url,
            extra_body={"thinking": {"type": "disabled"}},
        )


class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Embeddings:
        return OpenAIEmbeddings(
            model=rag_conf["embedding_model_name"],
            api_key=os.environ.get(rag_conf.embedding_api_key),
            base_url=rag_conf.embedding_base_url,
            check_embedding_ctx_length=False,
            model_kwargs={"encoding_format": "float"},
            chunk_size=64,
        )


chat_model = ChatModelFactory().generator()

embed_model = EmbeddingsFactory().generator()
