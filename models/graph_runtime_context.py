from typing	import List, TypedDict, Optional

from langchain_core.language_models	import BaseChatModel
from langchain_core.tools			import BaseTool


class GraphRuntimeContext(TypedDict):
	client	: Optional[BaseChatModel]
	tools	: List[BaseTool]