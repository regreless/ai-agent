from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="qwen3.5:0.8b",
    temperature=0.3,
    base_url="http://localhost:11434",
    reasoning=False,
    keep_alive="30m",
    num_predict=512,
)