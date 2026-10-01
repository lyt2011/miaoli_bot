from pydantic				import BaseModel, Field
from typing					import Dict
from miaoli_bot				import success, fail
from langchain_core.tools	import tool

import aiofiles


class ToolSchema(BaseModel):
	path	: str	= Field(..., description="待写入的文件路径")
	content	: str	= Field(..., description="待写入的内容")
	encoding: str	= Field(default="utf-8", description="文件编码 默认utf-8")


@tool(args_schema=ToolSchema)
async def write(path: str, content: str, encoding: str = "utf-8") -> Dict[str, str]:
	
	"""
	将 content 写入 path 指向的文件
	path 指向的文件不存在时则会自动创建
	"""
	
	try:
		
		async with aiofiles.open(path, encoding=encoding, mode="w") as file:
			await file.write(content)
	
	except Exception as e:
		return fail(f"写入失败: {type(e).__name__}: {e}")
	
	return success("写入成功")