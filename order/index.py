from datetime import datetime, timedelta

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver

SYSTEM_PROMPT = """你是极速购电商客服，使用中文，回答简洁务实。
1. 用户明确要求下单后，从上下文获取商品、数量和姓名，只询问缺失信息；补充后继续下单。
2. 信息齐全后，先调用 check_goods_list 确认库存足够，再调用 create_order，只传商品和数量。
3. 新订单号由 create_order 自动生成，禁止向用户索要或自行编造，必须原样引用工具返回的 order_id。
4. 查询订单号或状态调用 order_status；不知道订单号时不传ID，查询最近一单。
5. 退款调用 withdraw_order，传入订单号和退款原因。
6. 以工具结果为准，失败就如实告知；未成功创建订单前，不得声称已提交或创建成功。
"""

# 用于查看会话记录，实际历史由 InMemorySaver 管理，重新运行后清空。
history_data = []

# 当前进程创建的订单，程序退出后清空。
order_data = {}

goods = {
    'iPhone_18': {"stock": 10, "price": 7999, "category": '手机'},
    'iPhone_18_pro': {"stock": 10, "price": 9999, "category": '手机'},
    'MacBook_Pro': {"stock": 5, "price": 19999, "category": '电脑'},
    'AirPods_Pro': {"stock": 20, "price": 1249, "category": '电脑'},
    'Nike_Air_Max': {"stock": 15, "price": 149, "category": '衣服'},
    'Adidas_Ultraboost': {"stock": 0, "price": 180, "category": '衣服'}
}


@tool(description="按商品名称查询库存和价格")
def check_goods_list(product_name: str):
    product = goods.get(product_name)
    if product is None:
        return f"{product_name}不存在"
    if product["stock"] == 0:
        return f"{product_name}库存暂时没有"
    return product


@tool(description="创建新订单，只需商品名称 product_name 和数量 product_count。工具自动生成并返回 order_id，不接受订单号参数，不能要求用户提供新订单号。")
def create_order(product_name: str, product_count: int):
    product = goods.get(product_name)
    if product is None:
        return f"{product_name}不存在"
    if type(product_count) is not int or product_count <= 0:
        return "商品数量必须是正整数"
    if product_count > product["stock"]:
        return f"{product_name}库存不足，剩余{product['stock']}件"
    order_time = datetime.now()
    order_id = order_time.strftime('%Y%m%d%H%M%S%f')
    while order_id in order_data:
        order_time += timedelta(microseconds=1)
        order_id = order_time.strftime('%Y%m%d%H%M%S%f')
    order_data[order_id] = {
        'order_id': order_id,
        'product_name': product_name,
        'product_count': product_count,
        'total_price': product['price'] * product_count,
        'status': '待支付',
    }
    product['stock'] -= product_count
    return {'success': True, 'order': dict(order_data[order_id])}


@tool(description="查询当前进程的订单。提供订单ID则查询指定订单；不传ID则查询最近创建的订单，可用于回答刚才的订单号是多少。")
def order_status(order_id: str = ''):
    if not order_data:
        return {'success': False, 'message': '暂无已创建的订单'}
    if not order_id:
        order_id = next(reversed(order_data))
    if order_id not in order_data:
        return {'success': False, 'message': f'订单{order_id}不存在'}
    return {'success': True, 'order': dict(order_data[order_id])}


@tool(description="退款")
def withdraw_order(order_id: str, reason: str):
    if order_id not in order_data:
        return f"订单{order_id}不存在"
    return f"退款的订单id{order_id},理由{reason}"


def main():
    agent = create_agent(
        model=ChatOllama(
            model="qwen3.5:0.8b",
            base_url="http://localhost:11434",
            reasoning=False,
        ),
        tools=[check_goods_list, create_order, order_status, withdraw_order],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )
    thread_config = {"configurable": {"thread_id": "1"}}

    # 多轮对话复用同一个 agent 和 thread_config。
    print("输入 exit 或 quit 退出，程序退出后会话记录清空。")
    while True:
        try:
            user_message = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_message.lower() in ('exit', 'quit'):
            break
        if not user_message:
            continue
        # 每轮只传新消息，InMemorySaver 自动加载同一会话的历史。
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config=thread_config,
        )
        history_data[:] = result['messages']
        print(f"助手：{history_data[-1].content}")


if __name__ == '__main__':
    main()
