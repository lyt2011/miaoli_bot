from miaoli_bot.models	import GraphRuntimeContext, GraphState
from miaoli_bot.consts	import ON_TURN_START

from miaoli_pipeline.actions	import Goto

from langgraph.runtime	import Runtime


async def on_after_compact(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Goto:
	return Goto(goto=ON_TURN_START)
