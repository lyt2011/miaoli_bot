from miaoli_bot.stores	import SHARE_STORE
from miaoli_bot.consts	import NCATBOT_API
from miaoli_bot.utils	import success, fail

from pydantic				import BaseModel, Field
from typing					import Dict, Any
from langchain_core.tools	import tool


class ToolSchema(BaseModel):
	url: str = Field(..., description="目标 QQ 文件的url")


@tool(args_schema=ToolSchema)
async def download_qq_file(url: str) -> Dict[str, Any]:

	"""
	下载从 QQ 平台发来的文件
	文件会下载到指定路径 并在工具结果返回
	url 为非 QQ 平台文件时将会发生未定义情况
	"""

	ncatbot_api = SHARE_STORE.recall(NCATBOT_API)
	
	try:
		dl_result = await ncatbot_api.qq.file.download_file(url=url)
	
	except Exception as e:
		return fail(f"下载失败: {type(e).__name__}: {e}")

	return success(dl_result.model_dump())
