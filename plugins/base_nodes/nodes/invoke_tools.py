from langgraph.runtime	import Runtime
from langgraph.prebuilt	import ToolNode

from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing	import Dict, Any, Optional


async def invoke_tools(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	return await ToolNode(runtime.context["tool_surface"].tools).ainvoke({"messages": state["messages"]})
