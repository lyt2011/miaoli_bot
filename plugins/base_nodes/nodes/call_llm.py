from miaoli_bot	import GraphRuntimeContext, GraphState
from typing		import Dict, Any

from langgraph.runtime			import Runtime
from langchain_core.messages	import SystemMessage



async def call_llm(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:

	"""
	请求模型并追加回复
	压缩后的摘要已由 compact 写进 messages，这里无需再拼
	"""

	client		= runtime.context["client"].bind_tools(runtime.context["tools"])
	message		= [SystemMessage(state["system_prompt"]), *state["messages"]]
	AI_message	= await client.ainvoke(message)

	return {"messages": [AI_message]}