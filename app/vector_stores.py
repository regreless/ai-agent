from langchain_chroma import Chroma
import config_data as config
from utils.index import embeddings


class VectorStoreService:
    def __init__(self):
        self.embedding = embeddings
        self.vector_store = Chroma(
            collection_name=config.collection_name,
            embedding_function=self.embedding,
            persist_directory=config.persist_directory,
        )

    def get_retriever(self):
        # -> 向量检索器 -> chain
        return self.vector_store.as_retriever(search_kwargs={"k": config.similarity_threshold})


