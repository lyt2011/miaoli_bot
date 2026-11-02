from langgraph.channels			import UntrackedValue
from langgraph.graph.message	import add_messages

from miaoli_pipeline.channels	import SectionPatch

from typing	import Annotated, Any, Dict, TypedDict


class GraphState(TypedDict):
	
	event	: Annotated[Dict[str, Any], UntrackedValue]
	messages: Annotated[list, add_messages]
	prompts	: Annotated[Dict[str, str], SectionPatch]
	
	final_answer: Annotated[str, UntrackedValue]
