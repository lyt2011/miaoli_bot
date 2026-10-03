from miaoli_bot			import GraphRuntimeContext, GraphState
from miaoli_bot.core	import Goto
from miaoli_bot.consts	import ON_BEFORE_REQUEST

from langgraph.runtime	import Runtime


async def on_turn_start(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Goto:
	return Goto(goto=ON_BEFORE_REQUEST)
