from miaoli_bot			import GraphRuntimeContext, GraphState
from miaoli_bot.core	import Goto
from miaoli_bot.consts	import ON_AGENT_END

from langgraph.runtime	import Runtime


async def on_turn_end(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Goto:
	return Goto(goto=ON_AGENT_END)
