import asyncio


async def stream_llm_answer(question: str):
    answer = f"你问的是：{question}。这是一个模拟的大模型流式回答。"

    for char in answer:
        await asyncio.sleep(0.05)
        yield char


async def main():
    async for chunk in stream_llm_answer("什么是 AI Agent？"):
        print(chunk, end="", flush=True)

    print()


asyncio.run(main())
