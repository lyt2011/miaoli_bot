from miaoli_bot.stores			import SHARE_STORE

from typing						import Any
from langchain_core.messages	import ToolMessage

from ..consts					import PLUGIN_CONFIG

def is_target_model(provider: str, model: str) -> bool:
	
	"""适配 <provider>/<model>与<model>"""
	
	plugin_config	= SHARE_STORE.recall(PLUGIN_CONFIG)
	
	if not plugin_config.models:
		return True
	
	pm_hit	= f"{provider}/{model}" in plugin_config.models
	m_hit	= f"{model}" in plugin_config.models
	
	return pm_hit or m_hit

def is_tool_message(message: ToolMessage) -> bool:
	"""判断是否为工具输出"""
	return isinstance(message, ToolMessage)

def is_block_content(content: Any) -> bool:
	"""判断是否为块列表（非字符串）"""
	return isinstance(content, list)

def is_target_message(message: Any) -> bool:
	"""判断message是否为目标信息"""
	return hasattr(message, "content") and is_tool_message(message) and is_block_content(message.content)
