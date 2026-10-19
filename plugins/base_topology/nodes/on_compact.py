from miaoli_bot.models	import GraphRuntimeContext, GraphState
from miaoli_pipeline.actions	import Goto
from miaoli_bot.consts	import ON_AFTER_COMPACT

from langgraph.runtime	import Runtime


async def on_compact(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Goto:
	return Goto(goto=ON_AFTER_COMPACT)
