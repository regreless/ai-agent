import asyncio
import time


async def query_llm():
    print("开始调用大模型")
    await asyncio.sleep(2)
    print("大模型返回结果")
    return "AI 回答"


async def query_user():
    print("开始查询用户")
    await asyncio.sleep(1)
    print("用户查询完成")
    return "用户信息"


async def main():
    start = time.perf_counter()
    llm_task = asyncio.create_task(query_llm())
    user = await query_user()
    answer = await llm_task
    end = time.perf_counter()

    print(user)
    print(answer)
    print(f"总耗时：{end - start:.2f} 秒")


asyncio.run(main())
