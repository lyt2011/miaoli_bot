from typing	import Any, Dict, List, NotRequired, TypedDict, Optional

from langchain_core.language_models	import BaseChatModel
from langchain_core.tools			import BaseTool


class GraphRuntimeContext(TypedDict):
	
	tools	: List[BaseTool]
	client	: NotRequired[Optional[BaseChatModel]]	# build_client 运行时写入
	event	: NotRequired[Any]
	
	custom_status	: NotRequired[List[Any]]
	custom_mapping	: NotRequired[Dict[str, Any]]