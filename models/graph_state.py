from langgraph.channels			import UntrackedValue
from langgraph.graph.message	import add_messages

from ..core	import SectionPatch

from typing	import Annotated, Dict, TypedDict


class GraphState(TypedDict):
	
	raw_input	: Annotated[str, UntrackedValue]
	messages	: Annotated[list, add_messages]
	prompts		: Annotated[Dict[str, str], SectionPatch]
	
