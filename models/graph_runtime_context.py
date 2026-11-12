from langchain_core.language_models	import BaseChatModel

from ..core	import ToolSurface

from typing	import Any, Dict, List, NotRequired, TypedDict, Optional


class GraphRuntimeContext(TypedDict):
	
	tool_surface: ToolSurface
	client		: NotRequired[Optional[BaseChatModel]]	# build_client 运行时写入
	
	custom_status	: NotRequired[List[Any]]
	custom_mapping	: NotRequired[Dict[str, Any]]
