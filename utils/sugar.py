from typing		import Optional, List

from langgraph.config			import get_config
from langchain_core.messages	import AIMessage, ToolCall

from ..consts	import GROUP_PREFIX, PRIVATE_PREFIX, PLUGIN_CONFIG
from ..stores	import SHARE_STORE
from ..models	import LLM

import os


def concatenate_id(session_id: str, is_group: bool) -> str:
	
	prefix = GROUP_PREFIX if is_group else PRIVATE_PREFIX
	
	return f"{prefix}{session_id}"

def split_string(string: str, separator: Optional[str] = None) -> List[str]:
	
	if not separator:
		return [string]
	
	return string.split(separator)

def get_thread_id() -> str:
	
	"""当前会话 id 仅用于日志 图外调用会抛异常 这里兜住"""
	
	try:
		config = get_config()
		return str(config["configurable"]["thread_id"])
	
	except Exception:
		return "unknown"

def get_tool_calls(message: AIMessage) -> List[ToolCall]:
	
	"""取消息里的工具调用 没有就返回空表"""
	
	return message.tool_calls or []

def get_sub_plugin_root(sub_plugin_name: str) -> str:
	
	"""获取子插件根目录"""
	
	plugin_config = SHARE_STORE.recall(PLUGIN_CONFIG)
	
	if not plugin_config.sub_plugin.is_enable or not plugin_config.sub_plugin.load_from:
		raise RuntimeError(f"插件未启用")
	
	return os.path.join(plugin_config.sub_plugin.load_from, sub_plugin_name)

def get_model_config(provider_name: str, model_name: str) -> "LLM":
	
	plugin_config = SHARE_STORE.recall(PLUGIN_CONFIG)
	
	if provider_name not in plugin_config.providers:
		raise RuntimeError()
	
	provider_cfg = plugin_config.providers[provider_name]
	
	if model_name not in provider_cfg.models:
		raise RuntimeError()
	
	return provider_cfg.models[model_name]