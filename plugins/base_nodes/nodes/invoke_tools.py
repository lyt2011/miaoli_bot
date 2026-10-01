from miaoli_bot	import GraphRuntimeContext, GraphState
from typing		import Dict, Any, Optional

from langgraph.runtime	import Runtime
from langgraph.prebuilt	import ToolNode


async def invoke_tools(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	return await ToolNode(runtime.context["tools"]).ainvoke({"messages": state["messages"]})