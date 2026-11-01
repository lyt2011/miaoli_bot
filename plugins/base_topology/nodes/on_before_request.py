from langgraph.runtime	import Runtime

from miaoli_pipeline.actions	import Goto

from miaoli_bot.consts	import ON_REQUEST
from miaoli_bot.models	import GraphRuntimeContext, GraphState


async def on_before_request(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Goto:
	return Goto(goto=ON_REQUEST)
