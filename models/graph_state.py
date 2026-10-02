from typing						import Annotated, Any, Dict, List, TypedDict
from langgraph.graph.message	import add_messages


class GraphState(TypedDict):
	
	messages: Annotated[list, add_messages]
	
	event	: Dict[str, Any]
	segments: List[Dict[str, Any]]
	
	provider_name	: str
	model_name		: str

	final_answer	: str
	system_prompt	: str
