from langchain_core.vectorstores import InMemoryVectorStore
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import config.index as config
from utils import load_documents

embeddings = OpenAIEmbeddings(
    model=config.zp_model,  # 保持与你现有向量库使用的模型一致
    api_key=config.zp_api_key,
    base_url=config.zp_base_url,
    check_embedding_ctx_length=False,
    model_kwargs={"encoding_format": "float"},
    chunk_size=1,
)

documents = load_documents(
    file_path='../data/mock.csv'
)

# vector_store = InMemoryVectorStore(
#     embedding=embeddings
# )

vector_store = Chroma(
    collection_name='vector',
    embedding_function=embeddings,
    persist_directory='./chroma_db'
)

vector_store.add_documents(
    documents=documents,
    ids=[f"id{i}" for i in range(1, len(documents) + 1)]
)

vector_store.delete(['id1'])

res = vector_store.similarity_search(
    query="笔记本电脑",
    k=2
)

print(res)
