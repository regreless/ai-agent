import asyncio


async def query_user():
    print("开始查询用户信息")
    await asyncio.sleep(1)
    print("用户信息查询完成")
    return "用户信息"


async def main():
    result = await query_user()
    print(result)


asyncio.run(main())