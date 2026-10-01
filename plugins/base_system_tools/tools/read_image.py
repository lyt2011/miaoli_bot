from langchain_core.tools	import tool
from pydantic				import BaseModel, Field
from typing					import List, Dict, Any, Union
from pathlib				import Path
from base64					import b64encode

from miaoli_bot.utils	import fail
from miaoli_bot			import SHARE_STORE

from ..consts	import PLUGIN_CONFIG

import filetype


class ToolSchema(BaseModel):
	path: str	= Field(..., description="图片路径")


@tool(args_schema=ToolSchema)
async def read_image(path: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
	
	"""读取一张图片"""
	
	read_image_config = SHARE_STORE.recall(PLUGIN_CONFIG).read_image
	
	try:
		
		kind = filetype.guess(path)
		if kind is None:
			return fail(f"无法识别 {path} 的类型")
		
		mime, extension	= kind.mime, kind.extension
		if extension not in read_image_config.support_image:
			return fail(f"不支持的数据类型 {extension}")
		
		image_b64 = b64encode(Path(path).read_bytes()).decode()
	
	except Exception as e:
		return fail(f"{type(e).__name__}: {str(e)}")
	
	return [
		{ "type": "text", "text": "图片已添加到上下文中" },
		{ "type": "image_url", "image_url": { "url": f"data:{mime};base64,{image_b64}" } }
	]