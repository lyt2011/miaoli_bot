from langgraph.channels			import UntrackedValue
from langgraph.graph.message	import add_messages

from ..core	import UntrackedSectionPatch

from typing	import Annotated, Dict, List, TypedDict, Union


class GraphState(TypedDict):
	
	# 服务于 langgraph
	messages: Annotated[list, add_messages]
	prompts	: Annotated[Dict[str, str], UntrackedSectionPatch]
	
	# 可替换的输入输出
	input	: Annotated[Union[str, List[dict]], UntrackedValue]
	output	: Annotated[Union[str, List[dict]], UntrackedValue]
	
