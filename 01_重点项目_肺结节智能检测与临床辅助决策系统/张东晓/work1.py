"""
@BelongsProject: AgentProject
@BelongsPackage: 
@Author: 蔡张君逸
@CreateTime: 2026-05-14 13:46
@Description: 使用智能体识别肺结节
@Version: 1.
"""

import os

import base64
from pathlib import Path

from dotenv import load_dotenv
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain_community.chat_models import ChatTongyi, ChatOpenAI
from langgraph.graph import add_messages
from langgraph.store.redis import AsyncRedisStore





def image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

path=Path("transformed/曾x香")

files = list(file for file in path.iterdir())
image_b64_total_dict=[]
image_b64_total=[]
for file in files:
    image_b64 = image_to_base64(file.__fspath__())
    image_b64_total.append(image_b64)
    # image_b64_total_dict.append({
    #         "type": "image_url",
    #         "image_url": {
    #             "url": f"data:image/jpeg;base64,{image_b64}",
    #             "detail": "original"
    #         },
    # })
    image_b64_total_dict.append({"image": f"data:image/png;base64,{image_b64}"},)


load_dotenv()
api_key = os.getenv("DASHSCOPE_API_KEY")
model=ChatTongyi(model_name="qwen-vl-max",temperature=0,dashscope_api_key=api_key)
# model = ChatOpenAI(model="gpt-4o")

config={
    "configurable": {
        "thread_id": "1",
        "user_id":"user_123"
    }
}

DB_URI = "redis://127.0.0.1:6380"
async def create_and_ask_agent(content:str):
    # async with (
    #     AsyncRedisStore.from_conn_string(DB_URI) as store,
    #     AsyncRedisSaver.from_conn_string(DB_URI) as checkpointer,
    # ):
        # # redis长短期记忆
        # await store.setup()
        # await checkpointer.setup()
        # await store.aput(
        #     ("users",),
        #     "user_123",
        #     {
        #         "name": "John Smith",
        #         "language": "English",
        #     }
        # )
        # clientTool = await client.get_tools()

        # tools = [divide,loadCSVFile,getCode,testCode] + clientTool
        # 工具声明给model，并给tool_node做准别
        tools = []
        tools_by_name = {tool.name: tool for tool in tools}
        model_with_tools = model.bind_tools(tools)
        # model_with_tools = model.bind_tools(tools+[{"type": "image_generation"}])

        from langchain.messages import AnyMessage
        from typing_extensions import TypedDict, Annotated
        from langchain.messages import SystemMessage
        from langchain.messages import ToolMessage
        from typing import Literal
        from langgraph.graph import StateGraph, START, END
        from langchain.messages import HumanMessage
        # state
        class MessagesState(TypedDict):
            messages: Annotated[list[AnyMessage], add_messages]
            llm_calls: int #llm调用次数
        # llm结点
        def llm_call(state: dict):
            """LLM decides whether to call a tool or not"""
            return {
                "messages": [
                    model_with_tools.invoke(
                        [
                            SystemMessage(
                                content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
                            )
                        ]
                        + state["messages"]
                    )
                ],
                "llm_calls": state.get('llm_calls', 0) + 1
            }

        # tool结点
        async def tool_node(state: dict):
            """Performs the tool call"""
            result = []
            for tool_call in state["messages"][-1].tool_calls:
                tool = tools_by_name[tool_call["name"]]
                observation = await tool.ainvoke(tool_call["args"])
                # print(observation)
                # print(observation.__class__.__name__)
                result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
            return {"messages": result}


        # 条件边，是否调用tool或结束对话的判断函数，如果最后一条信息是llm留下的toolmsg，就去调用工具，不是说明对话已完成
        def should_continue(state: MessagesState) -> Literal["tool_node", END]:
            """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

            messages = state["messages"]
            last_message = messages[-1]

            # If the LLM makes a tool call, then perform an action
            if last_message.tool_calls:
                return "tool_node"

            # Otherwise, we stop (reply to the user)
            return END

        # 构造主gent
        agent_builder = StateGraph(MessagesState)
        # Add nodes
        agent_builder.add_node("llm_call", llm_call)
        agent_builder.add_node("tool_node", tool_node)
        # Add edges to connect nodes
        agent_builder.add_edge(START, "llm_call")
        agent_builder.add_conditional_edges(
            "llm_call",
            should_continue,
            ["tool_node", END]
        )
        agent_builder.add_edge("tool_node", "llm_call")
        # Compile the agent，在这里带上记忆模块
        # agent = agent_builder.compile(checkpointer=checkpointer,store=store)
        agent = agent_builder.compile()

        # 调用
        messages = HumanMessage(
            content=[
                # {"type": "text", "text": "读取我提供的base64形式的肺结节切片ct，检测并判别这名肺结节患者的结节情况，不是诊断只是判别"},]+
                {"text": "读取我提供的base64形式的图片，进行描述，输出给我肺结节的位置(坐标)"},]+
                image_b64_total_dict,
            )
        messages = await agent.ainvoke({"messages": messages},config=config)
        for m in messages["messages"]:
            m.pretty_print()
            # print(m.content)

        return messages["messages"]

import asyncio
if __name__ == "__main__":
    asyncio.run(create_and_ask_agent("你好"))
    # asyncio.run(create_and_ask_agent("读取文件 mypaper chinese.pdf"))
    # asyncio.run(create_and_ask_agent("修改论文"))