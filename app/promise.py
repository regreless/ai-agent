"""async / await / yield 常用场景。

运行：uv run python promise.py
示例用 asyncio.sleep 模拟网络等待，无需安装额外依赖。
"""

import asyncio


# 场景 1：请求接口、查询数据库，等待结果后继续处理。
# async 定义异步函数，await 等待结果。
async def fetch_user(user_id: int) -> dict:
    await asyncio.sleep(0.1)
    return {"user_id": user_id, "user_name": f"用户_{user_id}"}


async def show_await_example():
    print("\n1. 顺序请求：查完第一个，再查第二个")
    first_user = await fetch_user(1)
    second_user = await fetch_user(2)
    print(first_user, second_user)


# 场景 2：多个请求互不依赖时，用 gather 并发执行。
async def show_gather_example():
    print("\n2. 并发请求：同时查询多个用户")
    user_list = await asyncio.gather(fetch_user(1), fetch_user(2))
    print(user_list)


# 场景 3：批量处理数据，每次取一批。
# yield 返回一批后暂停，下次迭代继续；它本身不代表异步。
def generate_batches(user_ids: list[int]):
    for start_index in range(0, len(user_ids), 2):
        yield user_ids[start_index:start_index + 2]


def show_yield_example():
    print("\n3. 分批处理：每次处理两个用户")
    for batch_data in generate_batches([1, 2, 3, 4, 5]):
        print("当前批次：", batch_data)


# 场景 4：AI 流式回答，每收到一段就展示一段。
# async + yield 定义异步生成器，用 async for 逐段读取。
async def stream_answer():
    for text_chunk in ["你好，", "这是一个", "流式回答。"]:
        await asyncio.sleep(0.1)
        yield text_chunk


async def show_stream_example():
    print("\n4. 流式输出：逐段显示回答")
    async for text_chunk in stream_answer():
        print(text_chunk, end="", flush=True)
    print()


async def main():
    await show_await_example()
    await show_gather_example()
    show_yield_example()
    await show_stream_example()


if __name__ == "__main__":
    # 启动异步程序。
    asyncio.run(main())
