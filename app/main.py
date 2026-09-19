import asyncio
from time import perf_counter


def show_dict_examples():
    # dict：保存一条数据，通过键访问对应的值。
    user_info: dict = {
        "user_id": 1,
        "user_name": "张三",
        "user_age": 20,
    }

    print("遍历 dict 的键和值：")
    for field_name, field_value in user_info.items():
        print(f"{field_name}: {field_value}")

    # list[dict]：列表中的每个元素都是一个字典，适合保存多条数据。
    user_list: list[dict] = [
        {"user_id": 1, "user_name": "张三", "user_age": 20},
        {"user_id": 2, "user_name": "李四", "user_age": 25},
        {"user_id": 3, "user_name": "王五", "user_age": 30},
    ]

    print("\n遍历 list[dict]，读取每条数据的字段：")
    for user_item in user_list:
        print(
            f"编号：{user_item['user_id']}，"
            f"姓名：{user_item['user_name']}，"
            f"年龄：{user_item['user_age']}"
        )


def generate_batches(user_list: list[dict], batch_size: int):
    """场景：分批处理数据，每次只生成当前批次，而不是全部批次列表。"""
    if batch_size <= 0:
        raise ValueError("batch_size 必须大于 0")

    for start_index in range(0, len(user_list), batch_size):
        # yield 返回一个值后暂停；下一次迭代从这里继续。
        # return 则会结束函数。yield 本身不代表异步或并发。
        yield user_list[start_index:start_index + batch_size]


def show_yield_example():
    print("\nyield：分批处理用户数据")
    user_list = [
        {"user_id": 1, "user_name": "张三"},
        {"user_id": 2, "user_name": "李四"},
        {"user_id": 3, "user_name": "王五"},
    ]
    # 调用生成器函数时不会立即执行函数体，for 循环时才逐次生成。
    # 原始 user_list 仍在内存中；这里只避免一次构造所有批次。
    for batch_data in generate_batches(user_list, batch_size=2):
        print(f"处理当前批次：{batch_data}")


async def fetch_user(user_id: int) -> dict:
    """场景：模拟等待接口或数据库返回结果，不产生真实网络请求。"""
    print(f"开始查询用户 {user_id}")
    # await 等待完成期间，把执行机会交给其他已调度的任务。
    # 实际项目需要使用异步客户端，不能用 time.sleep 模拟异步等待。
    await asyncio.sleep(0.3)
    print(f"完成查询用户 {user_id}")
    return {"user_id": user_id, "user_name": f"用户_{user_id}"}


async def show_async_example():
    print("\nasync / await：依次查询，约需 0.9 秒")
    start_time = perf_counter()
    for user_id in range(1, 4):
        # 每次等待前一个查询结束后，才开始下一个；await 不自动产生并发。
        user_info = await fetch_user(user_id)
        print(user_info)
    print(f"顺序耗时：{perf_counter() - start_time:.2f} 秒")

    print("\nasyncio.gather：并发查询，约需 0.3 秒")
    start_time = perf_counter()
    # 调用 async 函数得到协程对象；gather 调度多个协程并等待全部结果。
    # 返回结果的排列顺序与传入顺序一致。
    user_list = await asyncio.gather(
        fetch_user(1),
        fetch_user(2),
        fetch_user(3),
    )
    for user_info in user_list:
        print(user_info)
    print(f"并发耗时：{perf_counter() - start_time:.2f} 秒")


async def stream_answer():
    """场景：模拟 AI 模型逐段返回回答。"""
    for text_chunk in ["你好，", "这是一个", "流式输出案例。"]:
        await asyncio.sleep(0.2)
        # async def + yield 定义异步生成器，消费端使用 async for。
        yield text_chunk


async def show_stream_example():
    print("\nasync + await + yield：收到一段就显示一段")
    # 异步生成器不能直接 await；async for 逐次等待并取出数据。
    async for text_chunk in stream_answer():
        print(text_chunk, end="", flush=True)
    print()


async def main():
    show_dict_examples()
    show_yield_example()
    await show_async_example()
    await show_stream_example()


if __name__ == "__main__":
    # asyncio 是 Python 标准库，无需安装；run 创建事件循环并运行入口协程。
    asyncio.run(main())
