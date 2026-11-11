from langgraph.graph.message	import add_messages

from ..core	import UntrackedSectionPatch

from typing	import Annotated, Dict, TypedDict


class GraphState(TypedDict):
	
	messages	: Annotated[list, add_messages]
	prompts		: Annotated[Dict[str, str], UntrackedSectionPatch]
	
