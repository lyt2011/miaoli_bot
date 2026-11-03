from langgraph.runtime	import Runtime

from miaoli_bot.core	import Goto
from miaoli_bot.consts	import ON_AFTER_REQUEST
from miaoli_bot.models	import GraphRuntimeContext, GraphState


async def on_request(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Goto:
	return Goto(goto=ON_AFTER_REQUEST)
