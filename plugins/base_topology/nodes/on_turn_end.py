from langgraph.runtime	import Runtime

from miaoli_pipeline.actions	import Goto

from miaoli_bot.consts	import ON_AGENT_END
from miaoli_bot.models	import GraphRuntimeContext, GraphState


async def on_turn_end(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Goto:
	return Goto(goto=ON_AGENT_END)
