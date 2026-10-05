from miaoli_bot			import GraphRuntimeContext, GraphState
from miaoli_bot.core	import Goto
from miaoli_bot.consts	import ON_AFTER_REQUEST

from langgraph.runtime	import Runtime


async def on_request(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Goto:
	return Goto(goto=ON_AFTER_REQUEST)
