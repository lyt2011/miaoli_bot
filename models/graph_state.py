from typing						import Annotated, Any, Dict, List, TypedDict
from langgraph.graph.message	import add_messages
from langgraph.channels			import UntrackedValue


class GraphState(TypedDict):
	
	messages: Annotated[list, add_messages]
	
	system_prompt	: Annotated[str, UntrackedValue]
	event			: Annotated[Dict[str, Any], UntrackedValue]
	segments		: Annotated[List[Dict[str, Any]], UntrackedValue]
	
	provider_name	: Annotated[str, UntrackedValue]
	model_name		: Annotated[str, UntrackedValue]
	
	final_answer	: Annotated[str, UntrackedValue]
