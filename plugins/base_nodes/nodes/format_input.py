from miaoli_bot	import GraphRuntimeContext, GraphState
from typing		import Dict, Any

from langgraph.runtime			import Runtime
from langchain_core.messages	import HumanMessage

import json


async def format_input(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:

	"""把 event 与 segments 打包成一条 HumanMessage"""

	human_message = json.dumps({
		"event"		: state["event"],
		"segments"	: state["segments"]
	}, indent=2, ensure_ascii=False)

	return {"messages": [HumanMessage(human_message)]}
