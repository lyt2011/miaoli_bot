from miaoli_bot.models	import GraphRuntimeContext, GraphState
from typing				import Dict, Any

from langgraph.runtime			import Runtime



async def call_llm(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:

	"""
	请求模型并追加回复
	压缩后的摘要已由 context_compactor 写进 messages，这里无需再拼
	"""
	
	messages	= state["messages"]
	client		= runtime.context["client"].bind_tools(runtime.context["tools"])
	assistant	= await client.ainvoke(messages)

	return {"messages": [assistant]}
