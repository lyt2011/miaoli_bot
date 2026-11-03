from langgraph.runtime	import Runtime

from miaoli_bot.core	import Goto
from miaoli_bot.consts	import ON_BEFORE_COMPACT
from miaoli_bot.models	import GraphRuntimeContext, GraphState


async def on_turn_start(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Goto:
	return Goto(goto=ON_BEFORE_COMPACT)
