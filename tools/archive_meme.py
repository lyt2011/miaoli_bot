from ..consts	import PLUGIN_CONFIG
from ..stores	import SHARE_STORE
from ..utils	import fail

from pydantic				import BaseModel, Field
from typing					import List, Dict, Any
from langchain_core.tools	import tool


class ToolSchema(BaseModel):
	meme: str		= Field(..., description="目标表情包(图片)的路径")
	tags: List[str]	= Field(..., description="表情包的标签", min_length=1)


@tool(args_schema=ToolSchema)
async def archive_meme(meme: str, tags: List[str]) -> Dict[str, Any]:
	
	"""归档表情包"""
	
	plugin_config	= SHARE_STORE.recall(PLUGIN_CONFIG, None)
	meme_config		= getattr(plugin_config, "meme_config", None)
	if meme_config is None:
		return fail("meme被禁用")
	
	return fail("工具未写完")