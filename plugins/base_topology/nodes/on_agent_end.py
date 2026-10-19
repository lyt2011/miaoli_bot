from miaoli_bot.models	import GraphRuntimeContext, GraphState
from miaoli_pipeline.actions	import Goto

from langgraph.graph	import END
from langgraph.runtime	import Runtime


async def on_agent_end(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Goto:
	
	"""END 会被 langgraph 过滤掉 于是没有下一跳 图就此结束"""
	
	return Goto(goto=END)
