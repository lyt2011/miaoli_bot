from typing	import List, TypedDict

from langchain_core.language_models	import BaseChatModel
from langchain_core.tools			import BaseTool

from .config	import PluginConfig


class GraphRuntimeContext(TypedDict):
	plugin_config	: PluginConfig
	chat_model		: BaseChatModel
	tools			: List[BaseTool]