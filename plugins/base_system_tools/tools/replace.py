from pydantic				import BaseModel, Field
from typing					import Dict
from pathlib				import Path
from miaoli_bot				import success, fail
from langchain_core.tools	import tool

import aiofiles


class ToolSchema(BaseModel):
	path	: str	= Field(..., description="待修改的文件路径")
	old_text: str	= Field(..., description="待替换内容")
	new_text: str	= Field(..., description="替换内容")
	encoding: str	= Field(default="utf-8", description="文件编码")
	count	: int	= Field(default=-1, description="替换数量 默认全部替换")


@tool(args_schema=ToolSchema)
async def replace(
	path	: str,
	old_text: str,
	new_text: str,
	encoding: str,
	count	: int,
) -> Dict[str, str]:
	
	"""
	替换文件内容
	将 path 的 old_text 替换为 new_text
	"""
	
	try:
		
		old_content	= Path(path).read_text(encoding=encoding)
		new_content	= old_content.replace(old_text, new_text, count)
	
		async with aiofiles.open(path, encoding=encoding, mode="w") as file:
			await file.write(new_content)
	
	except Exception as e:
		return fail(f"替换失败: {type(e).__name__}: {e}")
	
	return success(f"替换成功: {old_text} -> {new_text}")