from langchain_core.tools	import tool

from pydantic			import BaseModel, Field
from typing				import Dict, Any
from miaoli_bot.utils	import fail, success
from pathlib			import Path

import os


class ToolSchema(BaseModel):
	
	path	: str	= Field(..., description="待读取的目标文件路径")
	encoding: str	= Field(default="utf-8", description="文件编码")


@tool(args_schema=ToolSchema)
async def read_file(path: str, encoding: str = "utf-8") -> Dict[str, Any]:
	
	"""读取一个文件"""
	
	if not os.path.isfile(path):
		return fail(f"{path} 不是一个文件或不存在")
	
	try:
		
		b_data	= Path(path).read_bytes()
		s_data	= b_data.decode(encoding)
	
	except Exception as e:
		return fail(f"读取失败: {type(e).__name__}: {e}")
	
	return success(s_data)