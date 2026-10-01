from typing						import Annotated, Any, Dict, List, TypedDict
from langgraph.graph.message	import add_messages


class GraphState(TypedDict):
	
	event			: Dict[str, Any]
	segments		: List[Dict[str, Any]]
	messages		: Annotated[list, add_messages]

	final_answer	: str
	system_prompt	: str
