from ..consts	import PLUGIN_CONFIG
from ..stores	import SHARE_STORE
from ..utils	import fail

from langchain_core.tools	import tool
from typing					import Dict, Any


@tool
async def list_memes() -> Dict[str, Any]:
	
	"""列出所有已归档的表情包"""
	
	plugin_config	= SHARE_STORE.recall(PLUGIN_CONFIG, None)
	meme_config		= getattr(plugin_config, "meme_config", None)
	if meme_config is None:
		return fail("meme被禁用")
	
	return fail("工具未写完")