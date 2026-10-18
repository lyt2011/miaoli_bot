from typing						import Annotated, Any, Dict, TypedDict
from langgraph.graph.message	import add_messages
from langgraph.channels			import UntrackedValue


class GraphState(TypedDict):
	
	event			: Annotated[Dict[str, Any], UntrackedValue]
	messages		: Annotated[list, add_messages]
	system_prompt	: Annotated[str, UntrackedValue]
	
	model		: Annotated[str, UntrackedValue]
	base_url	: Annotated[str, UntrackedValue]
	api_key		: Annotated[str, UntrackedValue]
	max_tokens	: Annotated[int, UntrackedValue]
	
	final_answer	: Annotated[str, UntrackedValue]
