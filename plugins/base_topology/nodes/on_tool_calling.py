from miaoli_bot			import GraphRuntimeContext, GraphState
from miaoli_bot.core	import Goto
from miaoli_bot.consts	import ON_TURN_START

from langgraph.runtime	import Runtime


async def on_tool_calling(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Goto:
	return Goto(goto=ON_TURN_START)
